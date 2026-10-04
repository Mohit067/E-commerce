"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useAuth } from "@/stores/auth";
import { Button, Card, Input } from "@/components/ui";

const schema = z.object({
  full_name: z.string().min(2, "Name too short"),
  email: z.string().email("Invalid email"),
  password: z.string().min(6, "Min 6 characters"),
});

export default function RegisterPage() {
  const signup = useAuth((s) => s.signup);
  const router = useRouter();
  const [err, setErr] = useState("");
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
  });

  const onSubmit = handleSubmit(async (v) => {
    setErr("");
    try {
      await signup(v.email, v.password, v.full_name);
      router.push("/");
    } catch (e) {
      setErr((e as Error).message);
    }
  });

  return (
    <div className="mx-auto max-w-sm py-12">
      <Card className="p-6">
        <h1 className="text-xl font-bold">Create account</h1>
        <form onSubmit={onSubmit} className="mt-4 space-y-2">
          <Input placeholder="Full name" {...register("full_name")} />
          {errors.full_name && <p className="text-xs text-red-500">{errors.full_name.message}</p>}
          <Input placeholder="Email" {...register("email")} />
          {errors.email && <p className="text-xs text-red-500">{errors.email.message}</p>}
          <Input placeholder="Password" type="password" {...register("password")} />
          {errors.password && <p className="text-xs text-red-500">{errors.password.message}</p>}
          {err && <p className="text-xs text-red-500">{err}</p>}
          <Button disabled={isSubmitting} className="w-full">{isSubmitting ? "Creating…" : "Register"}</Button>
        </form>
        <p className="mt-2 text-sm">Have an account? <Link href="/login" className="underline">Login</Link></p>
      </Card>
    </div>
  );
}
