"use client";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Product } from "@/types";
import { ProductCard } from "@/components/product";
import { Button, Empty, ErrorState, Skeleton } from "@/components/ui";
import { useAuth } from "@/stores/auth";

export default function WishlistPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const wl = useQuery({
    queryKey: ["wishlist"],
    queryFn: () => apiFetch<{ id: string; items: Product[] }>("/wishlist", { auth: true }),
    enabled: !!user,
  });
  const remove = useMutation({
    mutationFn: (pid: string) => apiFetch(`/wishlist/${pid}`, { method: "DELETE", auth: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["wishlist"] }),
  });

  if (!user) return <div className="py-12"><Empty title="Save what you love" hint="Log in to sync your wishlist." action={<Link href="/login"><Button>Login</Button></Link>} /></div>;
  if (wl.isLoading) return <div className="py-6"><Skeleton className="h-40" /></div>;
  if (wl.isError) return <div className="py-6"><ErrorState message={(wl.error as Error).message} onRetry={() => wl.refetch()} /></div>;
  if (wl.data!.items.length === 0) return <div className="py-12"><Empty title="Wishlist is empty" hint="Tap the heart on any product." action={<Link href="/products"><Button>Discover products</Button></Link>} /></div>;

  return (
    <div className="py-6">
      <h1 className="text-xl font-bold">Wishlist ({wl.data!.items.length})</h1>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {wl.data!.items.map((p) => (
          <div key={p.id} className="relative">
            <ProductCard p={p} />
            <button onClick={() => remove.mutate(p.id)}
              className="absolute right-2 top-2 rounded-full bg-white/90 dark:bg-zinc-900/90 px-2 py-1 text-xs shadow">
              ✕ Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
