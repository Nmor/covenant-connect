import React from 'react';

import type { CareFollowUp } from '../../../lib/admin-api';
import { getRecentCareFollowUps } from '../../../lib/admin-api';
import CareFollowUpList from '../_components/care-follow-up-list';

async function loadCareFollowUps(): Promise<CareFollowUp[]> {
  try {
    return await getRecentCareFollowUps(25);
  } catch (error) {
    console.error('Unable to load care follow-up records.', error);
    return [];
  }
}

export default async function CareFollowUpPage(): Promise<JSX.Element> {
  const items = await loadCareFollowUps();

  return (
    <div className="space-y-8">
      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">Care follow-up</h1>
        <p className="mt-2 text-sm text-slate-500">
          Review recent pastoral touchpoints, confirm next steps, and coordinate ministry outreach. Once the Prisma mutation
          endpoints are live, this page will support completing follow-ups, rescheduling, and escalating tasks.
        </p>
        <div className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-xs text-indigo-700">
          Tip: keep the Flask dashboard open while we finish the Next.js migration so you can cross-reference long-form member
          profiles.
        </div>
      </section>

      <CareFollowUpList
        description="The API returns the latest interactions first. Optimistic updates will slot in once mutations are available."
        heading="Pastoral interactions"
        items={items}
      />
    </div>
  );
}
