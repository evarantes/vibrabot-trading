"use client";

import { useEffect, useState, useCallback } from "react";
import PageHeader from "@/components/PageHeader";
import DataTable from "@/components/DataTable";
import Modal from "@/components/Modal";
import { Plus, BedDouble, Trash2 } from "lucide-react";

interface Category {
  id: string;
  name: string;
  items: { id: string; name: string }[];
}

interface RoomUsage {
  id: string;
  date: string;
  roomNumber: string;
  quantity: number;
  notes: string | null;
  item: {
    id: string;
    name: string;
    category: { name: string };
  };
}

export default function EmUsoPage() {
  const [usages, setUsages] = useState<RoomUsage[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [dateFilter, setDateFilter] = useState(
    new Date().toISOString().split("T")[0]
  );

  const [form, setForm] = useState({
    itemId: "",
    date: new Date().toISOString().split("T")[0],
    roomNumber: "",
    quantity: "1",
    notes: "",
  });

  const loadData = useCallback(() => {
    Promise.all([
      fetch(`/api/room-usage?date=${dateFilter}`).then((r) => r.json()),
      fetch("/api/categories").then((r) => r.json()),
    ]).then(([u, c]) => {
      setUsages(u);
      setCategories(c);
      setLoading(false);
    });
  }, [dateFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetch("/api/room-usage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        quantity: parseInt(form.quantity),
      }),
    });
    setModalOpen(false);
    setForm({
      itemId: "",
      date: dateFilter,
      roomNumber: "",
      quantity: "1",
      notes: "",
    });
    loadData();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Remover este registro?")) return;
    await fetch(`/api/room-usage?id=${id}`, { method: "DELETE" });
    loadData();
  };

  const totalItems = usages.reduce((s, u) => s + u.quantity, 0);
  const uniqueRooms = new Set(usages.map((u) => u.roomNumber)).size;

  const columns = [
    {
      key: "roomNumber",
      label: "Quarto",
      render: (u: RoomUsage) => (
        <div className="flex items-center gap-2">
          <BedDouble className="w-4 h-4 text-purple-500" />
          <span className="font-semibold">{u.roomNumber}</span>
        </div>
      ),
    },
    {
      key: "item",
      label: "Item",
      render: (u: RoomUsage) => (
        <div>
          <div className="font-medium">{u.item.name}</div>
          <div className="text-xs text-muted">{u.item.category.name}</div>
        </div>
      ),
    },
    {
      key: "quantity",
      label: "Qtd",
      render: (u: RoomUsage) => (
        <span className="font-semibold">{u.quantity}</span>
      ),
    },
    {
      key: "notes",
      label: "Obs",
      render: (u: RoomUsage) => (
        <span className="text-xs text-muted">{u.notes || "-"}</span>
      ),
    },
    {
      key: "actions",
      label: "",
      render: (u: RoomUsage) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleDelete(u.id);
          }}
          className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      ),
    },
  ];

  const inputClass =
    "w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent";

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-muted">Carregando...</div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Enxoval em Uso"
        description="Acompanhe o enxoval distribuído nos quartos"
        action={
          <button
            onClick={() => {
              setForm({ ...form, date: dateFilter });
              setModalOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors"
          >
            <Plus className="w-4 h-4" />
            Registrar Uso
          </button>
        }
      />

      <div className="flex items-center gap-4 mb-6">
        <label className="text-sm font-medium">Data:</label>
        <input
          type="date"
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-light"
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-purple-50 rounded-xl border border-purple-100 p-4">
          <span className="text-xs text-purple-600 font-medium">Peças em Uso</span>
          <p className="text-2xl font-bold text-purple-600">{totalItems}</p>
        </div>
        <div className="bg-blue-50 rounded-xl border border-blue-100 p-4">
          <span className="text-xs text-blue-600 font-medium">Quartos Atendidos</span>
          <p className="text-2xl font-bold text-blue-600">{uniqueRooms}</p>
        </div>
        <div className="bg-white rounded-xl border border-card-border p-4">
          <span className="text-xs text-muted font-medium">Registros</span>
          <p className="text-2xl font-bold">{usages.length}</p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={usages}
        emptyMessage="Nenhum enxoval em uso registrado para esta data"
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Registrar Uso de Enxoval"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Item *</label>
            <select
              required
              className={inputClass}
              value={form.itemId}
              onChange={(e) => setForm({ ...form, itemId: e.target.value })}
            >
              <option value="">Selecione um item</option>
              {categories.map((cat) => (
                <optgroup key={cat.id} label={cat.name}>
                  {cat.items.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Quarto *</label>
              <input
                type="text"
                required
                className={inputClass}
                placeholder="101"
                value={form.roomNumber}
                onChange={(e) =>
                  setForm({ ...form, roomNumber: e.target.value })
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Qtd *</label>
              <input
                type="number"
                required
                min="1"
                className={inputClass}
                value={form.quantity}
                onChange={(e) =>
                  setForm({ ...form, quantity: e.target.value })
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Data *</label>
              <input
                type="date"
                required
                className={inputClass}
                value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Observações</label>
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
              Registrar
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
