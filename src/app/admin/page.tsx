"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { inr } from "@/lib/format";
import { AdminShell, Bars } from "@/components/admin";
import { Card, ErrorState, Skeleton } from "@/components/ui";

interface Overview {
  revenue: number; orders: number; customers: number; products: number;
  avg_order_value: number; low_stock_count: number; conversion_rate: number; refunds: number;
  revenue_series: { date: string; revenue: number; orders: number }[];
  top_products: { name: string; qty: number; revenue: number }[];
  category_split: { name: string; count: number }[];
}

export default function AdminOverview() {
  const q = useQuery({
    queryKey: ["admin-overview"],
    queryFn: () => apiFetch<Overview>("/admin/overview", { auth: true }),
  });

  return (
    <AdminShell>
      <h1 className="text-xl font-bold">Dashboard</h1>
      {q.isLoading ? <Skeleton className="mt-3 h-60" /> :
        q.isError ? <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /> : (
        <>
          <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[
              ["Revenue", inr(q.data!.revenue)],
              ["Orders", String(q.data!.orders)],
              ["Customers", String(q.data!.customers)],
              ["Avg order value", inr(q.data!.avg_order_value)],
              ["Conversion", `${q.data!.conversion_rate}%`],
              ["Products", String(q.data!.products)],
              ["Low stock", String(q.data!.low_stock_count)],
              ["Refunds", String(q.data!.refunds)],
            ].map(([k, v]) => (
              <Card key={k} className="p-3">
                <p className="text-xs text-zinc-500">{k}</p>
                <p className="text-xl font-bold">{v}</p>
              </Card>
            ))}
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <Card className="p-4">
              <p className="text-sm font-medium">Revenue · last 14 days</p>
              <Bars data={q.data!.revenue_series} />
            </Card>
            <Card className="p-4">
              <p className="text-sm font-medium">Orders · last 14 days</p>
              <Bars data={q.data!.revenue_series} valueKey="orders" />
            </Card>
            <Card className="p-4">
              <p className="text-sm font-medium">Top products</p>
              <ul className="mt-2 space-y-1 text-sm">
                {q.data!.top_products.map((t) => (
                  <li key={t.name} className="flex justify-between gap-2">
                    <span className="truncate">{t.name}</span>
                    <span className="text-zinc-500">{t.qty} sold · {inr(t.revenue)}</span>
                  </li>
                ))}
              </ul>
            </Card>
            <Card className="p-4">
              <p className="text-sm font-medium">Category split</p>
              <ul className="mt-2 space-y-1 text-sm">
                {q.data!.category_split.map((c) => (
                  <li key={c.name} className="flex justify-between"><span>{c.name}</span><span className="text-zinc-500">{c.count}</span></li>
                ))}
              </ul>
              <Link href="/admin/analytics" className="mt-2 inline-block text-sm underline">Full analytics →</Link>
            </Card>
          </div>
        </>
      )}
    </AdminShell>
  );
}
