"use client";
import { useState } from "react";
import { cn } from "@/lib/utils";

/** Product image with automatic placeholder fallback if the source fails. */
export function SmartImage({
  src,
  seed,
  alt,
  className,
}: {
  src?: string;
  seed: string;
  alt: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const fallback = `https://picsum.photos/seed/${encodeURIComponent(seed)}/800/800`;
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={!src || failed ? fallback : src}
      onError={() => setFailed(true)}
      alt={alt}
      loading="lazy"
      className={cn("bg-zinc-100 dark:bg-zinc-800", className)}
    />
  );
}
