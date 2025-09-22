import React from 'react';

import type { EventsResponse } from '../../lib/api';
import { API_BASE_URL, getEvents } from '../../lib/api';

async function loadEvents(): Promise<EventsResponse> {
  try {
    return await getEvents({ page: 1, pageSize: 12 });
  } catch (error) {
    console.error('Failed to load events from API, returning fallback data.', error);
    return {
      data: [],
      total: 0,
      page: 1,
      pageSize: 0
    } satisfies EventsResponse;
  }
}

const formatDate = (input: string, options: Intl.DateTimeFormatOptions) =>
  new Date(input).toLocaleString(undefined, options);

export default async function EventsPage() {
  const events = await loadEvents();

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-12">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-indigo-500">Ministry planner</p>
          <h1 className="mt-1 text-3xl font-semibold text-slate-900">Upcoming gatherings</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-500">
            Events are seeded from the NestJS service so the dashboard has realistic data while Prisma integration is under
            construction.
          </p>
        </div>
        <a
          className="inline-flex items-center justify-center rounded-full border border-indigo-200 px-4 py-2 text-sm font-medium text-indigo-600 transition hover:bg-indigo-50"
          href={`${API_BASE_URL}/events/calendar.ics`}
        >
          Download calendar (.ics)
        </a>
      </header>

      {events.data.length ? (
        <ul className="space-y-4">
          {events.data.map((event) => (
            <li key={event.id} className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">
                    {formatDate(event.startsAt, {
                      weekday: 'short',
                      month: 'short',
                      day: 'numeric'
                    })}{' '}
                    · {formatDate(event.startsAt, { hour: 'numeric', minute: '2-digit' })} —
                    {formatDate(event.endsAt, { hour: 'numeric', minute: '2-digit' })} {event.timezone}
                  </p>
                  <h2 className="mt-1 text-xl font-semibold text-slate-900">{event.title}</h2>
                  <p className="text-sm text-slate-500">{event.location}</p>
                  {event.tags?.length ? (
                    <ul className="mt-3 flex flex-wrap gap-2 text-xs text-indigo-600">
                      {event.tags.map((tag) => (
                        <li key={tag} className="rounded-full bg-indigo-50 px-3 py-1 font-medium">
                          #{tag}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
                <div className="flex gap-3">
                  <button className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50">
                    Edit event
                  </button>
                  <button className="rounded-full border border-indigo-200 bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500">
                    Manage team
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <section className="rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-center">
          <p className="text-lg font-semibold text-slate-900">No events scheduled yet</p>
          <p className="mt-2 text-sm text-slate-500">
            Start creating gatherings in the NestJS backend or via the API to see them appear here.
          </p>
        </section>
      )}
    </main>
  );
}
