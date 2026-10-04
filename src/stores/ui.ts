"use client";
import { create } from "zustand";

interface UIState {
  chatOpen: boolean;
  setChatOpen: (v: boolean) => void;
  cartBump: number;
  bumpCart: () => void;
}

export const useUI = create<UIState>((set) => ({
  chatOpen: false,
  setChatOpen: (v) => set({ chatOpen: v }),
  cartBump: 0,
  bumpCart: () => set((s) => ({ cartBump: s.cartBump + 1 })),
}));
