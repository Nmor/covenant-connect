import React from 'react';

import type { GivingSummary } from '../../../lib/admin-api';

type GivingPanelProps = {
  summary: GivingSummary;
};

const formatCurrency = (amount: number, currency = 'USD'): string =>
  new Intl.NumberFormat(undefined, { style: 'currency', currency, maximumFractionDigits: 0 }).format(amount);

export default function GivingPanel({ summary }: GivingPanelProps): JSX.Element {
  const primaryCurrency = Object.keys(summary.byCurrency)[0] ?? 'USD';

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Giving summary</h2>
          <p className="text-sm text-slate-500">Financial health across payment channels.</p>
        </div>
        <p className="text-2xl font-semibold text-slate-900">{formatCurrency(summary.total, primaryCurrency)}</p>
      </header>

      <div className="mt-6 grid gap-6 text-sm text-slate-600 md:grid-cols-2">
        <article>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">By currency</h3>
          <ul className="mt-2 space-y-2">
            {Object.entries(summary.byCurrency).map(([currency, amount]) => (
              <li key={currency} className="flex items-center justify-between rounded-xl border border-slate-100 px-3 py-2">
                <span className="font-medium text-slate-900">{currency}</span>
                <span>{formatCurrency(amount, currency)}</span>
              </li>
            ))}
            {!Object.keys(summary.byCurrency).length ? (
              <li className="text-xs text-slate-500">No completed donations yet.</li>
            ) : null}
          </ul>
        </article>

        <article>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">By payment method</h3>
          <ul className="mt-2 space-y-2">
            {Object.entries(summary.byMethod).map(([method, amount]) => (
              <li key={method} className="flex items-center justify-between rounded-xl border border-slate-100 px-3 py-2">
                <span className="capitalize text-slate-900">{method}</span>
                <span>{formatCurrency(amount, primaryCurrency)}</span>
              </li>
            ))}
            {!Object.keys(summary.byMethod).length ? (
              <li className="text-xs text-slate-500">No payment channels configured.</li>
            ) : null}
          </ul>
        </article>
      </div>

      <div className="mt-6">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Monthly totals</h3>
        {summary.monthly.length ? (
          <ul className="mt-2 space-y-2 text-sm text-slate-600">
            {summary.monthly.map((entry) => (
              <li key={entry.month} className="flex items-center justify-between rounded-xl border border-slate-100 px-3 py-2">
                <span>{entry.month}</span>
                <span>{formatCurrency(entry.amount, primaryCurrency)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-xs text-slate-500">No giving activity captured for this period.</p>
        )}
      </div>
    </section>
  );
}
