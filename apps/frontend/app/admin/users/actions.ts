'use server';

import { revalidatePath } from 'next/cache';

import type {
  AdminUserRecord,
  CreateAdminUserInput,
  UpdateAdminUserInput
} from '../../../lib/admin-api';
import { createAdminUser, deleteAdminUser, updateAdminUser } from '../../../lib/admin-api';

export type UserActionResult =
  | { status: 'success'; user?: AdminUserRecord }
  | { status: 'deleted' }
  | { status: 'error'; message: string };

const GENERIC_ERROR =
  'The admin API did not respond. Please verify the Nest/Prisma service is running and try again.';

export async function createUserAction(input: CreateAdminUserInput): Promise<UserActionResult> {
  try {
    const user = await createAdminUser(input);
    revalidatePath('/admin/users');
    return { status: 'success', user };
  } catch (error) {
    console.error('Failed to create admin user.', error);
    return { status: 'error', message: GENERIC_ERROR };
  }
}

export async function updateUserAction(input: UpdateAdminUserInput): Promise<UserActionResult> {
  try {
    const user = await updateAdminUser(input);
    revalidatePath('/admin/users');
    return { status: 'success', user };
  } catch (error) {
    console.error('Failed to update admin user.', error);
    return { status: 'error', message: GENERIC_ERROR };
  }
}

export async function deleteUserAction(id: string): Promise<UserActionResult> {
  try {
    await deleteAdminUser(id);
    revalidatePath('/admin/users');
    return { status: 'deleted' };
  } catch (error) {
    console.error('Failed to delete admin user.', error);
    return { status: 'error', message: GENERIC_ERROR };
  }
}
