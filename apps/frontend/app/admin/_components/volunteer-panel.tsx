import React from 'react';

import type { VolunteerReport } from '../../../lib/admin-api';

type VolunteerPanelProps = {
  report: VolunteerReport;
};

const formatPercent = (value: number): string => `${value.toFixed(1)}%`;

export default function VolunteerPanel({ report }: VolunteerPanelProps): JSX.Element {
  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Volunteer fulfilment</h2>
          <p className="text-sm text-slate-500">Track coverage across departments and roles.</p>
        </div>
        <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600">
          {formatPercent(report.overallRate)} filled
        </span>
      </header>

      <div className="mt-6 grid gap-4 text-sm text-slate-600 sm:grid-cols-2">
        {report.departments.map((department) => (
          <article key={department.department} className="rounded-xl border border-slate-100 p-4">
            <h3 className="text-base font-semibold text-slate-900">{department.department}</h3>
            <p className="mt-1 text-xs text-slate-500">
              {department.assigned} of {department.needed} volunteers scheduled
            </p>
            <div className="mt-3 h-2 rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full bg-indigo-500"
                style={{ width: `${Math.min(department.rate, 100)}%` }}
              />
            </div>
            <p className="mt-2 text-xs font-semibold text-indigo-600">{formatPercent(department.rate)} coverage</p>
          </article>
        ))}
      </div>

      {report.roles.length ? (
        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full text-left text-xs text-slate-600">
            <thead className="text-slate-400">
              <tr>
                <th className="py-2 pr-4 font-medium">Department</th>
                <th className="py-2 pr-4 font-medium">Role</th>
                <th className="py-2 pr-4 font-medium">Assigned</th>
                <th className="py-2 pr-4 font-medium">Needed</th>
                <th className="py-2 font-medium">Fill rate</th>
              </tr>
            </thead>
            <tbody>
              {report.roles.map((role) => (
                <tr key={`${role.department}-${role.role}`} className="border-t border-slate-100">
                  <td className="py-2 pr-4">{role.department}</td>
                  <td className="py-2 pr-4">{role.role}</td>
                  <td className="py-2 pr-4">{role.assigned}</td>
                  <td className="py-2 pr-4">{role.needed}</td>
                  <td className="py-2">{formatPercent(role.rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-6 text-sm text-slate-500">No volunteer assignments recorded for this range.</p>
      )}
    </section>
  );
}
