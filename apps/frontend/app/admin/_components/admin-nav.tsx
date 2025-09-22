'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

type NavItem = {
  href: string;
  label: string;
  external?: boolean;
};

const NAV_ITEMS = [
  { href: '/admin', label: 'Dashboard' },
  { href: '/admin/users', label: 'Users' },
  { href: '/admin/care', label: 'Care follow-up' },
  { href: '/admin/reports/metrics', label: 'Reporting API', external: true }
] satisfies readonly NavItem[];

export default function AdminNav(): JSX.Element {
  const pathname = usePathname();

  return (
    <nav aria-label="Admin navigation" className="space-y-1">
      {NAV_ITEMS.map((item) => {
        const isExternal = item.external === true;
        const isActive = isExternal
          ? false
          : pathname === item.href || pathname?.startsWith(`${item.href}/`);
        const baseClasses =
          'flex items-center justify-between rounded-xl px-4 py-2 text-sm font-medium transition';
        const activeClasses = isActive
          ? 'bg-indigo-50 text-indigo-600'
          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900';

        if (isExternal) {
          return (
            <a
              key={item.href}
              className={`${baseClasses} ${activeClasses}`}
              href={item.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              <span>{item.label}</span>
              <span aria-hidden className="text-xs text-slate-400">
                ↗
              </span>
            </a>
          );
        }

        return (
          <Link key={item.href} className={`${baseClasses} ${activeClasses}`} href={item.href}>
            <span>{item.label}</span>
            {isActive ? (
              <span className="text-xs uppercase tracking-widest text-indigo-500">Active</span>
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}
