import React from 'react';

import type { AdminUserRecord } from '../../../lib/admin-api';
import { getAdminUsers } from '../../../lib/admin-api';
import UserManagement from './user-management';

async function loadUsers(): Promise<AdminUserRecord[]> {
  try {
    const response = await getAdminUsers();
    return response.users;
  } catch (error) {
    console.error('Unable to load admin users.', error);
    return [];
  }
}

export default async function AdminUsersPage(): Promise<JSX.Element> {
  const users = await loadUsers();

  return (
    <div className="space-y-8">
      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">User management</h1>
        <p className="mt-2 text-sm text-slate-500">
          Manage staff accounts, promote admins, and prepare for the upcoming Prisma-based authentication rollout. All
          mutations optimistically update the table and surface clear error states if the API is offline.
        </p>
      </section>

      <UserManagement initialUsers={users} />
    </div>
  );
}
