import React from 'react';
import type { Metadata } from 'next';

import AdminNav from './_components/admin-nav';

export const metadata: Metadata = {
  title: 'Admin | Covenant Connect',
  description: 'Secure dashboards and workflows for Covenant Connect administrators.'
};

type AdminLayoutProps = {
  children: React.ReactNode;
};

export default function AdminLayout({ children }: AdminLayoutProps): JSX.Element {
  return (
    <div className="bg-slate-50 py-12">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 lg:flex-row">
        <aside className="lg:w-64">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-widest text-indigo-500">Admin console</p>
            <h1 className="mt-2 text-xl font-semibold text-slate-900">Leadership tools</h1>
            <p className="mt-2 text-sm text-slate-500">
              Authenticate against the Nest/Prisma services before running production workflows. Demo data is safe to explore.
            </p>
            <div className="mt-6">
              <AdminNav />
            </div>
          </div>
        </aside>
        <main className="flex-1 space-y-8">{children}</main>
      </div>
    </div>
  );
}
