"use client";
import Link from "next/link";
import { Heart, Moon, Search, ShoppingCart, Sparkles, Sun, User } from "lucide-react";
import { useTheme } from "next-themes";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/stores/auth";
import { useUI } from "@/stores/ui";
import { useGuestCart } from "@/stores/guest-cart";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export function Header() {
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuth();
  const setChatOpen = useUI((s) => s.setChatOpen);
  const cartBump = useUI((s) => s.cartBump);
  const router = useRouter();
  const [q, setQ] = useState("");

  const { data: cart } = useQuery({
    queryKey: ["cart", cartBump, user?.id],
    queryFn: () => apiFetch<{ items: { quantity: number }[] }>("/cart", { auth: true }),
    enabled: !!user,
    retry: false,
  });
  const guestCount = useGuestCart((s) => s.items.reduce((a, i) => a + i.quantity, 0));
  const count = user
    ? cart?.items.reduce((a, i) => a + i.quantity, 0) ?? 0
    : guestCount;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    router.push(`/search?q=${encodeURIComponent(q)}`);
  };

  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3">
        <Link href="/" className="text-lg font-bold tracking-tight">
          Nova<span className="text-zinc-400">.</span>
        </Link>
        <nav className="hidden md:flex items-center gap-4 text-sm text-zinc-600 dark:text-zinc-400">
          <Link href="/products" className="hover:text-zinc-900 dark:hover:text-white">Shop</Link>
          <Link href="/search?q=laptop" className="hover:text-zinc-900 dark:hover:text-white">Laptops</Link>
          <Link href="/search?q=headphone" className="hover:text-zinc-900 dark:hover:text-white">Audio</Link>
          <Link href="/search?q=shoe" className="hover:text-zinc-900 dark:hover:text-white">Footwear</Link>
        </nav>
        <form onSubmit={submit} className="relative ml-auto hidden sm:block w-full max-w-xs">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search products…"
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-zinc-400"
          />
        </form>
        <div className="ml-auto sm:ml-0 flex items-center gap-1">
          <button
            onClick={() => setChatOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-zinc-900 dark:bg-white px-3 py-2 text-sm font-medium text-white dark:text-zinc-900"
            title="AI shopping assistant"
          >
            <Sparkles className="h-4 w-4" />
            <span className="hidden lg:inline">AI Assistant</span>
          </button>
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="rounded-lg p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <Link href="/wishlist" className="rounded-lg p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800" aria-label="Wishlist">
            <Heart className="h-4 w-4" />
          </Link>
          <Link href="/cart" className="relative rounded-lg p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800" aria-label="Cart">
            <ShoppingCart className="h-4 w-4" />
            {count > 0 && (
              <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-zinc-900 dark:bg-white px-1 text-[10px] font-bold text-white dark:text-zinc-900">
                {count}
              </span>
            )}
          </Link>
          {user ? (
            <div className="flex items-center gap-1">
              <Link href="/profile" className="rounded-lg p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800" title={user.email}>
                <User className="h-4 w-4" />
              </Link>
              {(user.role === "admin" || user.role === "manager") && (
                <Link href="/admin" className="hidden sm:inline rounded-lg px-2 py-2 text-xs font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800">
                  Admin
                </Link>
              )}
              <button onClick={logout} className="hidden sm:inline text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-white px-1">
                Logout
              </button>
            </div>
          ) : (
            <Link href="/login" className="rounded-lg px-3 py-2 text-sm font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800">
              Login
            </Link>
          )}
        </div>
      </div>
      <form onSubmit={submit} className="sm:hidden px-4 pb-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search products…"
          className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 px-3 py-2 text-sm outline-none"
        />
      </form>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mt-16 border-t border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 text-sm sm:grid-cols-4">
        <div>
          <p className="font-bold">Nova.</p>
          <p className="mt-2 text-zinc-500">A production-grade AI-powered commerce platform.</p>
        </div>
        <div>
          <p className="font-medium">Shop</p>
          <ul className="mt-2 space-y-1 text-zinc-500">
            <li><Link href="/products">All products</Link></li>
            <li><Link href="/search?q=laptop">Laptops</Link></li>
            <li><Link href="/search?q=phone">Mobiles</Link></li>
          </ul>
        </div>
        <div>
          <p className="font-medium">Account</p>
          <ul className="mt-2 space-y-1 text-zinc-500">
            <li><Link href="/orders">Orders</Link></li>
            <li><Link href="/wishlist">Wishlist</Link></li>
            <li><Link href="/profile">Profile</Link></li>
          </ul>
        </div>
        <div>
          <p className="font-medium">Demo accounts</p>
          <ul className="mt-2 space-y-1 text-zinc-500">
            <li>customer@example.com</li>
            <li>admin@example.com</li>
            <li className="text-xs">password: password123</li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
