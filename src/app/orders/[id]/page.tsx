"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { inr } from "@/lib/format";
import { Badge, Card, Empty, ErrorState, Skeleton } from "@/components/ui";
import { useAuth } from "@/stores/auth";
import type { Order } from "@/types";

const STAGES = ["pending", "confirmed", "processing", "shipped", "out_for_delivery", "delivered"];

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const q = useQuery({
    queryKey: ["order", id],
    queryFn: () => apiFetch<Order>(`/orders/${id}`, { auth: true }),
    enabled: !!user,
  });

  if (!user) return <div className="py-12"><Empty title="Log in to view this order" /></div>;
  if (q.isLoading) return <div className="py-6"><Skeleton className="h-40" /></div>;
  if (q.isError) return <div className="py-6"><ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /></div>;
  const o = q.data!;
  const stageIdx = STAGES.indexOf(o.status);

  return (
    <div className="py-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold">{o.order_number}</h1>
        <Badge tone={o.status === "cancelled" ? "red" : o.status === "delivered" ? "green" : "amber"}>{o.status}</Badge>
      </div>
      <p className="text-sm text-zinc-500">Payment: {o.payment_status} · Tracking: {o.tracking_number || "—"}</p>

      {/* lifecycle tracker */}
      <div className="mt-4 flex items-center gap-1 overflow-x-auto">
        {STAGES.map((s, i) => (
          <div key={s} className="flex items-center gap-1">
            <div className={`whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] font-medium ${i <= stageIdx ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-500"}`}>
              {s.replace(/_/g, " ")}
            </div>
            {i < STAGES.length - 1 && <span className="text-zinc-300">→</span>}
          </div>
        ))}
      </div>

      <Card className="mt-4 p-4">
        {o.items.map((i) => (
          <div key={i.id} className="flex justify-between border-b border-zinc-100 dark:border-zinc-800 py-2 text-sm last:border-0">
            <span>{i.product_name} × {i.quantity}</span>
            <span className="font-medium">{inr(i.total_price)}</span>
          </div>
        ))}
        <p className="mt-2 text-right font-bold">Total: {inr(o.total)}</p>
      </Card>
    </div>
  );
}
