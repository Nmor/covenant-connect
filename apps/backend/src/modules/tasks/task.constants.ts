export const TASK_QUEUE_NAME = 'automation-tasks';

export const TaskJobNames = {
  SendPrayerNotification: 'notifications.prayer',
  DepartmentKpiDigest: 'digests.department',
  ExecutiveKpiDigest: 'digests.executive',
  RunAutomations: 'automations.run',
  ExecuteAutomationStep: 'automations.execute-step',
  FollowUpScan: 'automations.follow-up'
} as const;

export type TaskJobName = (typeof TaskJobNames)[keyof typeof TaskJobNames];

export type TaskJobPayloads = {
  [TaskJobNames.SendPrayerNotification]: { prayerRequestId: string | number };
  [TaskJobNames.DepartmentKpiDigest]: { rangeDays?: number };
  [TaskJobNames.ExecutiveKpiDigest]: { rangeDays?: number };
  [TaskJobNames.RunAutomations]: {
    automationIds: Array<number | string>;
    context?: Record<string, unknown>;
    trigger?: string | null;
  };
  [TaskJobNames.ExecuteAutomationStep]: {
    stepId: number | string;
    context?: Record<string, unknown>;
    trigger?: string | null;
  };
  [TaskJobNames.FollowUpScan]: {
    context?: Record<string, unknown>;
  };
};

export type TaskJobPayload<TName extends TaskJobName> = TaskJobPayloads[TName];
