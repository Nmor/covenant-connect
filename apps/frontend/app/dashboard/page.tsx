import React from 'react';

import type { DashboardResponse } from '../../lib/api';
import { getDashboardReport } from '../../lib/api';

export default async function DashboardPage() {
  const report: DashboardResponse = await getDashboardReport().catch(() => ({
    kpis: [
      { label: 'Total Giving', value: 0 },
      { label: 'Completed Donations', value: 0 },
      { label: 'Upcoming Events', value: 0 }
    ]
  }));

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-12">
      <header>
        <h1 className="text-3xl font-semibold text-slate-900">Operational dashboard</h1>
        <p className="mt-2 text-sm text-slate-500">
          Monitor the health of your ministry, giving pipeline, and pastoral care automations.
        </p>
      </header>

      <section className="grid gap-6 md:grid-cols-3">
        {report.kpis.map((kpi) => (
          <article key={kpi.label} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-slate-400">{kpi.label}</p>
            <p className="mt-4 text-3xl font-semibold text-slate-900">{kpi.value}</p>
            {typeof kpi.change === 'number' ? (
              <p className="mt-2 text-sm text-emerald-600">{kpi.change.toFixed(1)}% change</p>
            ) : (
              <p className="mt-2 text-sm text-slate-400">Awaiting data</p>
            )}
          </article>
        ))}
      </section>
    </main>
  );
}
