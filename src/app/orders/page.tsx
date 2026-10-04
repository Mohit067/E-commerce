"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { inr } from "@/lib/format";
import { Badge, Button, Card, Empty, ErrorState, Skeleton } from "@/components/ui";
import { useAuth } from "@/stores/auth";

import type { Order } from "@/types";

export default function OrdersPage() {
  const { user } = useAuth();
  const q = useQuery({
    queryKey: ["orders"],
    queryFn: () => apiFetch<{ items: Order[] }>("/orders", { auth: true }),
    enabled: !!user,
  });

  if (!user) return <div className="py-12"><Empty title="Track your orders" hint="Log in to see order history." action={<Link href="/login"><Button>Login</Button></Link>} /></div>;
  if (q.isLoading) return <div className="py-6"><Skeleton className="h-24" /></div>;
  if (q.isError) return <div className="py-6"><ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /></div>;
  if (q.data!.items.length === 0) return <div className="py-12"><Empty title="No orders yet" action={<Link href="/products"><Button>Start shopping</Button></Link>} /></div>;

  return (
    <div className="py-6">
      <h1 className="text-xl font-bold">My orders</h1>
      <div className="mt-3 space-y-2">
        {q.data!.items.map((o) => (
          <Link key={o.id} href={`/orders/${o.id}`}>
            <Card className="flex items-center gap-3 p-3 hover:shadow-sm">
              <div className="flex-1">
                <p className="text-sm font-bold">{o.order_number}</p>
                <p className="text-xs text-zinc-500">{new Date(o.created_at).toLocaleDateString()} · {o.items.length} item(s) · {o.tracking_number}</p>
              </div>
              <Badge tone={o.status === "cancelled" ? "red" : o.status === "delivered" ? "green" : "amber"}>{o.status}</Badge>
              <p className="text-sm font-bold">{inr(o.total)}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
