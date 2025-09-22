'use client';

import React, { useMemo, useState, useTransition } from 'react';

import type { AdminUserRecord } from '../../../lib/admin-api';
import { createUserAction, deleteUserAction, updateUserAction } from './actions';

const sortUsers = (list: AdminUserRecord[]): AdminUserRecord[] =>
  [...list].sort((a, b) => a.username.localeCompare(b.username, undefined, { sensitivity: 'base' }));

type Feedback = {
  type: 'success' | 'error' | 'info';
  text: string;
};

type UserManagementProps = {
  initialUsers: AdminUserRecord[];
};

type EditFormState = {
  username: string;
  email: string;
  password: string;
  isAdmin: boolean;
};

const emptyEditForm: EditFormState = {
  username: '',
  email: '',
  password: '',
  isAdmin: false
};

export default function UserManagement({ initialUsers }: UserManagementProps): JSX.Element {
  const [users, setUsers] = useState<AdminUserRecord[]>(() => sortUsers(initialUsers));
  const [message, setMessage] = useState<Feedback | null>(null);
  const [isPending, startTransition] = useTransition();
  const [editingUser, setEditingUser] = useState<AdminUserRecord | null>(null);
  const [editForm, setEditForm] = useState<EditFormState>(emptyEditForm);

  const totalAdmins = useMemo(() => users.filter((user) => user.isAdmin).length, [users]);

  const handleCreateSubmit: React.FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);

    const payload = {
      username: String(formData.get('username') ?? '').trim(),
      email: String(formData.get('email') ?? '').trim(),
      password: String(formData.get('password') ?? ''),
      isAdmin: formData.get('isAdmin') === 'on'
    };

    if (!payload.username || !payload.email || !payload.password) {
      setMessage({ type: 'error', text: 'Username, email, and password are required.' });
      return;
    }

    const optimisticUser: AdminUserRecord = {
      id: `temp-${Date.now()}`,
      username: payload.username,
      email: payload.email,
      isAdmin: payload.isAdmin,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      lastLoginAt: null
    };

    setUsers((prev) => sortUsers([...prev, optimisticUser]));
    setMessage({ type: 'info', text: 'Creating user…' });
    form.reset();

    startTransition(async () => {
      const result = await createUserAction(payload);
      if (result.status === 'success' && result.user) {
        const createdUser = result.user;
        setUsers((prev) => sortUsers(prev.map((user) => (user.id === optimisticUser.id ? createdUser : user))));
        setMessage({ type: 'success', text: `Created ${createdUser.username}.` });
      } else {
        setUsers((prev) => prev.filter((user) => user.id !== optimisticUser.id));
        setMessage({ type: 'error', text: result.status === 'error' ? result.message : 'Unable to create user.' });
      }
    });
  };

  const startEditing = (user: AdminUserRecord) => {
    setEditingUser(user);
    setEditForm({ username: user.username, email: user.email, password: '', isAdmin: user.isAdmin });
    setMessage(null);
  };

  const cancelEditing = () => {
    setEditingUser(null);
    setEditForm(emptyEditForm);
  };

  const handleEditChange = (key: keyof EditFormState, value: string | boolean) => {
    setEditForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleUpdateSubmit: React.FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    if (!editingUser) {
      return;
    }

    if (!editForm.username.trim() || !editForm.email.trim()) {
      setMessage({ type: 'error', text: 'Username and email are required.' });
      return;
    }

    const payload = {
      id: editingUser.id,
      username: editForm.username.trim(),
      email: editForm.email.trim(),
      password: editForm.password.trim() || undefined,
      isAdmin: editForm.isAdmin
    };

    const originalUser = editingUser;
    const optimisticUser: AdminUserRecord = {
      ...editingUser,
      username: payload.username,
      email: payload.email,
      isAdmin: payload.isAdmin,
      updatedAt: new Date().toISOString()
    };

    setUsers((prev) => sortUsers(prev.map((user) => (user.id === originalUser.id ? optimisticUser : user))));
    setMessage({ type: 'info', text: 'Saving changes…' });

    startTransition(async () => {
      const result = await updateUserAction(payload);
      if (result.status === 'success' && result.user) {
        const savedUser = result.user;
        setUsers((prev) => sortUsers(prev.map((user) => (user.id === originalUser.id ? savedUser : user))));
        setEditingUser(savedUser);
        setEditForm((prevState) => ({ ...prevState, password: '' }));
        setMessage({ type: 'success', text: `Updated ${savedUser.username}.` });
      } else {
        setUsers((prev) => sortUsers(prev.map((user) => (user.id === originalUser.id ? originalUser : user))));
        setMessage({ type: 'error', text: result.status === 'error' ? result.message : 'Unable to update user.' });
      }
    });
  };

  const handleDelete = (user: AdminUserRecord) => {
    const previousUsers = users;
    setUsers((prev) => prev.filter((existing) => existing.id !== user.id));
    setMessage({ type: 'info', text: `Removing ${user.username}…` });
    if (editingUser?.id === user.id) {
      cancelEditing();
    }

    startTransition(async () => {
      const result = await deleteUserAction(user.id);
      if (result.status === 'deleted') {
        setMessage({ type: 'success', text: `${user.username} removed.` });
      } else {
        setUsers(previousUsers);
        setMessage({ type: 'error', text: result.status === 'error' ? result.message : 'Unable to delete user.' });
      }
    });
  };

  return (
    <div className="space-y-8">
      {message ? (
        <div
          aria-live="polite"
          className={`rounded-xl border px-4 py-3 text-sm ${
            message.type === 'success'
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
              : message.type === 'error'
              ? 'border-rose-200 bg-rose-50 text-rose-700'
              : 'border-indigo-200 bg-indigo-50 text-indigo-700'
          }`}
        >
          {message.text}
        </div>
      ) : null}

      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Invite a new user</h2>
        <p className="mt-2 text-sm text-slate-500">
          Accounts are created immediately through the Prisma API. Use the admin toggle for staff who should access reports and
          automations.
        </p>
        <form className="mt-6 grid gap-4 sm:grid-cols-2" onSubmit={handleCreateSubmit}>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            Username
            <input
              className="mt-1 rounded-xl border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              maxLength={100}
              name="username"
              placeholder="e.g. adefemi"
              required
              type="text"
            />
          </label>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            Email
            <input
              className="mt-1 rounded-xl border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              name="email"
              placeholder="team@covenant.cc"
              required
              type="email"
            />
          </label>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            Temporary password
            <input
              className="mt-1 rounded-xl border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              minLength={8}
              name="password"
              placeholder="Send a reset link after creation"
              required
              type="password"
            />
          </label>
          <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <input
              className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              name="isAdmin"
              type="checkbox"
            />
            Grant admin access
          </label>
          <div className="sm:col-span-2">
            <button
              className="inline-flex items-center rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-70"
              disabled={isPending}
              type="submit"
            >
              Create user
            </button>
          </div>
        </form>
      </section>

      {editingUser ? (
        <section className="rounded-2xl bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold text-slate-900">Edit {editingUser.username}</h2>
            <button
              className="text-sm font-medium text-slate-500 hover:text-slate-900"
              onClick={cancelEditing}
              type="button"
            >
              Cancel
            </button>
          </div>
          <form className="mt-6 grid gap-4 sm:grid-cols-2" onSubmit={handleUpdateSubmit}>
            <label className="flex flex-col text-sm font-medium text-slate-700">
              Username
              <input
                className="mt-1 rounded-xl border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                onChange={(event) => handleEditChange('username', event.target.value)}
                required
                type="text"
                value={editForm.username}
              />
            </label>
            <label className="flex flex-col text-sm font-medium text-slate-700">
              Email
              <input
                className="mt-1 rounded-xl border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                onChange={(event) => handleEditChange('email', event.target.value)}
                required
                type="email"
                value={editForm.email}
              />
            </label>
            <label className="flex flex-col text-sm font-medium text-slate-700">
              New password (optional)
              <input
                className="mt-1 rounded-xl border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
                onChange={(event) => handleEditChange('password', event.target.value)}
                placeholder="Leave blank to keep the current password"
                type="password"
                value={editForm.password}
              />
            </label>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input
                checked={editForm.isAdmin}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                onChange={(event) => handleEditChange('isAdmin', event.target.checked)}
                type="checkbox"
              />
              Admin access
            </label>
            <div className="sm:col-span-2">
              <button
                className="inline-flex items-center rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-70"
                disabled={isPending}
                type="submit"
              >
                Save changes
              </button>
            </div>
          </form>
        </section>
      ) : null}

      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Team directory</h2>
            <p className="text-sm text-slate-500">{users.length} users · {totalAdmins} admins</p>
          </div>
        </div>
        {users.length ? (
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full text-left text-sm text-slate-600">
              <thead className="text-slate-400">
                <tr>
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Email</th>
                  <th className="py-2 pr-4 font-medium">Role</th>
                  <th className="py-2 pr-4 font-medium">Updated</th>
                  <th className="py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-t border-slate-100">
                    <td className="py-2 pr-4 font-medium text-slate-900">{user.username}</td>
                    <td className="py-2 pr-4">{user.email}</td>
                    <td className="py-2 pr-4">
                      <span
                        className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                          user.isAdmin ? 'bg-indigo-50 text-indigo-600' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {user.isAdmin ? 'Admin' : 'User'}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-xs text-slate-500">
                      {new Date(user.updatedAt).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                    </td>
                    <td className="py-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-600 transition hover:border-indigo-200 hover:text-indigo-600"
                          disabled={isPending}
                          onClick={() => startEditing(user)}
                          type="button"
                        >
                          Edit
                        </button>
                        <button
                          className="rounded-full border border-rose-200 px-3 py-1 text-xs font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                          disabled={isPending}
                          onClick={() => handleDelete(user)}
                          type="button"
                        >
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-6 text-sm text-slate-500">No users found. Add your first teammate to get started.</p>
        )}
      </section>
    </div>
  );
}
