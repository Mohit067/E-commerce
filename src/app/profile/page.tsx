"use client";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button, Card, Empty, Input } from "@/components/ui";
import { useAuth } from "@/stores/auth";
import Link from "next/link";
import { useState } from "react";

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const [form, setForm] = useState({ full_name: "", phone: "" });
  const [saved, setSaved] = useState(false);
  const orders = useQuery({
    queryKey: ["orders-count"],
    queryFn: () => apiFetch<{ total: number }>("/orders?page=1&page_size=1", { auth: true }),
    enabled: !!user,
  });

  if (!user) return <div className="py-12"><Empty title="Your profile" hint="Log in to manage your account." action={<Link href="/login"><Button>Login</Button></Link>} /></div>;

  return (
    <div className="mx-auto max-w-lg py-6">
      <Card className="p-5">
        <h1 className="text-xl font-bold">{user.full_name || "My profile"}</h1>
        <p className="text-sm text-zinc-500">{user.email} · {user.role} · {orders.data ? `${orders.data.total} orders` : ""}</p>
        <div className="mt-4 space-y-2">
          <Input placeholder="Full name" defaultValue={user.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          <Input placeholder="Phone" onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <Button variant="outline" onClick={async () => {
            await apiFetch("/auth/me", { method: "PATCH", auth: true, body: JSON.stringify(form) });
            setSaved(true);
          }}>Save profile</Button>
          {saved && <p className="text-xs text-green-600">Saved ✓</p>}
        </div>
        <div className="mt-4 flex gap-2 text-sm">
          <Link href="/orders" className="underline">Orders</Link>
          <Link href="/wishlist" className="underline">Wishlist</Link>
          <button onClick={logout} className="text-red-500 underline">Logout</button>
        </div>
      </Card>
    </div>
  );
}
