import React from 'react';

import type { PrayerRequestsResponse } from '../../lib/api';
import { getPrayerRequests } from '../../lib/api';

async function loadPrayerRequests(): Promise<PrayerRequestsResponse> {
  try {
    return await getPrayerRequests();
  } catch (error) {
    console.error('Failed to load prayer requests from API, returning fallback data.', error);
    return {
      data: [],
      total: 0,
      page: 1,
      pageSize: 0
    } satisfies PrayerRequestsResponse;
  }
}

const statusLabels: Record<string, string> = {
  new: 'New',
  assigned: 'Assigned',
  praying: 'In progress',
  answered: 'Answered'
};

const statusStyles: Record<string, string> = {
  new: 'bg-indigo-100 text-indigo-700',
  assigned: 'bg-amber-100 text-amber-700',
  praying: 'bg-emerald-100 text-emerald-700',
  answered: 'bg-slate-100 text-slate-600'
};

const formatDateTime = (input: string) =>
  new Date(input).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });

export default async function PrayerPage() {
  const requests = await loadPrayerRequests();
  const openRequests = requests.data.filter((request) => request.status !== 'answered');
  const nextFollowUp = requests.data
    .filter((request) => request.followUpAt)
    .map((request) => ({ request, date: new Date(request.followUpAt!) }))
    .sort((a, b) => a.date.getTime() - b.date.getTime())[0];

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-12">
      <header>
        <p className="text-sm font-medium uppercase tracking-wide text-indigo-500">Care follow-up</p>
        <h1 className="mt-1 text-3xl font-semibold text-slate-900">Prayer requests</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-500">
          The connected dashboard surfaces realistic pastoral-care metrics using in-memory data until the queue and messaging
          infrastructure ships.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2">
        <article className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <p className="text-xs uppercase tracking-wide text-slate-400">Open requests</p>
          <p className="mt-3 text-2xl font-semibold text-slate-900">{openRequests.length}</p>
          <p className="mt-2 text-sm text-slate-500">Includes new, assigned, and praying statuses.</p>
        </article>
        <article className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <p className="text-xs uppercase tracking-wide text-slate-400">Next follow-up</p>
          <p className="mt-3 text-2xl font-semibold text-slate-900">
            {nextFollowUp ? formatDateTime(nextFollowUp.date.toISOString()) : 'None scheduled'}
          </p>
          {nextFollowUp ? (
            <p className="mt-2 text-sm text-slate-500">
              Assigned to <span className="font-medium">{nextFollowUp.request.requesterName}</span>.
            </p>
          ) : (
            <p className="mt-2 text-sm text-slate-500">Add follow-up reminders in the API to track pastoral care touches.</p>
          )}
        </article>
      </section>

      {requests.data.length ? (
        <ul className="space-y-4">
          {requests.data.map((request) => (
            <li key={request.id} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <h2 className="text-lg font-semibold text-slate-900">{request.requesterName}</h2>
                    <span
                      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                        statusStyles[request.status] ?? 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {statusLabels[request.status] ?? request.status}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{request.message}</p>
                  <dl className="mt-4 grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
                    <div>
                      <dt className="font-medium text-slate-400">Submitted</dt>
                      <dd>{formatDateTime(request.createdAt)}</dd>
                    </div>
                    {request.followUpAt ? (
                      <div>
                        <dt className="font-medium text-slate-400">Follow-up</dt>
                        <dd>{formatDateTime(request.followUpAt)}</dd>
                      </div>
                    ) : null}
                  </dl>
                </div>
                <div className="flex flex-col gap-3 text-sm text-indigo-600">
                  {request.requesterEmail ? (
                    <a className="font-medium" href={`mailto:${request.requesterEmail}`}>
                      Email requester
                    </a>
                  ) : null}
                  {request.requesterPhone ? (
                    <a className="font-medium" href={`tel:${request.requesterPhone}`}>
                      Call requester
                    </a>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <section className="rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-center">
          <p className="text-lg font-semibold text-slate-900">No prayer requests logged</p>
          <p className="mt-2 text-sm text-slate-500">Use the Nest API to create sample records while the admin console evolves.</p>
        </section>
      )}
    </main>
  );
}
