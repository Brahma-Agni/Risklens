'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  CheckCheck,
  CircleDot,
  ShieldAlert,
  ShieldCheck,
  Waypoints,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const nav = [
  { label: 'High-risk links', href: '/', icon: ShieldAlert },
  { label: 'Actions taken', href: '/actions', icon: CheckCheck },
];

export function DashboardShell({
  children,
  title,
  eyebrow,
}: {
  children: React.ReactNode;
  title: string;
  eyebrow: string;
}) {
  const pathname = usePathname();
  return (
    <main className="min-h-screen bg-transparent text-foreground">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r-2 border-black bg-sidebar lg:flex lg:flex-col">
        <Link
          href="/"
          className="flex h-24 items-center gap-3 border-b-2 border-black bg-primary px-5"
        >
          <span className="grid size-11 place-items-center border-2 border-black bg-white shadow-[4px_4px_0_#000]">
            <Waypoints className="size-6 stroke-[3]" />
          </span>
          <span>
            <span className="block text-xl font-black tracking-[-.04em] uppercase">
              RiskLens
            </span>
            <span className="block text-[10px] font-extrabold tracking-[.18em] uppercase">
              Customer protection
            </span>
          </span>
        </Link>
        <div className="border-b-2 border-black bg-white px-5 py-3">
          <p className="flex items-center gap-2 text-[11px] font-extrabold tracking-[.1em] uppercase">
            <CircleDot className="size-4 fill-[#86efac] stroke-[3]" />
            AI monitoring live
          </p>
        </div>
        <nav className="space-y-2 p-3" aria-label="Main navigation">
          {nav.map((item) => {
            const baseHref = item.href.split('/latest')[0];
            const active =
              item.href === '/'
                ? pathname === '/'
                : pathname.startsWith(baseHref);
            return (
              <Link
                key={item.label}
                href={item.href}
                className={`flex min-h-11 items-center gap-3 border-2 border-black px-3 py-2 text-xs font-extrabold tracking-[.06em] uppercase transition-all duration-100 focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 ${active ? 'translate-x-1 bg-black text-white shadow-none' : 'bg-white shadow-[3px_3px_0_#000] hover:-translate-y-0.5 hover:bg-[#c4b5fd]'}`}
              >
                <item.icon className="size-4 stroke-[3]" />
                <span className="flex-1">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="m-3 mt-auto border-2 border-black bg-white p-4 shadow-[4px_4px_0_#000]">
          <div className="mb-2 flex items-center gap-2 text-xs font-black uppercase">
            <ShieldCheck className="size-5 fill-[#86efac] stroke-[3]" />
            Systems operational
          </div>
          <p className="text-xs font-semibold leading-5">
            Payments are stored, scored, verified, and routed to the support
            queue when intervention is needed.
          </p>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex min-h-20 items-center gap-3 border-b-2 border-black bg-[#fffdf5] px-4 py-3 md:px-8">
          <div className="min-w-0 flex-1">
            <p className="truncate text-[10px] font-extrabold tracking-[.15em] uppercase">
              Customer protection / {eyebrow}
            </p>
            <h1 className="truncate text-xl font-black tracking-[-.03em] md:text-2xl">
              {title}
            </h1>
          </div>
          <Badge className="hidden bg-[#86efac] sm:inline-flex">
            <span className="status-pulse" />
            Live
          </Badge>
        </header>

        <div className="border-b-2 border-black bg-secondary px-3 py-2 lg:hidden">
          <nav
            className="flex gap-2 overflow-x-auto pb-1"
            aria-label="Mobile navigation"
          >
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="whitespace-nowrap border-2 border-black bg-white px-3 py-2 text-[10px] font-extrabold tracking-[.06em] uppercase shadow-[2px_2px_0_#000]"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="space-y-7 p-4 pb-12 md:p-8">{children}</div>
      </div>
    </main>
  );
}

export function PageHeading({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 border-b-2 border-black pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h2 className="text-3xl font-black tracking-[-.045em] md:text-4xl">
          {title}
        </h2>
        <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-muted-foreground">
          {description}
        </p>
      </div>
      {action}
    </div>
  );
}
