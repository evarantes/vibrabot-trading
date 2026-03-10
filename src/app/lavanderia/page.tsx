"use client";

import { useEffect, useState, useCallback } from "react";
import PageHeader from "@/components/PageHeader";
import DataTable from "@/components/DataTable";
import Modal from "@/components/Modal";
import Badge from "@/components/Badge";
import { Plus, WashingMachine, ArrowUpRight, ArrowDownLeft } from "lucide-react";

interface Category {
  id: string;
  name: string;
  items: { id: string; name: string }[];
}

interface LaundryRecord {
  id: string;
  date: string;
  sentQuantity: number;
  returnedQuantity: number;
  damagedQuantity: number;
  notes: string | null;
  item: {
    id: string;
    name: string;
    category: { name: string };
  };
}

export default function LavanderiaPage() {
  const [records, setRecords] = useState<LaundryRecord[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [dateFilter, setDateFilter] = useState(
    new Date().toISOString().split("T")[0]
  );

  const [form, setForm] = useState({
    itemId: "",
    date: new Date().toISOString().split("T")[0],
    sentQuantity: "",
    returnedQuantity: "",
    damagedQuantity: "0",
    notes: "",
  });

  const loadData = useCallback(() => {
    Promise.all([
      fetch(`/api/laundry?date=${dateFilter}`).then((r) => r.json()),
      fetch("/api/categories").then((r) => r.json()),
    ]).then(([l, c]) => {
      setRecords(l);
      setCategories(c);
      setLoading(false);
    });
  }, [dateFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetch("/api/laundry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        sentQuantity: parseInt(form.sentQuantity) || 0,
        returnedQuantity: parseInt(form.returnedQuantity) || 0,
        damagedQuantity: parseInt(form.damagedQuantity) || 0,
      }),
    });
    setModalOpen(false);
    setForm({
      itemId: "",
      date: dateFilter,
      sentQuantity: "",
      returnedQuantity: "",
      damagedQuantity: "0",
      notes: "",
    });
    loadData();
  };

  const totalSent = records.reduce((s, r) => s + r.sentQuantity, 0);
  const totalReturned = records.reduce((s, r) => s + r.returnedQuantity, 0);
  const totalDamaged = records.reduce((s, r) => s + r.damagedQuantity, 0);

  const columns = [
    {
      key: "item",
      label: "Item",
      render: (r: LaundryRecord) => (
        <div>
          <div className="font-medium">{r.item.name}</div>
          <div className="text-xs text-muted">{r.item.category.name}</div>
        </div>
      ),
    },
    {
      key: "sentQuantity",
      label: "Enviado",
      render: (r: LaundryRecord) => (
        <div className="flex items-center gap-1">
          <ArrowUpRight className="w-4 h-4 text-blue-500" />
          <span className="font-semibold">{r.sentQuantity}</span>
        </div>
      ),
    },
    {
      key: "returnedQuantity",
      label: "Retornado",
      render: (r: LaundryRecord) => (
        <div className="flex items-center gap-1">
          <ArrowDownLeft className="w-4 h-4 text-emerald-500" />
          <span className="font-semibold">{r.returnedQuantity}</span>
        </div>
      ),
    },
    {
      key: "damagedQuantity",
      label: "Danificado",
      render: (r: LaundryRecord) =>
        r.damagedQuantity > 0 ? (
          <Badge variant="danger">{r.damagedQuantity}</Badge>
        ) : (
          <span className="text-muted">0</span>
        ),
    },
    {
      key: "balance",
      label: "Saldo",
      render: (r: LaundryRecord) => {
        const balance = r.returnedQuantity - r.sentQuantity;
        return (
          <Badge variant={balance >= 0 ? "success" : "warning"}>
            {balance >= 0 ? "+" : ""}
            {balance}
          </Badge>
        );
      },
    },
    {
      key: "notes",
      label: "Obs",
      render: (r: LaundryRecord) => (
        <span className="text-xs text-muted">{r.notes || "-"}</span>
      ),
    },
  ];

  const inputClass =
    "w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent";

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-muted">Carregando lavanderia...</div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Controle de Lavanderia"
        description="Acompanhe o envio e retorno diário de enxoval da lavanderia"
        action={
          <button
            onClick={() => {
              setForm({ ...form, date: dateFilter });
              setModalOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors"
          >
            <Plus className="w-4 h-4" />
            Registrar
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

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-card-border p-4">
          <div className="flex items-center gap-2 mb-1">
            <WashingMachine className="w-4 h-4 text-blue-500" />
            <span className="text-xs text-muted font-medium">Registros do Dia</span>
          </div>
          <p className="text-2xl font-bold">{records.length}</p>
        </div>
        <div className="bg-blue-50 rounded-xl border border-blue-100 p-4">
          <div className="flex items-center gap-2 mb-1">
            <ArrowUpRight className="w-4 h-4 text-blue-600" />
            <span className="text-xs text-blue-600 font-medium">Total Enviado</span>
          </div>
          <p className="text-2xl font-bold text-blue-600">{totalSent}</p>
        </div>
        <div className="bg-emerald-50 rounded-xl border border-emerald-100 p-4">
          <div className="flex items-center gap-2 mb-1">
            <ArrowDownLeft className="w-4 h-4 text-emerald-600" />
            <span className="text-xs text-emerald-600 font-medium">Total Retornado</span>
          </div>
          <p className="text-2xl font-bold text-emerald-600">{totalReturned}</p>
        </div>
        <div className="bg-red-50 rounded-xl border border-red-100 p-4">
          <span className="text-xs text-red-600 font-medium">Danificados</span>
          <p className="text-2xl font-bold text-red-600">{totalDamaged}</p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={records}
        emptyMessage="Nenhum registro de lavanderia para esta data"
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Registrar Lavanderia"
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
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Enviado</label>
              <input
                type="number"
                min="0"
                className={inputClass}
                value={form.sentQuantity}
                onChange={(e) =>
                  setForm({ ...form, sentQuantity: e.target.value })
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Retornado</label>
              <input
                type="number"
                min="0"
                className={inputClass}
                value={form.returnedQuantity}
                onChange={(e) =>
                  setForm({ ...form, returnedQuantity: e.target.value })
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Danificado</label>
              <input
                type="number"
                min="0"
                className={inputClass}
                value={form.damagedQuantity}
                onChange={(e) =>
                  setForm({ ...form, damagedQuantity: e.target.value })
                }
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
              Salvar
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
