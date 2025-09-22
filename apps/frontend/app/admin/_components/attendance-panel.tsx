import React from 'react';

import type { AttendanceReport } from '../../../lib/admin-api';

type AttendancePanelProps = {
  report: AttendanceReport;
};

const formatNumber = (value: number): string => value.toLocaleString();

export default function AttendancePanel({ report }: AttendancePanelProps): JSX.Element {
  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Attendance trends</h2>
          <p className="text-sm text-slate-500">Segmented by campus and ministry.</p>
        </div>
        <p className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-indigo-600">
          {report.attendanceRate.toFixed(1)}% overall
        </p>
      </header>

      <dl className="mt-6 grid gap-4 text-sm text-slate-600 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-100 p-4">
          <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">Expected check-ins</dt>
          <dd className="mt-2 text-2xl font-semibold text-slate-900">{formatNumber(report.totalExpected)}</dd>
        </div>
        <div className="rounded-xl border border-slate-100 p-4">
          <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">Actual check-ins</dt>
          <dd className="mt-2 text-2xl font-semibold text-slate-900">{formatNumber(report.totalChecked)}</dd>
        </div>
        <div className="rounded-xl border border-slate-100 p-4">
          <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">Gap</dt>
          <dd className="mt-2 text-2xl font-semibold text-rose-600">
            {formatNumber(Math.max(report.totalExpected - report.totalChecked, 0))}
          </dd>
        </div>
      </dl>

      {report.campuses.length ? (
        <div className="mt-6 space-y-4">
          {report.campuses.map((campus) => (
            <article key={campus.campus} className="rounded-xl border border-slate-100 p-4">
              <header className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-slate-900">{campus.campus}</h3>
                  <p className="text-xs text-slate-500">
                    {formatNumber(campus.checked)} attended · {formatNumber(campus.expected)} expected
                  </p>
                </div>
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600">
                  {campus.attendanceRate.toFixed(1)}% attendance
                </span>
              </header>

              {campus.timeline.length ? (
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full text-left text-xs text-slate-600">
                    <thead>
                      <tr className="text-slate-400">
                        <th className="py-2 pr-4 font-medium">Date</th>
                        <th className="py-2 pr-4 font-medium">Checked-in</th>
                        <th className="py-2 font-medium">Expected</th>
                      </tr>
                    </thead>
                    <tbody>
                      {campus.timeline.map((entry) => (
                        <tr key={`${campus.campus}-${entry.date}`} className="border-t border-slate-100">
                          <td className="py-2 pr-4">{entry.date}</td>
                          <td className="py-2 pr-4">{formatNumber(entry.checked)}</td>
                          <td className="py-2">{formatNumber(entry.expected)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}

              {campus.departments.length ? (
                <div className="mt-4">
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Departments</h4>
                  <ul className="mt-2 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
                    {campus.departments.map((department) => (
                      <li key={`${campus.campus}-${department.name}`} className="rounded-lg border border-slate-100 px-3 py-2">
                        <p className="font-medium text-slate-900">{department.name}</p>
                        <p className="text-xs text-slate-500">
                          {formatNumber(department.checked)} of {formatNumber(department.expected)} attendees
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <p className="mt-6 text-sm text-slate-500">No attendance records available for this reporting window.</p>
      )}
    </section>
  );
}
