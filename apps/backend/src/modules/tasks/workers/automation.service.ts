import { Inject, Injectable, Logger } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import type { JobsOptions } from 'bullmq';

import { PrismaService } from '../../../prisma/prisma.service';
import { EmailService } from '../../email/email.service';
import { TasksService } from '../tasks.service';
import { TaskJobNames } from '../task.constants';

type AutomationWithSteps = Prisma.AutomationGetPayload<{ include: { steps: true } }>;
type AutomationStepWithAutomation = Prisma.AutomationStepGetPayload<{ include: { automation: true } }>;

type AutomationContext = Record<string, unknown>;

@Injectable()
export class AutomationService {
  private readonly logger = new Logger(AutomationService.name);

  constructor(
    @Inject(PrismaService) private readonly prisma: PrismaService,
    @Inject(TasksService) private readonly tasks: TasksService,
    @Inject(EmailService) private readonly email: EmailService
  ) {}

  async trigger(trigger: string, context: AutomationContext = {}): Promise<number> {
    const automations = await this.prisma.automation.findMany({
      where: { trigger, isActive: true },
      select: { id: true }
    });

    if (automations.length === 0) {
      return 0;
    }

    await this.tasks.enqueue(TaskJobNames.RunAutomations, {
      automationIds: automations.map((automation) => automation.id),
      context: this.cloneContext(context),
      trigger
    });

    return automations.length;
  }

  async triggerFollowUp(context: AutomationContext = {}): Promise<void> {
    await this.trigger('scheduled_follow_up', context);
  }

  async runAutomationsForIds(
    automationIds: number[],
    context: AutomationContext = {},
    trigger?: string
  ): Promise<void> {
    if (automationIds.length === 0) {
      return;
    }

    const automations = await this.prisma.automation.findMany({
      where: { id: { in: automationIds }, isActive: true },
      include: { steps: true }
    });

    for (const automation of automations) {
      await this.scheduleAutomationSteps(automation, context, trigger);
    }
  }

  async executeStep(
    stepId: number,
    context: AutomationContext = {},
    trigger?: string
  ): Promise<void> {
    const step = await this.prisma.automationStep.findUnique({
      where: { id: stepId },
      include: { automation: true }
    });

    if (!step || !step.automation || !step.automation.isActive) {
      this.logger.debug(`Skipping automation step ${stepId} because it is missing or inactive.`);
      return;
    }

    const config = this.parseConfig(step.config);
    const expandedContext = await this.expandContext(context, trigger, step.automation);

    switch ((step.actionType ?? '').toLowerCase()) {
      case 'email':
        await this.runEmailAction(step, config, expandedContext);
        break;
      case 'sms':
        await this.runSmsAction(step, config, expandedContext);
        break;
      case 'assignment':
        await this.runAssignmentAction(step, config, expandedContext);
        break;
      default:
        this.logger.warn(`Unknown automation action type '${step.actionType}' for step ${step.id}`);
    }
  }

  private async scheduleAutomationSteps(
    automation: AutomationWithSteps,
    context: AutomationContext,
    trigger?: string
  ): Promise<void> {
    const sortedSteps = [...automation.steps].sort((left, right) => {
      const leftOrder = left.order ?? 0;
      const rightOrder = right.order ?? 0;
      if (leftOrder !== rightOrder) {
        return leftOrder - rightOrder;
      }
      return left.id - right.id;
    });

    for (const step of sortedSteps) {
      const delayMinutes = Math.max(step.delayMinutes ?? 0, 0);
      const options: JobsOptions = {};
      if (delayMinutes > 0) {
        options.delay = delayMinutes * 60 * 1000;
      }

      await this.tasks.enqueue(
        TaskJobNames.ExecuteAutomationStep,
        {
          stepId: step.id,
          context: this.cloneContext(context),
          trigger: trigger ?? automation.trigger
        },
        options
      );
    }
  }

  private async expandContext(
    context: AutomationContext,
    trigger: string | undefined,
    automation: AutomationWithSteps
  ): Promise<AutomationContext> {
    const expanded: AutomationContext = {
      ...context,
      trigger: context.trigger ?? trigger ?? automation.trigger,
      automationName: context.automationName ?? automation.name,
      automationId: context.automationId ?? automation.id
    };

    await this.resolveContextEntity(expanded, 'prayerRequest', ['prayer_request', 'prayerRequest'], ['prayer_request_id', 'prayerRequestId'], async (id) =>
      this.prisma.prayerRequest.findUnique({ where: { id } })
    );

    await this.resolveContextEntity(expanded, 'event', ['event'], ['event_id', 'eventId'], async (id) =>
      this.prisma.event.findUnique({ where: { id } })
    );

    await this.resolveContextEntity(expanded, 'sermon', ['sermon'], ['sermon_id', 'sermonId'], async (id) =>
      this.prisma.sermon.findUnique({ where: { id } })
    );

    await this.resolveContextEntity(expanded, 'user', ['user'], ['user_id', 'userId'], async (id) =>
      this.prisma.user.findUnique({ where: { id } })
    );

    if (!expanded.submitterEmail && expanded.prayerRequest && typeof expanded.prayerRequest === 'object') {
      const email = (expanded.prayerRequest as { requesterEmail?: string | null }).requesterEmail;
      if (email) {
        expanded.submitterEmail = email;
      }
    }

    return expanded;
  }

  private async resolveContextEntity(
    context: AutomationContext,
    targetKey: string,
    entityKeys: string[],
    idKeys: string[],
    resolver: (id: number) => Promise<unknown>
  ): Promise<void> {
    if (context[targetKey]) {
      return;
    }

    for (const key of entityKeys) {
      if (context[key]) {
        context[targetKey] = context[key];
        return;
      }
    }

    for (const idKey of idKeys) {
      const rawId = context[idKey];
      const id = this.parseId(rawId);
      if (id !== null) {
        const entity = await resolver(id);
        if (entity) {
          context[targetKey] = entity;
        }
        return;
      }
    }
  }

  private async runEmailAction(
    step: AutomationStepWithAutomation,
    config: Record<string, unknown>,
    context: AutomationContext
  ): Promise<void> {
    const recipients = await this.resolveRecipients(step, config, context);
    if (recipients.length === 0) {
      this.logger.log(`Skipping automation email step ${step.id} because no recipients were resolved.`);
      return;
    }

    const renderContext = {
      ...context,
      step,
      automation: step.automation
    };

    const subjectTemplate = this.getString(config, ['subject']) ?? step.title ?? step.automation.name;
    const bodyTemplate = this.getString(config, ['body', 'message']) ?? '';
    const isHtml = this.getString(config, ['bodyFormat', 'body_format'])?.toLowerCase() === 'html';

    const subject = this.renderTemplate(subjectTemplate, renderContext).trim();
    const body = this.renderTemplate(bodyTemplate, renderContext);

    await this.email.sendMail({
      to: recipients,
      subject,
      text: isHtml ? this.stripHtml(body) : body,
      html: isHtml ? body : undefined
    });

    this.logger.log(`Automation email step ${step.id} sent to ${recipients.length} recipient(s).`);
  }

  private async runSmsAction(
    step: AutomationStepWithAutomation,
    config: Record<string, unknown>,
    context: AutomationContext
  ): Promise<void> {
    const recipients = await this.resolveRecipients(step, config, context);
    if (recipients.length === 0) {
      this.logger.log(`No SMS recipients resolved for automation step ${step.id}`);
      return;
    }

    const template = this.getString(config, ['message', 'body']) ?? '';
    const renderContext = {
      ...context,
      step,
      automation: step.automation
    };
    const message = this.renderTemplate(template, renderContext);

    this.logger.log(
      `SMS automation step ${step.id} would notify ${recipients.join(', ')} via channel '${step.channel ?? 'sms'}': ${message}`
    );
  }

  private async runAssignmentAction(
    step: AutomationStepWithAutomation,
    config: Record<string, unknown>,
    context: AutomationContext
  ): Promise<void> {
    const department = step.department ?? this.getString(config, ['department']);
    const assignee = this.getString(config, ['assignee']);
    const notesTemplate = this.getString(config, ['notes', 'body']);
    const renderContext = {
      ...context,
      step,
      automation: step.automation
    };
    const notes = notesTemplate ? this.renderTemplate(notesTemplate, renderContext) : '';

    this.logger.log(
      `Automation assignment step ${step.id} assigned to department '${department ?? 'unspecified'}'` +
        `${assignee ? ` (assignee: ${assignee})` : ''}. ${notes}`
    );
  }

  private async resolveRecipients(
    step: AutomationStepWithAutomation,
    config: Record<string, unknown>,
    context: AutomationContext
  ): Promise<string[]> {
    const mode = (this.getString(config, ['recipientMode', 'recipient_mode']) ?? 'custom').toLowerCase();
    const recipients = new Set<string>();

    if (mode === 'admins') {
      const admins = await this.prisma.user.findMany({
        where: { isAdmin: true, email: { not: null } },
        select: { email: true }
      });
      for (const admin of admins) {
        if (admin.email) {
          recipients.add(admin.email);
        }
      }
    } else if (mode === 'context') {
      const key = this.getString(config, ['contextKey', 'context_key']) ?? 'submitterEmail';
      const value = this.resolveContextValue(context, key);
      if (typeof value === 'string') {
        recipients.add(value);
      } else if (Array.isArray(value)) {
        for (const item of value) {
          if (typeof item === 'string') {
            recipients.add(item);
          }
        }
      }
    } else if (mode === 'department') {
      this.splitEmails(this.getString(config, ['departmentEmails', 'department_emails'])).forEach((email) =>
        recipients.add(email)
      );
    } else {
      this.splitEmails(this.getString(config, ['recipients'])).forEach((email) => recipients.add(email));
    }

    if (recipients.size === 0) {
      this.splitEmails(this.getString(config, ['fallbackRecipients', 'fallback_recipients'])).forEach((email) =>
        recipients.add(email)
      );
    }

    if (recipients.size === 0 && step.department) {
      this.splitEmails(this.getString(config, ['departmentEmails', 'department_emails'])).forEach((email) =>
        recipients.add(email)
      );
    }

    return Array.from(recipients).filter((email) => Boolean(email));
  }

  private renderTemplate(template: string, context: AutomationContext): string {
    return template.replace(/{{\s*([^}]+)\s*}}/g, (_, expression: string) => {
      const value = this.resolveContextValue(context, expression.trim());
      if (value === null || value === undefined) {
        return '';
      }
      if (value instanceof Date) {
        return value.toISOString();
      }
      if (typeof value === 'object') {
        try {
          return JSON.stringify(value);
        } catch (error) {
          return '[object]';
        }
      }
      return String(value);
    });
  }

  private resolveContextValue(context: AutomationContext, path: string): unknown {
    const normalisedPath = path.replace(/[[\]]/g, '.');
    const segments = normalisedPath.split('.').map((segment) => segment.trim()).filter(Boolean);

    let current: unknown = context;
    for (const segment of segments) {
      if (current && typeof current === 'object' && !Array.isArray(current) && segment in (current as Record<string, unknown>)) {
        current = (current as Record<string, unknown>)[segment];
      } else {
        return undefined;
      }
    }

    return current;
  }

  private splitEmails(value: string | null | undefined): string[] {
    if (!value) {
      return [];
    }
    return value
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  }

  private getString(config: Record<string, unknown>, keys: string[]): string | undefined {
    for (const key of keys) {
      const value = config[key];
      if (typeof value === 'string' && value.trim()) {
        return value.trim();
      }
    }
    return undefined;
  }

  private parseId(value: unknown): number | null {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return Math.trunc(value);
    }
    if (typeof value === 'string' && value.trim()) {
      const parsed = Number.parseInt(value, 10);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
    return null;
  }

  private parseConfig(value: Prisma.JsonValue | null): Record<string, unknown> {
    if (!value || typeof value !== 'object') {
      return {};
    }
    if (Array.isArray(value)) {
      return {};
    }
    return { ...(value as Record<string, unknown>) };
  }

  private cloneContext(context: AutomationContext): AutomationContext {
    if (!context || typeof context !== 'object') {
      return {};
    }
    return JSON.parse(JSON.stringify(context));
  }

  private stripHtml(value: string): string {
    return value.replace(/<[^>]+>/g, '');
  }
}
