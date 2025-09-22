import React from 'react';

import type { AdminMetrics, CareFollowUp } from '../../lib/admin-api';
import { getAdminMetrics, getRecentCareFollowUps } from '../../lib/admin-api';
import AssimilationPanel from './_components/assimilation-panel';
import AttendancePanel from './_components/attendance-panel';
import CareFollowUpList from './_components/care-follow-up-list';
import GivingPanel from './_components/giving-panel';
import TimeRangeFilter from './_components/time-range-filter';
import VolunteerPanel from './_components/volunteer-panel';

const DEFAULT_RANGE = '90d';
const RANGE_LABELS: Record<string, string> = {
  '30d': 'Last 30 days',
  '60d': 'Last 60 days',
  '90d': 'Last 90 days',
  '6m': 'Last 6 months',
  '1y': 'Last 12 months'
};

const createEmptyMetrics = (): AdminMetrics => ({
  attendance: {
    totalExpected: 0,
    totalChecked: 0,
    attendanceRate: 0,
    campuses: []
  },
  volunteers: {
    roles: [],
    departments: [],
    overallRate: 0
  },
  giving: {
    total: 0,
    byCurrency: {},
    byMethod: {},
    monthly: []
  },
  assimilation: {
    totalMembers: 0,
    stages: [],
    campuses: []
  }
});

type DashboardData = {
  metrics: AdminMetrics;
  followUps: CareFollowUp[];
  error?: string;
};

async function loadDashboard(range: string): Promise<DashboardData> {
  try {
    const [metrics, followUps] = await Promise.all([
      getAdminMetrics(range),
      getRecentCareFollowUps(8)
    ]);

    return { metrics, followUps };
  } catch (error) {
    console.error('Failed to load admin dashboard data.', error);
    return {
      metrics: createEmptyMetrics(),
      followUps: [],
      error:
        'The Prisma API is unavailable right now. The dashboard is showing placeholder data until the connection is restored.'
    };
  }
}

type AdminDashboardPageProps = {
  searchParams?: Record<string, string | string[]>;
};

export default async function AdminDashboardPage({
  searchParams
}: AdminDashboardPageProps): Promise<JSX.Element> {
  const rangeParam = typeof searchParams?.range === 'string' ? searchParams.range : DEFAULT_RANGE;
  const { metrics, followUps, error } = await loadDashboard(rangeParam);
  const rangeLabel = RANGE_LABELS[rangeParam] ?? RANGE_LABELS[DEFAULT_RANGE];

  return (
    <div className="space-y-8">
      <header className="rounded-2xl bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">Executive insights</h1>
        <p className="mt-2 text-sm text-slate-500">
          Monitor attendance, assimilation, volunteer coverage, and giving in one place. All data flows through the forthcoming
          Prisma-backed admin APIs.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-between gap-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Current window</p>
            <p className="text-sm font-medium text-slate-900">{rangeLabel}</p>
          </div>
          <TimeRangeFilter selected={rangeParam} />
        </div>
        {error ? (
          <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
            {error}
          </div>
        ) : null}
      </header>

      <div className="grid gap-8 lg:grid-cols-[2fr_1fr]">
        <AttendancePanel report={metrics.attendance} />
        <AssimilationPanel report={metrics.assimilation} />
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        <VolunteerPanel report={metrics.volunteers} />
        <GivingPanel summary={metrics.giving} />
      </div>

      <CareFollowUpList items={followUps} />
    </div>
  );
}
