const TRUE_VALUES = new Set(['1', 'true', 't', 'yes', 'y', 'on']);

export function getString(credentials: Record<string, string>, key: string): string {
  const value = credentials[key];
  if (typeof value !== 'string') {
    return '';
  }

  return value.trim();
}

export function parseBoolean(value: string | undefined): boolean {
  if (!value) {
    return false;
  }

  return TRUE_VALUES.has(value.trim().toLowerCase());
}

export function cloneCredentials(credentials: Record<string, string>): Record<string, string> {
  return Object.entries(credentials).reduce<Record<string, string>>((acc, [key, value]) => {
    acc[key] = typeof value === 'string' ? value : String(value ?? '');
    return acc;
  }, {});
}
