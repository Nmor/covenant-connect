import React from 'react';

import type { DonationsResponse } from '../../lib/api';
import { getDonations } from '../../lib/api';

async function loadDonations(): Promise<DonationsResponse> {
  try {
    return await getDonations({ page: 1, pageSize: 25 });
  } catch (error) {
    console.error('Failed to load donations from API, returning fallback data.', error);
    return {
      data: [],
      total: 0,
      page: 1,
      pageSize: 0
    } satisfies DonationsResponse;
  }
}

const formatCurrency = (amount: number, currency: string) =>
  new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2
  }).format(amount);

const formatDateTime = (input: string) =>
  new Date(input).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });

const statusStyles: Record<string, string> = {
  completed: 'bg-emerald-100 text-emerald-700',
  pending: 'bg-amber-100 text-amber-700',
  failed: 'bg-rose-100 text-rose-700',
  refunded: 'bg-slate-100 text-slate-600'
};

export default async function DonationsPage() {
  const donations = await loadDonations();
  const completed = donations.data.filter((donation) => donation.status === 'completed');
  const totalGiven = completed.reduce((sum, donation) => sum + donation.amount, 0);
  const completionRate = donations.data.length
    ? (completed.length / donations.data.length) * 100
    : 0;

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-12">
      <header>
        <p className="text-sm font-medium uppercase tracking-wide text-indigo-500">Giving operations</p>
        <h1 className="mt-1 text-3xl font-semibold text-slate-900">Recent donations</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-500">
          These transactions mirror the in-memory donations repository exposed by the Nest API. Replace the service with
          Prisma once the SQL schema is ready.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2">
        <article className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <p className="text-xs uppercase tracking-wide text-slate-400">Completed giving</p>
          <p className="mt-3 text-2xl font-semibold text-slate-900">
            {donations.data.length
              ? formatCurrency(totalGiven, donations.data[0]?.currency ?? 'USD')
              : '$0.00'}
          </p>
          <p className="mt-2 text-sm text-slate-500">Summed from the sample Stripe, Paystack, and Flutterwave gifts.</p>
        </article>
        <article className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <p className="text-xs uppercase tracking-wide text-slate-400">Completion rate</p>
          <p className="mt-3 text-2xl font-semibold text-slate-900">{completionRate.toFixed(0)}%</p>
          <p className="mt-2 text-sm text-slate-500">Out of {donations.data.length} seeded transactions in memory.</p>
        </article>
      </section>

      {donations.data.length ? (
        <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-100">
            <thead className="bg-slate-50">
              <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <th scope="col" className="px-6 py-3">
                  Donor
                </th>
                <th scope="col" className="px-6 py-3">
                  Amount
                </th>
                <th scope="col" className="px-6 py-3">
                  Provider
                </th>
                <th scope="col" className="px-6 py-3">
                  Status
                </th>
                <th scope="col" className="px-6 py-3">
                  Received
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-600">
              {donations.data.map((donation) => (
                <tr key={donation.id}>
                  <td className="px-6 py-4">
                    {donation.memberId ? donation.memberId.replace('member-', '') : 'Guest donor'}
                  </td>
                  <td className="px-6 py-4 font-medium text-slate-900">
                    {formatCurrency(donation.amount, donation.currency)}
                  </td>
                  <td className="px-6 py-4 capitalize">{donation.provider}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                        statusStyles[donation.status] ?? 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {donation.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">{formatDateTime(donation.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <section className="rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-center">
          <p className="text-lg font-semibold text-slate-900">No donations yet</p>
          <p className="mt-2 text-sm text-slate-500">Seed data will appear here once the backend donation service populates records.</p>
        </section>
      )}
    </main>
  );
}
