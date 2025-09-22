import './globals.css';
import type { Metadata } from 'next';
import Link from 'next/link';
import { Inter } from 'next/font/google';
import React from 'react';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Covenant Connect',
  description: 'A modern ministry platform reimagined in TypeScript.'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const currentYear = new Date().getFullYear();

  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 text-slate-900`}>
        <div className="flex min-h-screen flex-col">
          <header className="border-b border-slate-200 bg-white">
            <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
              <Link className="text-lg font-semibold text-indigo-600" href="/">
                Covenant Connect
              </Link>
              <nav className="flex items-center gap-6 text-sm font-medium text-slate-600">
                <Link className="transition hover:text-indigo-600" href="/">
                  Home
                </Link>
                <Link className="transition hover:text-indigo-600" href="/dashboard">
                  Dashboard
                </Link>
                <Link className="transition hover:text-indigo-600" href="/events">
                  Events
                </Link>
                <Link className="transition hover:text-indigo-600" href="/donations">
                  Donations
                </Link>
                <Link className="transition hover:text-indigo-600" href="/prayer">
                  Prayer
                </Link>
              </nav>
            </div>
          </header>
          <div className="flex-1">{children}</div>
          <footer className="border-t border-slate-200 bg-white">
            <div className="mx-auto w-full max-w-6xl px-6 py-4 text-sm text-slate-500">
              <p>
                © {currentYear} Covenant Connect. Prototype rebuilt in TypeScript while the production migration continues.
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
