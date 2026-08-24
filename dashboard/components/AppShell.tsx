"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout, getEmail } from "@/lib/auth";
import { Badge } from "@/components/ui";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/",
    label: "Overview",
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
      </svg>
    ),
  },
  {
    href: "/traces",
    label: "Traces",
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
      </svg>
    ),
  },
  {
    href: "/playground",
    label: "Playground",
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    href: "/agents",
    label: "Agents",
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
      </svg>
    ),
  },
];

const CONFIGURE_ITEMS: NavItem[] = [
  {
    href: "/settings",
    label: "Settings",
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
];

function NavGroup({ label, items, pathname }: { label: string; items: NavItem[]; pathname: string }) {
  return (
    <div role="group" aria-label={label}>
      <p className="px-2 pt-3 pb-1 text-[9px] font-bold uppercase tracking-[0.14em] text-fg-faint">
        {label}
      </p>
      {items.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-all duration-150 w-full relative ${
              active
                ? "bg-gradient-to-r from-brand/10 to-transparent text-brand border-l-2 border-brand"
                : "text-fg-subtle hover:bg-surface-2/50 hover:text-fg border-l-2 border-transparent"
            }`}
          >
            <span className={`flex-shrink-0 transition-colors ${active ? "text-brand" : "text-fg-faint group-hover:text-fg-muted"}`}>
              {item.icon}
            </span>
            <span className="truncate">{item.label}</span>
          </Link>
        );
      })}
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const email = getEmail();

  return (
    <div className="min-h-screen flex bg-bg">
      {/* ── Left sidebar ─────────────────────────────────────────────── */}
      <aside className="w-56 flex-shrink-0 border-r border-line bg-bg">
        <nav aria-label="Primary" className="sticky top-0 flex h-screen flex-col overflow-y-auto px-2 py-4">
          <div className="mb-1 border-b border-line/60 px-1 py-3">
            <p className="text-[10px] font-medium text-fg-faint">v0.1.0 · open source</p>
          </div>
          <NavGroup label="Observe" items={NAV_ITEMS} pathname={pathname} />
          <div className="my-0.5 mx-2 border-t border-line/50" />
          <NavGroup label="Configure" items={CONFIGURE_ITEMS} pathname={pathname} />
        </nav>
      </aside>

      {/* ── Right column: header + main ──────────────────────────────── */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-40 border-b border-line bg-bg/90 backdrop-blur-lg">
          <div className="flex items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
            {/* Brand */}
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 shadow-lg shadow-cyan-500/20">
                <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-base font-bold text-fg tracking-tight">TokenSight</h1>
                  <Badge tone="neutral" size="sm" className="uppercase tracking-wider">
                    Open Source
                  </Badge>
                </div>
                <p className="hidden text-[11px] text-fg-subtle sm:block leading-tight">
                  AI Observability &amp; Instrumentation
                </p>
              </div>
            </div>

            {/* Right: status + account */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 rounded-full border border-success/20 bg-success/10 px-2.5 py-1">
                <span className="h-1.5 w-1.5 rounded-full bg-success" />
                <span className="text-xs font-medium text-success">Live</span>
              </div>

              {email && (
                <span className="hidden text-xs text-fg-subtle sm:block">{email}</span>
              )}

              <button
                title="Sign out"
                aria-label="Sign out"
                onClick={() => {
                  logout();
                  router.push("/login");
                }}
                className="flex items-center justify-center rounded-lg border border-line-strong bg-surface-2 hover:bg-surface-3 p-2 text-fg-muted hover:text-fg transition-colors"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                  />
                </svg>
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 min-w-0 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
