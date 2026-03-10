"use client";

import { useEffect, useState, useCallback } from "react";
import PageHeader from "@/components/PageHeader";
import DataTable from "@/components/DataTable";
import Modal from "@/components/Modal";
import Badge from "@/components/Badge";
import { ClipboardCheck } from "lucide-react";

interface StockItem {
  id: string;
  name: string;
  category: string;
  unit: string;
  minStock: number;
  currentStock: number;
  lastCountDate: string | null;
  totalPurchased: number;
}

export default function EstoquePage() {
  const [stockData, setStockData] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<StockItem | null>(null);
  const [form, setForm] = useState({
    quantity: "",
    location: "",
    notes: "",
    date: new Date().toISOString().split("T")[0],
  });

  const loadData = useCallback(() => {
    fetch("/api/stock")
      .then((r) => r.json())
      .then((d) => {
        setStockData(d);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCountClick = (item: StockItem) => {
    setSelectedItem(item);
    setForm({
      quantity: item.currentStock.toString(),
      location: "",
      notes: "",
      date: new Date().toISOString().split("T")[0],
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;

    await fetch("/api/stock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        itemId: selectedItem.id,
        quantity: parseInt(form.quantity),
        location: form.location,
        notes: form.notes,
        date: form.date,
      }),
    });
    setModalOpen(false);
    loadData();
  };

  const columns = [
    {
      key: "name",
      label: "Item",
      render: (item: StockItem) => (
        <div>
          <div className="font-medium">{item.name}</div>
          <div className="text-xs text-muted">{item.category}</div>
        </div>
      ),
    },
    {
      key: "currentStock",
      label: "Estoque Atual",
      render: (item: StockItem) => (
        <span className="text-lg font-bold">{item.currentStock}</span>
      ),
    },
    {
      key: "minStock",
      label: "Mínimo",
      render: (item: StockItem) => item.minStock,
    },
    {
      key: "status",
      label: "Status",
      render: (item: StockItem) => {
        if (item.currentStock === 0 && item.totalPurchased === 0)
          return <Badge variant="default">Sem registro</Badge>;
        if (item.currentStock <= 0) return <Badge variant="danger">Esgotado</Badge>;
        if (item.currentStock < item.minStock)
          return <Badge variant="warning">Baixo</Badge>;
        return <Badge variant="success">Normal</Badge>;
      },
    },
    {
      key: "totalPurchased",
      label: "Total Comprado",
      render: (item: StockItem) => item.totalPurchased,
    },
    {
      key: "lastCountDate",
      label: "Última Contagem",
      render: (item: StockItem) =>
        item.lastCountDate
          ? new Date(item.lastCountDate).toLocaleDateString("pt-BR")
          : "Nunca",
    },
    {
      key: "actions",
      label: "Ação",
      render: (item: StockItem) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleCountClick(item);
          }}
          className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
        >
          <ClipboardCheck className="w-3.5 h-3.5" />
          Contar
        </button>
      ),
    },
  ];

  const inputClass =
    "w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent";

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-muted">Carregando estoque...</div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Controle de Estoque"
        description="Monitore e atualize a contagem de estoque do enxoval"
      />

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-card-border p-4">
          <p className="text-xs text-muted font-medium">Total em Estoque</p>
          <p className="text-2xl font-bold text-emerald-600">
            {stockData.reduce((s, i) => s + i.currentStock, 0)}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-card-border p-4">
          <p className="text-xs text-muted font-medium">Itens Esgotados</p>
          <p className="text-2xl font-bold text-red-600">
            {stockData.filter((i) => i.currentStock <= 0 && i.totalPurchased > 0).length}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-card-border p-4">
          <p className="text-xs text-muted font-medium">Estoque Baixo</p>
          <p className="text-2xl font-bold text-amber-600">
            {stockData.filter((i) => i.currentStock > 0 && i.currentStock < i.minStock).length}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-card-border p-4">
          <p className="text-xs text-muted font-medium">Itens Cadastrados</p>
          <p className="text-2xl font-bold">{stockData.length}</p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={stockData}
        emptyMessage="Nenhum item cadastrado. Cadastre itens na página de Compras."
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={`Contagem: ${selectedItem?.name}`}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              Quantidade Contada *
            </label>
            <input
              type="number"
              required
              min="0"
              className={inputClass}
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Data da Contagem *</label>
            <input
              type="date"
              required
              className={inputClass}
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Localização
            </label>
            <input
              type="text"
              className={inputClass}
              placeholder="Ex: Almoxarifado Principal"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Observações
            </label>
            <textarea
              className={inputClass}
              rows={2}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary-dark"
            >
              Salvar Contagem
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
