"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/stores/auth";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/products", label: "Products" },
  { href: "/admin/orders", label: "Orders" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/inventory", label: "Inventory" },
  { href: "/admin/analytics", label: "Analytics" },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const { user, ready } = useAuth();
  const router = useRouter();
  const path = usePathname();
  const allowed = user && (user.role === "admin" || user.role === "manager");

  useEffect(() => {
    if (ready && !allowed) router.replace("/login");
  }, [ready, allowed, router]);

  if (!ready) return <p className="py-10 text-sm text-zinc-500">Loading…</p>;
  if (!allowed) return <p className="py-10 text-sm text-zinc-500">Admin access required.</p>;

  return (
    <div className="grid gap-6 py-6 lg:grid-cols-[200px_1fr]">
      <nav className="flex gap-1 overflow-x-auto lg:flex-col">
        {NAV.map((n) => (
          <Link key={n.href} href={n.href}
            className={cn("whitespace-nowrap rounded-lg px-3 py-2 text-sm",
              path === n.href ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900 font-medium" : "hover:bg-zinc-100 dark:hover:bg-zinc-800")}>
            {n.label}
          </Link>
        ))}
      </nav>
      <div>{children}</div>
    </div>
  );
}

export function Bars({ data, valueKey = "revenue", labelKey = "date" }: { data: Record<string, unknown>[]; valueKey?: string; labelKey?: string }) {
  const vals = data.map((d) => Number(d[valueKey] ?? 0));
  const max = Math.max(1, ...vals);
  return (
    <div className="flex h-40 items-end gap-1">
      {data.map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1" title={`${String(d[labelKey])}: ${vals[i]}`}>
          <div className="w-full rounded-t bg-zinc-900 dark:bg-zinc-100" style={{ height: `${Math.max(3, (vals[i] / max) * 140)}px` }} />
          {i % 2 === 0 && <span className="text-[9px] text-zinc-400">{String(d[labelKey]).slice(5)}</span>}
        </div>
      ))}
    </div>
  );
}
