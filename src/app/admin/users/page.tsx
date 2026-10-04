"use client";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { AdminShell } from "@/components/admin";
import { Badge, ErrorState, Skeleton } from "@/components/ui";

export default function AdminUsers() {
  const q = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => apiFetch<{ id: string; email: string; full_name: string; role: string; is_active: boolean }[]>("/users", { auth: true }),
  });
  return (
    <AdminShell>
      <h1 className="text-xl font-bold">Users</h1>
      <div className="mt-3">
        {q.isLoading ? <Skeleton className="h-60" /> :
          q.isError ? <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /> : (
          <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 dark:bg-zinc-900 text-left text-xs text-zinc-500">
                <tr><th className="p-2">Email</th><th className="p-2">Name</th><th className="p-2">Role</th><th className="p-2">Active</th></tr>
              </thead>
              <tbody>
                {q.data!.slice(0, 100).map((u) => (
                  <tr key={u.id} className="border-t border-zinc-100 dark:border-zinc-800">
                    <td className="p-2">{u.email}</td>
                    <td className="p-2">{u.full_name}</td>
                    <td className="p-2"><Badge>{u.role}</Badge></td>
                    <td className="p-2">{u.is_active ? "Yes" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="p-2 text-xs text-zinc-500">Showing 100 of {q.data!.length}</p>
          </div>
        )}
      </div>
    </AdminShell>
  );
}
