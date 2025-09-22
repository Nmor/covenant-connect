import React from 'react';

import type { AssimilationReport } from '../../../lib/admin-api';

type AssimilationPanelProps = {
  report: AssimilationReport;
};

export default function AssimilationPanel({ report }: AssimilationPanelProps): JSX.Element {
  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Assimilation funnel</h2>
          <p className="text-sm text-slate-500">Movement from guest to serving members.</p>
        </div>
        <p className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
          {report.totalMembers.toLocaleString()} tracked
        </p>
      </header>

      <ul className="mt-6 grid gap-3 sm:grid-cols-2">
        {report.stages.map((stage) => (
          <li key={stage.label} className="rounded-xl border border-slate-100 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{stage.label}</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{stage.count.toLocaleString()}</p>
          </li>
        ))}
        {!report.stages.length ? (
          <li className="rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
            No members recorded during this period.
          </li>
        ) : null}
      </ul>

      {report.campuses.length ? (
        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full text-left text-xs text-slate-600">
            <thead className="text-slate-400">
              <tr>
                <th className="py-2 pr-4 font-medium">Campus</th>
                {report.stages.map((stage) => (
                  <th key={stage.label} className="py-2 pr-4 font-medium">
                    {stage.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {report.campuses.map((campus) => (
                <tr key={campus.campus} className="border-t border-slate-100">
                  <td className="py-2 pr-4 font-medium text-slate-900">{campus.campus}</td>
                  {report.stages.map((stage) => {
                    const campusStage = campus.stages.find((item) => item.label === stage.label);
                    return (
                      <td key={`${campus.campus}-${stage.label}`} className="py-2 pr-4">
                        {campusStage ? campusStage.count.toLocaleString() : '0'}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-6 text-sm text-slate-500">No campus segmentation available for this range.</p>
      )}
    </section>
  );
}
