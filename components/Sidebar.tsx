"use client";

import { Package, ShoppingCart, ArrowRightLeft, BarChart3 } from "lucide-react";

export function Sidebar() {
  return (
    <aside className="w-64 bg-codexia-secondary/80 backdrop-blur border-r border-codexia-primary/30 min-h-screen p-4">
      <div className="mb-8">
        <h1 className="text-xl font-bold text-codexia-accent font-mono">CODEXIAAUDITOR</h1>
        <p className="text-xs text-codexia-light/70 mt-1">Auditoria de Enxoval</p>
      </div>
      <nav className="space-y-1">
        <a
          href="#dashboard"
          className="flex items-center gap-3 px-3 py-2 rounded-lg bg-codexia-primary/50 text-codexia-accent"
        >
          <BarChart3 className="w-5 h-5" />
          Dashboard
        </a>
        <a
          href="#compras"
          className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-codexia-primary/30 text-codexia-light/90"
        >
          <ShoppingCart className="w-5 h-5" />
          Compras
        </a>
        <a
          href="#movimentacoes"
          className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-codexia-primary/30 text-codexia-light/90"
        >
          <ArrowRightLeft className="w-5 h-5" />
          Movimentações
        </a>
        <a
          href="#tipos"
          className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-codexia-primary/30 text-codexia-light/90"
        >
          <Package className="w-5 h-5" />
          Tipos de Enxoval
        </a>
      </nav>
      <div className="mt-auto pt-8 border-t border-codexia-primary/30">
        <p className="text-xs text-codexia-light/50">
          Sistema de auditoria com IA para identificar desfalques no enxoval do hotel.
        </p>
      </div>
    </aside>
  );
}
