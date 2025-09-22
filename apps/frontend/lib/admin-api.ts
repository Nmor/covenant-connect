import { apiRequest } from './api';

export type AttendanceTimelineEntry = {
  date: string;
  expected: number;
  checked: number;
};

export type AttendanceDepartmentSummary = {
  name: string;
  expected: number;
  checked: number;
};

export type AttendanceCampusSummary = {
  campus: string;
  expected: number;
  checked: number;
  attendanceRate: number;
  timeline: AttendanceTimelineEntry[];
  departments: AttendanceDepartmentSummary[];
};

export type AttendanceReport = {
  totalExpected: number;
  totalChecked: number;
  attendanceRate: number;
  campuses: AttendanceCampusSummary[];
};

export type VolunteerRoleRow = {
  department: string;
  role: string;
  needed: number;
  assigned: number;
  rate: number;
};

export type VolunteerDepartmentSummary = {
  department: string;
  assigned: number;
  needed: number;
  rate: number;
};

export type VolunteerReport = {
  roles: VolunteerRoleRow[];
  departments: VolunteerDepartmentSummary[];
  overallRate: number;
};

export type GivingMonthlyEntry = {
  month: string;
  amount: number;
};

export type GivingSummary = {
  total: number;
  byCurrency: Record<string, number>;
  byMethod: Record<string, number>;
  monthly: GivingMonthlyEntry[];
};

export type AssimilationStage = {
  label: string;
  count: number;
};

export type AssimilationCampus = {
  campus: string;
  stages: AssimilationStage[];
};

export type AssimilationReport = {
  totalMembers: number;
  stages: AssimilationStage[];
  campuses: AssimilationCampus[];
};

export type AdminMetrics = {
  attendance: AttendanceReport;
  volunteers: VolunteerReport;
  giving: GivingSummary;
  assimilation: AssimilationReport;
};

export type CareFollowUp = {
  id: string;
  memberName: string;
  interactionType: string;
  interactionDate: string;
  notes?: string;
  followUpRequired?: boolean;
  followUpDate?: string | null;
};

export type AdminUserRecord = {
  id: string;
  username: string;
  email: string;
  isAdmin: boolean;
  createdAt: string;
  updatedAt: string;
  lastLoginAt?: string | null;
};

export type AdminUsersResponse = {
  users: AdminUserRecord[];
};

export type CreateAdminUserInput = {
  username: string;
  email: string;
  password: string;
  isAdmin: boolean;
};

export type UpdateAdminUserInput = {
  id: string;
  username?: string;
  email?: string;
  password?: string;
  isAdmin?: boolean;
};

type MetricsPayload = {
  attendance: {
    total_expected: number;
    total_checked: number;
    attendance_rate: number;
    campuses: {
      campus: string;
      expected: number;
      checked: number;
      attendance_rate: number;
      timeline: {
        date: string;
        expected: number;
        checked: number;
      }[];
      departments: {
        name: string;
        expected: number;
        checked: number;
      }[];
    }[];
  };
  volunteers: {
    roles: VolunteerRoleRow[];
    departments: VolunteerDepartmentSummary[];
    overall_rate: number;
  };
  giving: {
    total: number;
    by_currency: Record<string, number>;
    by_method: Record<string, number>;
    monthly: GivingMonthlyEntry[];
  };
  assimilation: {
    total_members: number;
    stages: AssimilationStage[];
    campuses: {
      campus: string;
      stages: AssimilationStage[];
    }[];
  };
};

type CareFollowUpRecord = {
  id: string | number;
  member_name?: string | null;
  interaction_type: string;
  interaction_date: string;
  notes?: string | null;
  follow_up_required?: boolean;
  follow_up_date?: string | null;
};

type AdminUserRecordPayload = {
  id: string | number;
  username: string;
  email: string;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string | null;
};

const toAttendanceReport = (payload: MetricsPayload['attendance']): AttendanceReport => ({
  totalExpected: payload.total_expected ?? 0,
  totalChecked: payload.total_checked ?? 0,
  attendanceRate: payload.attendance_rate ?? 0,
  campuses: (payload.campuses ?? []).map((campus) => ({
    campus: campus.campus,
    expected: campus.expected ?? 0,
    checked: campus.checked ?? 0,
    attendanceRate: campus.attendance_rate ?? 0,
    timeline: (campus.timeline ?? []).map((entry) => ({
      date: entry.date,
      expected: entry.expected ?? 0,
      checked: entry.checked ?? 0
    })),
    departments: (campus.departments ?? []).map((department) => ({
      name: department.name,
      expected: department.expected ?? 0,
      checked: department.checked ?? 0
    }))
  }))
});

const toVolunteerReport = (payload: MetricsPayload['volunteers']): VolunteerReport => ({
  roles: (payload.roles ?? []).map((role) => ({
    department: role.department,
    role: role.role,
    needed: role.needed ?? 0,
    assigned: role.assigned ?? 0,
    rate: role.rate ?? 0
  })),
  departments: (payload.departments ?? []).map((department) => ({
    department: department.department,
    assigned: department.assigned ?? 0,
    needed: department.needed ?? 0,
    rate: department.rate ?? 0
  })),
  overallRate: payload.overall_rate ?? 0
});

const toGivingSummary = (payload: MetricsPayload['giving']): GivingSummary => ({
  total: payload.total ?? 0,
  byCurrency: payload.by_currency ?? {},
  byMethod: payload.by_method ?? {},
  monthly: (payload.monthly ?? []).map((entry) => ({
    month: entry.month,
    amount: entry.amount ?? 0
  }))
});

const toAssimilationReport = (payload: MetricsPayload['assimilation']): AssimilationReport => ({
  totalMembers: payload.total_members ?? 0,
  stages: (payload.stages ?? []).map((stage) => ({
    label: stage.label,
    count: stage.count ?? 0
  })),
  campuses: (payload.campuses ?? []).map((campus) => ({
    campus: campus.campus,
    stages: (campus.stages ?? []).map((stage) => ({
      label: stage.label,
      count: stage.count ?? 0
    }))
  }))
});

const toCareFollowUp = (record: CareFollowUpRecord): CareFollowUp => ({
  id: String(record.id),
  memberName: record.member_name?.trim() || 'Unknown member',
  interactionType: record.interaction_type,
  interactionDate: record.interaction_date,
  notes: record.notes ?? undefined,
  followUpRequired: record.follow_up_required ?? false,
  followUpDate: record.follow_up_date ?? null
});

const toAdminUserRecord = (record: AdminUserRecordPayload): AdminUserRecord => ({
  id: String(record.id),
  username: record.username,
  email: record.email,
  isAdmin: record.is_admin,
  createdAt: record.created_at,
  updatedAt: record.updated_at,
  lastLoginAt: record.last_login_at ?? null
});

export async function getAdminMetrics(range?: string): Promise<AdminMetrics> {
  const search = new URLSearchParams();
  if (range) {
    search.set('range', range);
  }
  const path = search.toString() ? `/admin/reports/metrics?${search.toString()}` : '/admin/reports/metrics';
  const payload = await apiRequest<MetricsPayload>(path);

  return {
    attendance: toAttendanceReport(payload.attendance),
    volunteers: toVolunteerReport(payload.volunteers),
    giving: toGivingSummary(payload.giving),
    assimilation: toAssimilationReport(payload.assimilation)
  };
}

export async function getRecentCareFollowUps(limit = 10): Promise<CareFollowUp[]> {
  const search = new URLSearchParams({ limit: String(limit) });
  const records = await apiRequest<CareFollowUpRecord[]>(`/admin/care/follow-ups?${search.toString()}`);
  return records.map(toCareFollowUp);
}

export async function getAdminUsers(): Promise<AdminUsersResponse> {
  const records = await apiRequest<AdminUserRecordPayload[]>(`/admin/users`);
  return { users: records.map(toAdminUserRecord) };
}

export async function createAdminUser(input: CreateAdminUserInput): Promise<AdminUserRecord> {
  const record = await apiRequest<AdminUserRecordPayload>(`/admin/users`, {
    method: 'POST',
    body: JSON.stringify({
      username: input.username,
      email: input.email,
      password: input.password,
      is_admin: input.isAdmin
    })
  });
  return toAdminUserRecord(record);
}

export async function updateAdminUser(input: UpdateAdminUserInput): Promise<AdminUserRecord> {
  const { id, ...rest } = input;
  const record = await apiRequest<AdminUserRecordPayload>(`/admin/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({
      username: rest.username,
      email: rest.email,
      password: rest.password,
      is_admin: rest.isAdmin
    })
  });
  return toAdminUserRecord(record);
}

export async function deleteAdminUser(id: string): Promise<void> {
  await apiRequest(`/admin/users/${id}`, { method: 'DELETE' });
}
