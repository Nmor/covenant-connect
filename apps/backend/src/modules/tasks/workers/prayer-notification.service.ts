import { Inject, Injectable, Logger } from '@nestjs/common';

import { PrismaService } from '../../../prisma/prisma.service';
import { EmailService } from '../../email/email.service';

@Injectable()
export class PrayerNotificationService {
  private readonly logger = new Logger(PrayerNotificationService.name);

  constructor(
    @Inject(PrismaService) private readonly prisma: PrismaService,
    @Inject(EmailService) private readonly email: EmailService
  ) {}

  async notifyAdmins(prayerRequestId: unknown): Promise<void> {
    const id = this.parseId(prayerRequestId);
    if (id === null) {
      this.logger.warn(`Skipping prayer notification because the id '${String(prayerRequestId)}' is invalid`);
      return;
    }

    const prayerRequest = await this.prisma.prayerRequest.findUnique({ where: { id } });
    if (!prayerRequest) {
      this.logger.warn(`Prayer request ${id} was not found when dispatching notifications`);
      return;
    }

    const admins = await this.prisma.user.findMany({
      where: { isAdmin: true },
      select: { email: true }
    });

    const recipients = admins.map((admin) => admin.email).filter((email): email is string => Boolean(email));

    if (recipients.length === 0) {
      this.logger.warn('No administrators with email addresses are configured to receive prayer notifications');
      return;
    }

    const createdAt = prayerRequest.createdAt ?? new Date();
    const formattedDate = new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: 'numeric',
      minute: '2-digit'
    }).format(createdAt);

    const subject = 'New Prayer Request Received';
    const bodyLines = [
      'A new prayer request has been submitted:',
      '',
      `From: ${prayerRequest.requesterName}`,
      `Email: ${prayerRequest.requesterEmail ?? 'Not provided'}`,
      `Phone: ${prayerRequest.requesterPhone ?? 'Not provided'}`,
      `Request: ${prayerRequest.message}`,
      `Public: ${prayerRequest.isPublic ? 'Yes' : 'No'}`,
      `Submitted: ${formattedDate}`
    ];

    await this.email.sendMail({
      to: recipients,
      subject,
      text: bodyLines.join('\n')
    });

    this.logger.log(`Prayer notification sent to ${recipients.length} administrator(s)`);
  }

  private parseId(value: unknown): number | null {
    if (typeof value === 'number' && Number.isInteger(value)) {
      return value;
    }

    if (typeof value === 'string' && value.trim()) {
      const parsed = Number.parseInt(value, 10);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }

    return null;
  }
}
