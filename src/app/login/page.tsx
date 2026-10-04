"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/stores/auth";
import { Button, Card, Input } from "@/components/ui";

export default function LoginPage() {
  const [email, setEmail] = useState("customer@example.com");
  const [password, setPassword] = useState("password123");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const login = useAuth((s) => s.login);
  const router = useRouter();

  const submit = async () => {
    setErr("");
    setBusy(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-sm py-12">
      <Card className="p-6">
        <h1 className="text-xl font-bold">Welcome back</h1>
        <p className="text-sm text-zinc-500">Log in to shop, track orders and chat with AI.</p>
        <div className="mt-4 space-y-2">
          <Input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()} />
          {err && <p className="text-xs text-red-500">{err}</p>}
          <Button onClick={submit} disabled={busy} className="w-full">{busy ? "Logging in…" : "Login"}</Button>
        </div>
        <p className="mt-3 text-xs text-zinc-500">
          Demo: customer@example.com / admin@example.com · password123
        </p>
        <p className="mt-2 text-sm">No account? <Link href="/register" className="underline">Register</Link></p>
      </Card>
    </div>
  );
}
