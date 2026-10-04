import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Header, Footer } from "@/components/chrome";
import { ChatWidget, ChatFab } from "@/components/chat";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Nova — AI-Powered Commerce",
  description: "Production-grade e-commerce with an AI shopping assistant.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="min-h-screen bg-white text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100 antialiased">
        <Providers>
          <Header />
          <main className="mx-auto w-full max-w-7xl px-4">{children}</main>
          <Footer />
          <ChatWidget />
          <ChatFab />
        </Providers>
      </body>
    </html>
  );
}
