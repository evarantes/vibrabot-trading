"use client";

import { useEffect, useState } from "react";
import Dashboard from "@/components/Dashboard";
import { Sidebar } from "@/components/Sidebar";

export default function Home() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-codexia-accent text-xl">Carregando CODEXIAAUDITOR...</div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 lg:p-8">
        <Dashboard />
      </main>
    </div>
  );
}
