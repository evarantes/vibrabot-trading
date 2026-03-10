"use client";

import { useEffect, useState, useCallback } from "react";
import PageHeader from "@/components/PageHeader";
import DataTable from "@/components/DataTable";
import Modal from "@/components/Modal";
import { Plus, ShoppingCart } from "lucide-react";
import { formatCurrency, formatDate } from "@/lib/utils";

interface Category {
  id: string;
  name: string;
  items: Item[];
}

interface Item {
  id: string;
  name: string;
  categoryId: string;
  category: { name: string };
}

interface Purchase {
  id: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  supplier: string | null;
  invoiceNumber: string | null;
  purchaseDate: string;
  notes: string | null;
  item: Item;
}

export default function ComprasPage() {
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [categoryModalOpen, setCategoryModalOpen] = useState(false);
  const [itemModalOpen, setItemModalOpen] = useState(false);

  const [form, setForm] = useState({
    itemId: "",
    quantity: "",
    unitPrice: "",
    supplier: "",
    invoiceNumber: "",
    purchaseDate: new Date().toISOString().split("T")[0],
    notes: "",
  });

  const [categoryForm, setCategoryForm] = useState({ name: "", description: "" });
  const [itemForm, setItemForm] = useState({
    categoryId: "",
    name: "",
    description: "",
    unit: "unidade",
    minStock: "0",
  });

  const loadData = useCallback(() => {
    Promise.all([
      fetch("/api/purchases").then((r) => r.json()),
      fetch("/api/items").then((r) => r.json()),
      fetch("/api/categories").then((r) => r.json()),
    ]).then(([p, i, c]) => {
      setPurchases(p);
      setItems(i);
      setCategories(c);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetch("/api/purchases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        quantity: parseInt(form.quantity),
        unitPrice: parseFloat(form.unitPrice),
      }),
    });
    setModalOpen(false);
    setForm({
      itemId: "",
      quantity: "",
      unitPrice: "",
      supplier: "",
      invoiceNumber: "",
      purchaseDate: new Date().toISOString().split("T")[0],
      notes: "",
    });
    loadData();
  };

  const handleCategorySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetch("/api/categories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(categoryForm),
    });
    setCategoryModalOpen(false);
    setCategoryForm({ name: "", description: "" });
    loadData();
  };

  const handleItemSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetch("/api/items", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...itemForm,
        minStock: parseInt(itemForm.minStock),
      }),
    });
    setItemModalOpen(false);
    setItemForm({
      categoryId: "",
      name: "",
      description: "",
      unit: "unidade",
      minStock: "0",
    });
    loadData();
  };

  const columns = [
    {
      key: "item",
      label: "Item",
      render: (p: Purchase) => (
        <div>
          <div className="font-medium">{p.item.name}</div>
          <div className="text-xs text-muted">{p.item.category.name}</div>
        </div>
      ),
    },
    { key: "quantity", label: "Qtd", render: (p: Purchase) => p.quantity },
    {
      key: "unitPrice",
      label: "Preço Unit.",
      render: (p: Purchase) => formatCurrency(p.unitPrice),
    },
    {
      key: "totalPrice",
      label: "Total",
      render: (p: Purchase) => (
        <span className="font-semibold text-emerald-600">
          {formatCurrency(p.totalPrice)}
        </span>
      ),
    },
    {
      key: "supplier",
      label: "Fornecedor",
      render: (p: Purchase) => p.supplier || "-",
    },
    {
      key: "invoiceNumber",
      label: "NF",
      render: (p: Purchase) => p.invoiceNumber || "-",
    },
    {
      key: "purchaseDate",
      label: "Data",
      render: (p: Purchase) => formatDate(p.purchaseDate),
    },
  ];

  const inputClass =
    "w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent";

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-muted">Carregando compras...</div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Compras de Enxoval"
        description="Registre e acompanhe todas as compras de enxoval"
        action={
          <div className="flex gap-2">
            <button
              onClick={() => setCategoryModalOpen(true)}
              className="px-4 py-2 bg-slate-600 text-white rounded-lg text-sm font-medium hover:bg-slate-700 transition-colors"
            >
              + Categoria
            </button>
            <button
              onClick={() => setItemModalOpen(true)}
              className="px-4 py-2 bg-cyan-600 text-white rounded-lg text-sm font-medium hover:bg-cyan-700 transition-colors"
            >
              + Item
            </button>
            <button
              onClick={() => setModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors"
            >
              <Plus className="w-4 h-4" />
              Nova Compra
            </button>
          </div>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-card-border p-4">
          <div className="flex items-center gap-2 mb-1">
            <ShoppingCart className="w-4 h-4 text-blue-500" />
            <span className="text-xs text-muted font-medium">Total de Compras</span>
          </div>
          <p className="text-2xl font-bold">{purchases.length}</p>
        </div>
        <div className="bg-white rounded-xl border border-card-border p-4">
          <div className="flex items-center gap-2 mb-1">
            <ShoppingCart className="w-4 h-4 text-emerald-500" />
            <span className="text-xs text-muted font-medium">Total Investido</span>
          </div>
          <p className="text-2xl font-bold text-emerald-600">
            {formatCurrency(purchases.reduce((s, p) => s + p.totalPrice, 0))}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-card-border p-4">
          <div className="flex items-center gap-2 mb-1">
            <ShoppingCart className="w-4 h-4 text-purple-500" />
            <span className="text-xs text-muted font-medium">Peças Compradas</span>
          </div>
          <p className="text-2xl font-bold">
            {purchases.reduce((s, p) => s + p.quantity, 0)}
          </p>
        </div>
      </div>

      <DataTable columns={columns} data={purchases} emptyMessage="Nenhuma compra registrada" />

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Registrar Compra" size="lg">
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
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Quantidade *</label>
              <input
                type="number"
                required
                min="1"
                className={inputClass}
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Preço Unitário</label>
              <input
                type="number"
                step="0.01"
                min="0"
                className={inputClass}
                value={form.unitPrice}
                onChange={(e) => setForm({ ...form, unitPrice: e.target.value })}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Fornecedor</label>
              <input
                type="text"
                className={inputClass}
                value={form.supplier}
                onChange={(e) => setForm({ ...form, supplier: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Nota Fiscal</label>
              <input
                type="text"
                className={inputClass}
                value={form.invoiceNumber}
                onChange={(e) => setForm({ ...form, invoiceNumber: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Data da Compra *</label>
            <input
              type="date"
              required
              className={inputClass}
              value={form.purchaseDate}
              onChange={(e) => setForm({ ...form, purchaseDate: e.target.value })}
            />
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
              Registrar Compra
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={categoryModalOpen}
        onClose={() => setCategoryModalOpen(false)}
        title="Nova Categoria"
      >
        <form onSubmit={handleCategorySubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Nome *</label>
            <input
              type="text"
              required
              className={inputClass}
              placeholder="Ex: Toalhas, Lençóis, Fronhas..."
              value={categoryForm.name}
              onChange={(e) => setCategoryForm({ ...categoryForm, name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Descrição</label>
            <textarea
              className={inputClass}
              rows={2}
              value={categoryForm.description}
              onChange={(e) => setCategoryForm({ ...categoryForm, description: e.target.value })}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setCategoryModalOpen(false)}
              className="px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm bg-slate-600 text-white rounded-lg hover:bg-slate-700"
            >
              Criar Categoria
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={itemModalOpen}
        onClose={() => setItemModalOpen(false)}
        title="Novo Item"
      >
        <form onSubmit={handleItemSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Categoria *</label>
            <select
              required
              className={inputClass}
              value={itemForm.categoryId}
              onChange={(e) => setItemForm({ ...itemForm, categoryId: e.target.value })}
            >
              <option value="">Selecione uma categoria</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Nome *</label>
            <input
              type="text"
              required
              className={inputClass}
              placeholder="Ex: Toalha de Banho Branca"
              value={itemForm.name}
              onChange={(e) => setItemForm({ ...itemForm, name: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Unidade</label>
              <input
                type="text"
                className={inputClass}
                value={itemForm.unit}
                onChange={(e) => setItemForm({ ...itemForm, unit: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Estoque Mínimo</label>
              <input
                type="number"
                min="0"
                className={inputClass}
                value={itemForm.minStock}
                onChange={(e) => setItemForm({ ...itemForm, minStock: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Descrição</label>
            <textarea
              className={inputClass}
              rows={2}
              value={itemForm.description}
              onChange={(e) => setItemForm({ ...itemForm, description: e.target.value })}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setItemModalOpen(false)}
              className="px-4 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm bg-cyan-600 text-white rounded-lg hover:bg-cyan-700"
            >
              Criar Item
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
