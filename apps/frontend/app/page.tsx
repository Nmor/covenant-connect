import React from 'react';

import { getDashboardReport, getHomeContent, getUpcomingEvents } from '../lib/api';

type DashboardResponse = {
  kpis: { label: string; value: number; change?: number }[];
};

type EventsResponse = {
  data: { id: string; title: string; startsAt: string; location: string }[];
};

type HomeContentResponse = {
  heroTitle: string;
  heroSubtitle: string;
  highlights: string[];
  nextSteps: { label: string; url: string }[];
};

async function loadData() {
  try {
    const [home, report, events] = await Promise.all<[
      HomeContentResponse,
      DashboardResponse,
      EventsResponse
    ]>([getHomeContent(), getDashboardReport(), getUpcomingEvents()]);

    return { home, report, events };
  } catch (error) {
    console.error('Failed to reach API, falling back to placeholder data.', error);
    return {
      home: {
        heroTitle: 'Plan services and care pathways with ease',
        heroSubtitle:
          'The TypeScript rewrite ships with modular services for worship planning, assimilation, and giving.',
        highlights: [],
        nextSteps: [
          { label: 'Launch admin console', url: '/dashboard' },
          { label: 'Review API docs', url: '/docs' }
        ]
      },
      report: {
        kpis: [
          { label: 'Total Giving', value: 0 },
          { label: 'Completed Donations', value: 0 },
          { label: 'Upcoming Events', value: 0 }
        ]
      },
      events: {
        data: []
      }
    } satisfies {
      home: HomeContentResponse;
      report: DashboardResponse;
      events: EventsResponse;
    };
  }
}

export default async function HomePage() {
  const { home, report, events } = await loadData();

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-12 px-6 py-12">
      <section className="rounded-3xl bg-gradient-to-br from-indigo-600 via-purple-600 to-blue-600 p-10 text-white shadow-xl">
        <p className="text-sm uppercase tracking-widest text-indigo-200">Covenant Connect</p>
        <h1 className="mt-4 text-4xl font-semibold leading-tight md:text-5xl">{home.heroTitle}</h1>
        <p className="mt-4 max-w-2xl text-lg text-indigo-100">{home.heroSubtitle}</p>
        {home.highlights?.length ? (
          <ul className="mt-6 grid gap-2 text-sm text-indigo-100 md:grid-cols-2">
            {home.highlights.map((item) => (
              <li key={item} className="flex items-center gap-2">
                <span aria-hidden className="inline-flex h-2 w-2 rounded-full bg-indigo-200" />
                {item}
              </li>
            ))}
          </ul>
        ) : null}
        <div className="mt-8 flex flex-wrap gap-4">
          {home.nextSteps.map((step) => (
            <a
              key={step.url}
              className="rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font-medium backdrop-blur transition hover:bg-white/20"
              href={step.url}
            >
              {step.label}
            </a>
          ))}
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        {report.kpis.map((kpi) => (
          <article key={kpi.label} className="rounded-2xl bg-white p-6 shadow-sm">
            <p className="text-sm font-medium text-slate-500">{kpi.label}</p>
            <p className="mt-3 text-3xl font-semibold text-slate-900">
              {kpi.value.toLocaleString('en-US', { maximumFractionDigits: 2 })}
            </p>
            {typeof kpi.change === 'number' ? (
              <p className="mt-2 text-sm text-emerald-600">{kpi.change.toFixed(1)}% vs. last period</p>
            ) : null}
          </article>
        ))}
      </section>

      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <header className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-slate-900">Upcoming gatherings</h2>
          <a className="text-sm font-medium text-indigo-600" href="/events">
            View all
          </a>
        </header>
        <ul className="mt-6 space-y-4">
          {events.data.map((event) => (
            <li key={event.id} className="flex items-center justify-between rounded-xl border border-slate-100 p-4">
              <div>
                <p className="text-sm font-medium text-slate-500">
                  {new Date(event.startsAt).toLocaleDateString(undefined, {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric'
                  })}
                </p>
                <p className="text-lg font-semibold text-slate-900">{event.title}</p>
                <p className="text-sm text-slate-500">{event.location}</p>
              </div>
              <button className="rounded-full border border-indigo-200 px-4 py-2 text-sm font-medium text-indigo-600 transition hover:bg-indigo-50">
                Manage
              </button>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
