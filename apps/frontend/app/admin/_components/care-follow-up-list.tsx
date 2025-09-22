import React from 'react';

import type { CareFollowUp } from '../../../lib/admin-api';

type CareFollowUpListProps = {
  items: CareFollowUp[];
  heading?: string;
  description?: string;
};

const formatDate = (iso: string): string => {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleDateString(undefined, { dateStyle: 'medium' });
};

const formatInteractionType = (value: string): string =>
  value
    .split('_')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');

export default function CareFollowUpList({
  items,
  heading = 'Recent care follow-up',
  description = 'Latest pastoral touchpoints and outstanding follow-ups.'
}: CareFollowUpListProps): JSX.Element {
  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{heading}</h2>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
          {items.length} records
        </span>
      </header>

      {items.length ? (
        <ul className="mt-6 space-y-3">
          {items.map((item) => (
            <li key={item.id} className="rounded-xl border border-slate-100 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{item.memberName}</p>
                  <p className="text-xs text-slate-500">
                    {formatInteractionType(item.interactionType)} · {formatDate(item.interactionDate)}
                  </p>
                </div>
                {item.followUpRequired ? (
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
                    Follow-up required
                    {item.followUpDate ? ` · ${formatDate(item.followUpDate)}` : null}
                  </span>
                ) : null}
              </div>
              {item.notes ? <p className="mt-3 text-sm text-slate-600">{item.notes}</p> : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-6 text-sm text-slate-500">No follow-up activity recorded for this timeframe.</p>
      )}
    </section>
  );
}
