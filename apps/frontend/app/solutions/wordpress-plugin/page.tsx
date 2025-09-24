import React from 'react';

const features = [
  {
    icon: '🔄',
    title: 'Real-time content sync',
    description:
      'Display sermons, devotionals, and events from Covenant Connect inside WordPress without duplicating work across dashboards.'
  },
  {
    icon: '🎨',
    title: 'Theme-aware blocks',
    description:
      'Drop responsive embeds that inherit your existing typography, colours, and spacing so the plugin feels native on day one.'
  },
  {
    icon: '🔐',
    title: 'Secure token authentication',
    description:
      'Issue time-limited access tokens from the SaaS portal so editors can connect safely without sharing database credentials.'
  }
] as const;

const launchSteps = [
  {
    title: 'Install',
    details: 'Upload the plugin ZIP in WordPress or install directly from the marketplace.'
  },
  {
    title: 'Connect',
    details: 'Paste your SaaS API key and choose which site collections to sync.'
  },
  {
    title: 'Publish',
    details: 'Place sermon, event, or donation blocks on any page and let automated sync handle the rest.'
  }
] as const;

const capabilities = [
  'Embed sermon video and audio players with automatic fallbacks',
  'Show curated event lists, calendars, and add-to-calendar buttons',
  'Create donation callouts that route supporters to secure Paystack or Fincra checkouts',
  'Capture prayer requests that post back to the SaaS pipeline in seconds'
] as const;

const operationalHighlights = [
  {
    title: 'Sync frequency',
    description: 'Content sync runs every five minutes, and you can trigger an instant refresh from either dashboard.'
  },
  {
    title: 'Staging friendly',
    description: 'Safely test updates on staging domains before promoting them live with one-click promotion.'
  },
  {
    title: 'Developer ready',
    description: 'Filters and actions expose templates, caching, and custom field mapping for agencies.'
  }
] as const;

const supportChannels = [
  {
    title: 'Documentation',
    description: 'Step-by-step guides covering shortcodes, Gutenberg blocks, and theme overrides.'
  },
  {
    title: 'Office hours',
    description: 'Live weekly Q&A sessions with our product specialists to troubleshoot complex builds.'
  },
  {
    title: 'Priority support',
    description: 'Impact plan customers receive 2-hour response SLAs across chat and email.'
  }
] as const;

const faqs = [
  {
    question: 'Does the plugin work with multisite?',
    answer: 'Yes, each site can authenticate with its own API token and choose unique content feeds.'
  },
  {
    question: 'Can developers extend the plugin?',
    answer: 'Hooks and filters are available for custom taxonomies, templates, and caching strategies.'
  },
  {
    question: 'How often does sync occur?',
    answer: 'By default content updates every five minutes, and you can trigger an instant sync from the WordPress dashboard.'
  }
] as const;

export const metadata = {
  title: 'WordPress Plugin | Covenant Connect',
  description:
    'Embed synced sermons, events, and donation prompts on any WordPress site with the Covenant Connect plugin.'
};

export default function WordPressPluginPage(): React.ReactElement {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-12 px-6 py-12">
      <section className="rounded-3xl bg-gradient-to-br from-sky-500 via-indigo-500 to-purple-600 p-10 text-white shadow-xl">
        <p className="text-sm uppercase tracking-[0.3em] text-sky-100">WordPress integration</p>
        <h1 className="mt-4 text-4xl font-semibold leading-tight md:text-5xl">
          Publish ministry content in minutes
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-sky-50">
          Install the Covenant Connect WordPress plugin to sync sermons, events, and donation prompts straight from your SaaS
          dashboard without copying and pasting.
        </p>
        <div className="mt-8 flex flex-wrap gap-4">
          <a
            className="inline-flex items-center justify-center rounded-full bg-white px-5 py-2 text-sm font-semibold text-indigo-600 shadow transition hover:bg-indigo-50"
            href="mailto:support@covenantconnect.com?subject=WordPress%20Plugin%20Access"
          >
            Request download
          </a>
          <a
            className="inline-flex items-center justify-center rounded-full border border-white/30 px-5 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
            href="/dashboard"
          >
            Explore SaaS platform
          </a>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        {features.map((feature) => (
          <article key={feature.title} className="rounded-2xl bg-white p-6 shadow-sm">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 text-2xl">
              {feature.icon}
            </span>
            <h2 className="mt-4 text-xl font-semibold text-slate-900">{feature.title}</h2>
            <p className="mt-2 text-sm text-slate-500">{feature.description}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-semibold text-slate-900">Three steps to launch</h2>
          <ol className="mt-6 space-y-4">
            {launchSteps.map((step, index) => (
              <li key={step.title} className="flex gap-4">
                <span className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-base font-semibold text-indigo-600">
                  {index + 1}
                </span>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">{step.title}</h3>
                  <p className="mt-1 text-sm text-slate-500">{step.details}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-semibold text-slate-900">What you can build</h2>
          <p className="mt-2 text-sm text-slate-500">Drag-and-drop blocks make it easy to keep your website fresh.</p>
          <ul className="mt-4 space-y-3 text-sm text-slate-600">
            {capabilities.map((item) => (
              <li key={item} className="flex items-start gap-3">
                <span aria-hidden className="mt-1 inline-flex h-2 w-2 rounded-full bg-indigo-500" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        {operationalHighlights.map((highlight) => (
          <article key={highlight.title} className="rounded-2xl bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">{highlight.title}</h3>
            <p className="mt-2 text-sm text-slate-500">{highlight.description}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-semibold text-slate-900">Plugin support</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            {supportChannels.map((channel) => (
              <article key={channel.title} className="rounded-xl bg-indigo-50 p-4 text-indigo-900">
                <h3 className="text-sm font-semibold uppercase tracking-wide">{channel.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-indigo-800">{channel.description}</p>
              </article>
            ))}
          </div>
        </div>
        <aside className="rounded-2xl bg-indigo-600 p-6 text-white shadow-lg">
          <h2 className="text-2xl font-semibold">Need the SaaS backend?</h2>
          <p className="mt-3 text-sm text-indigo-100">
            Launch the full Covenant Connect platform to manage your content, donors, and teams with a single login.
          </p>
          <a
            className="mt-6 inline-flex w-full items-center justify-center rounded-full bg-white px-5 py-2 text-sm font-semibold text-indigo-600 transition hover:bg-indigo-100"
            href="/dashboard"
          >
            Start with SaaS
          </a>
        </aside>
      </section>

      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-semibold text-slate-900">Frequently asked questions</h2>
        <div className="mt-6 space-y-4">
          {faqs.map((faq) => (
            <details key={faq.question} className="group rounded-xl border border-slate-200 p-4">
              <summary className="flex cursor-pointer items-center justify-between gap-4 text-left text-sm font-semibold text-slate-900">
                {faq.question}
                <span className="text-lg text-indigo-500 transition group-open:rotate-45">+</span>
              </summary>
              <p className="mt-3 text-sm text-slate-600">{faq.answer}</p>
            </details>
          ))}
        </div>
      </section>
    </main>
  );
}
