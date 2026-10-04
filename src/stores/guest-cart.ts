"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { apiFetch } from "@/lib/api";

export interface GuestItem {
  product_id: string;
  slug: string;
  name: string;
  price: number;
  image_url: string;
  variant_id?: string | null;
  variant_name?: string;
  quantity: number;
}

interface GuestCartState {
  items: GuestItem[];
  add: (item: Omit<GuestItem, "quantity">, qty?: number) => void;
  setQty: (product_id: string, variant_id: string | null | undefined, qty: number) => void;
  remove: (product_id: string, variant_id: string | null | undefined) => void;
  clear: () => void;
}

export const useGuestCart = create<GuestCartState>()(
  persist(
    (set) => ({
      items: [],
      add: (item, qty = 1) =>
        set((s) => {
          const i = s.items.findIndex(
            (x) => x.product_id === item.product_id && (x.variant_id ?? null) === (item.variant_id ?? null),
          );
          if (i >= 0) {
            const items = [...s.items];
            items[i] = { ...items[i], quantity: Math.min(99, items[i].quantity + qty) };
            return { items };
          }
          return { items: [...s.items, { ...item, quantity: qty }] };
        }),
      setQty: (product_id, variant_id, qty) =>
        set((s) => ({
          items:
            qty <= 0
              ? s.items.filter(
                  (x) => !(x.product_id === product_id && (x.variant_id ?? null) === (variant_id ?? null)),
                )
              : s.items.map((x) =>
                  x.product_id === product_id && (x.variant_id ?? null) === (variant_id ?? null)
                    ? { ...x, quantity: Math.min(99, qty) }
                    : x,
                ),
        })),
      remove: (product_id, variant_id) =>
        set((s) => ({
          items: s.items.filter(
            (x) => !(x.product_id === product_id && (x.variant_id ?? null) === (variant_id ?? null)),
          ),
        })),
      clear: () => set({ items: [] }),
    }),
    { name: "nc_guest_cart" },
  ),
);

export function guestTotals(items: GuestItem[]) {
  const subtotal = Math.round(items.reduce((a, i) => a + i.price * i.quantity, 0) * 100) / 100;
  const shipping = subtotal === 0 || subtotal >= 999 ? 0 : 49;
  const tax = Math.round(subtotal * 0.18 * 100) / 100;
  return { subtotal, discount: 0, shipping, tax, total: Math.round((subtotal + shipping + tax) * 100) / 100 };
}

/** Push guest items into the backend cart after login/signup. Call while tokens exist. */
export async function mergeGuestCart(): Promise<void> {
  const { items, clear } = useGuestCart.getState();
  if (items.length === 0) return;
  for (const it of items) {
    try {
      await apiFetch("/cart/items", {
        method: "POST",
        auth: true,
        body: JSON.stringify({
          product_id: it.product_id,
          variant_id: it.variant_id ?? null,
          quantity: it.quantity,
        }),
      });
    } catch {
      // product may be gone; skip and continue merging the rest
    }
  }
  clear();
}
