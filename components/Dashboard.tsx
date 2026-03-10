"use client";

import { useEffect, useState } from "react";
import {
  BarChart3,
  Package,
  Truck,
  Shirt,
  Home,
  AlertTriangle,
  Sparkles,
  Plus,
  RefreshCw,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { clsx } from "clsx";

type EstadoEnxoval = {
  tipoId: string;
  tipoNome: string;
  totalCompras: number;
  emEstoque: number;
  naLavanderia: number;
  emUso: number;
  totalAtual: number;
  desfalque: number;
  parLevel: number;
};

type ResumoAuditoria = {
  data: string;
  totalCompras: number;
  totalEstoque: number;
  totalLavanderia: number;
  totalEmUso: number;
  totalEsperado: number;
  totalAtual: number;
  desfalque: number;
  porTipo: EstadoEnxoval[];
  analiseIA?: string;
};

export default function Dashboard() {
  const [resumo, setResumo] = useState<ResumoAuditoria | null>(null);
  const [loading, setLoading] = useState(true);
  const [analisando, setAnalisando] = useState(false);
  const [showFormCompra, setShowFormCompra] = useState(false);
  const [showFormMov, setShowFormMov] = useState(false);
  const [tipos, setTipos] = useState<{ id: string; nome: string }[]>([]);

  const carregarAuditoria = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/auditoria");
      const data = await res.json();
      setResumo(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const carregarTipos = async () => {
    const res = await fetch("/api/tipos");
    const data = await res.json();
    setTipos(data);
  };

  useEffect(() => {
    carregarAuditoria();
    carregarTipos();
  }, []);

  const executarAnaliseIA = async () => {
    setAnalisando(true);
    try {
      const res = await fetch("/api/auditoria", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ analiseIA: true }),
      });
      const data = await res.json();
      setResumo(data);
    } catch (e) {
      console.error(e);
    } finally {
      setAnalisando(false);
    }
  };

  if (loading || !resumo) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-codexia-accent" />
      </div>
    );
  }

  const chartData = resumo.porTipo.map((t) => ({
    nome: t.tipoNome,
    Compras: t.totalCompras,
    Estoque: t.emEstoque,
    Lavanderia: t.naLavanderia,
    "Em Uso": t.emUso,
    Desfalque: Math.max(0, t.desfalque),
  }));

  return (
    <div className="space-y-8">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-codexia-accent">Dashboard de Auditoria</h1>
          <p className="text-codexia-light/80 mt-1">
            Visão geral do enxoval: compras, estoque, lavanderia e uso
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={carregarAuditoria}
            className="px-4 py-2 rounded-lg bg-codexia-primary hover:bg-codexia-accent/20 text-codexia-accent border border-codexia-accent/50 flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Atualizar
          </button>
          <button
            onClick={executarAnaliseIA}
            disabled={analisando}
            className="px-4 py-2 rounded-lg bg-codexia-accent text-codexia-dark font-semibold hover:opacity-90 flex items-center gap-2 disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            {analisando ? "Analisando..." : "Análise com IA"}
          </button>
        </div>
      </header>

      {/* Cards de resumo */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Card
          icon={Package}
          label="Total Compras"
          value={resumo.totalCompras}
          sublabel="Histórico"
        />
        <Card
          icon={Home}
          label="Em Estoque"
          value={resumo.totalEstoque}
          sublabel="Disponível"
        />
        <Card
          icon={Truck}
          label="Na Lavanderia"
          value={resumo.totalLavanderia}
          sublabel="Em processamento"
        />
        <Card
          icon={Shirt}
          label="Em Uso"
          value={resumo.totalEmUso}
          sublabel="Nos quartos"
        />
        <Card
          icon={AlertTriangle}
          label="Desfalque"
          value={resumo.desfalque}
          sublabel="Itens perdidos"
          alert={resumo.desfalque > 0}
        />
      </div>

      {/* Alerta de desfalque */}
      {resumo.desfalque > 0 && (
        <div className="p-4 rounded-xl bg-amber-500/20 border border-amber-500/50 text-amber-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold">Desfalque detectado!</h3>
              <p>
                Há {resumo.desfalque} itens de enxoval que foram comprados mas não estão
                contabilizados (estoque + lavanderia + uso). Execute a análise com IA para
                identificar possíveis causas.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Gráfico */}
      <div className="bg-codexia-secondary/50 rounded-xl p-6 border border-codexia-primary/30">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          Distribuição por Tipo de Enxoval
        </h2>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0f766e" opacity={0.3} />
              <XAxis dataKey="nome" stroke="#ccfbf1" fontSize={12} />
              <YAxis stroke="#ccfbf1" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#134e4a",
                  border: "1px solid #0f766e",
                  borderRadius: "8px",
                }}
              />
              <Legend />
              <Bar dataKey="Compras" fill="#0f766e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Estoque" fill="#2dd4bf" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Lavanderia" fill="#14b8a6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Em Uso" fill="#5eead4" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Desfalque" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tabela detalhada */}
      <div className="bg-codexia-secondary/50 rounded-xl overflow-hidden border border-codexia-primary/30">
        <h2 className="text-xl font-semibold p-6 pb-0">Detalhamento por Tipo</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-codexia-primary/30">
                <th className="text-left p-4 font-medium">Tipo</th>
                <th className="text-right p-4 font-medium">Compras</th>
                <th className="text-right p-4 font-medium">Estoque</th>
                <th className="text-right p-4 font-medium">Lavanderia</th>
                <th className="text-right p-4 font-medium">Em Uso</th>
                <th className="text-right p-4 font-medium">Total Atual</th>
                <th className="text-right p-4 font-medium">Desfalque</th>
              </tr>
            </thead>
            <tbody>
              {resumo.porTipo.map((t) => (
                <tr
                  key={t.tipoId}
                  className="border-b border-codexia-primary/20 hover:bg-codexia-primary/10"
                >
                  <td className="p-4">{t.tipoNome}</td>
                  <td className="p-4 text-right">{t.totalCompras}</td>
                  <td className="p-4 text-right">{t.emEstoque}</td>
                  <td className="p-4 text-right">{t.naLavanderia}</td>
                  <td className="p-4 text-right">{t.emUso}</td>
                  <td className="p-4 text-right">{t.totalAtual}</td>
                  <td
                    className={clsx(
                      "p-4 text-right font-medium",
                      t.desfalque > 0 && "text-amber-400"
                    )}
                  >
                    {t.desfalque}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Análise IA */}
      {resumo.analiseIA && (
        <div className="bg-codexia-secondary/50 rounded-xl p-6 border border-codexia-accent/30">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-codexia-accent" />
            Análise da IA
          </h2>
          <div className="prose prose-invert prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-codexia-light/90 bg-codexia-dark/50 p-4 rounded-lg overflow-x-auto">
              {resumo.analiseIA}
            </pre>
          </div>
        </div>
      )}

      {/* Formulários rápidos */}
      {(showFormCompra || showFormMov) && (
        <div className="grid md:grid-cols-2 gap-6">
          <FormCompra
            tipos={tipos}
            show={showFormCompra}
            onClose={() => setShowFormCompra(false)}
            onSuccess={() => {
              setShowFormCompra(false);
              carregarAuditoria();
            }}
          />
          <FormMovimentacao
            tipos={tipos}
            show={showFormMov}
            onClose={() => setShowFormMov(false)}
            onSuccess={() => {
              setShowFormMov(false);
              carregarAuditoria();
            }}
          />
        </div>
      )}

      <div className="flex gap-4 flex-wrap">
        <button
          onClick={() => setShowFormCompra(true)}
          className="px-6 py-3 rounded-xl bg-codexia-primary hover:bg-codexia-accent/20 text-codexia-accent border border-codexia-accent/50 flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Registrar Compra
        </button>
        <button
          onClick={() => setShowFormMov(true)}
          className="px-6 py-3 rounded-xl bg-codexia-primary hover:bg-codexia-accent/20 text-codexia-accent border border-codexia-accent/50 flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Registrar Movimentação
        </button>
      </div>
    </div>
  );
}

function Card({
  icon: Icon,
  label,
  value,
  sublabel,
  alert,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  sublabel: string;
  alert?: boolean;
}) {
  return (
    <div
      className={clsx(
        "p-4 rounded-xl border",
        alert
          ? "bg-amber-500/10 border-amber-500/50"
          : "bg-codexia-secondary/50 border-codexia-primary/30"
      )}
    >
      <div className="flex items-center gap-2 text-codexia-light/70 text-sm mb-1">
        <Icon className="w-4 h-4" />
        {sublabel}
      </div>
      <p className="text-2xl font-bold text-codexia-accent">{value}</p>
      <p className="text-sm text-codexia-light/80">{label}</p>
    </div>
  );
}

function FormCompra({
  tipos,
  show,
  onClose,
  onSuccess,
}: {
  tipos: { id: string; nome: string }[];
  show: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    tipoId: "",
    quantidade: "",
    dataCompra: new Date().toISOString().slice(0, 10),
    fornecedor: "",
    observacao: "",
  });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetch("/api/compras", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setForm({ tipoId: "", quantidade: "", dataCompra: new Date().toISOString().slice(0, 10), fornecedor: "", observacao: "" });
    onSuccess();
  };

  if (!show) return null;

  return (
    <div className="bg-codexia-secondary/50 rounded-xl p-6 border border-codexia-primary/30">
      <h3 className="text-lg font-semibold mb-4">Nova Compra</h3>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="block text-sm text-codexia-light/80 mb-1">Tipo</label>
          <select
            required
            value={form.tipoId}
            onChange={(e) => setForm({ ...form, tipoId: e.target.value })}
            className="w-full px-3 py-2 rounded-lg bg-codexia-dark border border-codexia-primary/50 text-codexia-light"
          >
            <option value="">Selecione...</option>
            {tipos.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm text-codexia-light/80 mb-1">Quantidade</label>
          <input
            type="number"
            required
            min="1"
            value={form.quantidade}
            onChange={(e) => setForm({ ...form, quantidade: e.target.value })}
            className="w-full px-3 py-2 rounded-lg bg-codexia-dark border border-codexia-primary/50 text-codexia-light"
          />
        </div>
        <div>
          <label className="block text-sm text-codexia-light/80 mb-1">Data</label>
          <input
            type="date"
            value={form.dataCompra}
            onChange={(e) => setForm({ ...form, dataCompra: e.target.value })}
            className="w-full px-3 py-2 rounded-lg bg-codexia-dark border border-codexia-primary/50 text-codexia-light"
          />
        </div>
        <div>
          <label className="block text-sm text-codexia-light/80 mb-1">Fornecedor</label>
          <input
            type="text"
            value={form.fornecedor}
            onChange={(e) => setForm({ ...form, fornecedor: e.target.value })}
            className="w-full px-3 py-2 rounded-lg bg-codexia-dark border border-codexia-primary/50 text-codexia-light"
          />
        </div>
        <div className="flex gap-2">
          <button
            type="submit"
            className="px-4 py-2 rounded-lg bg-codexia-accent text-codexia-dark font-medium"
          >
            Salvar
          </button>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-codexia-primary/50 text-codexia-light/80"
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  );
}

function FormMovimentacao({
  tipos,
  show,
  onClose,
  onSuccess,
}: {
  tipos: { id: string; nome: string }[];
  show: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    tipoId: "",
    quantidade: "",
    tipoMov: "SAIDA_LAVANDERIA",
    origem: "",
    observacao: "",
  });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetch("/api/movimentacoes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setForm({ tipoId: "", quantidade: "", tipoMov: "SAIDA_LAVANDERIA", origem: "", observacao: "" });
    onSuccess();
  };

  if (!show) return null;

  return (
    <div className="bg-codexia-secondary/50 rounded-xl p-6 border border-codexia-primary/30">
      <h3 className="text-lg font-semibold mb-4">Nova Movimentação</h3>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="block text-sm text-codexia-light/80 mb-1">Tipo</label>
          <select
            required
            value={form.tipoId}
            onChange={(e) => setForm({ ...form, tipoId: e.target.value })}
            className="w-full px-3 py-2 rounded-lg bg-codexia-dark border border-codexia-primary/50 text-codexia-light"
          >
            <option value="">Selecione...</option>
            {tipos.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm text-codexia-light/80 mb-1">Tipo de Movimentação</label>
          <select
            value={form.tipoMov}
            onChange={(e) => setForm({ ...form, tipoMov: e.target.value })}
            className="w-full px-3 py-2 rounded-lg bg-codexia-dark border border-codexia-primary/50 text-codexia-light"
          >
            <option value="ENTRADA_ESTOQUE">Entrada no Estoque</option>
            <option value="SAIDA_LAVANDERIA">Saída para Lavanderia</option>
            <option value="RETORNO_LAVANDERIA">Retorno da Lavanderia</option>
            <option value="SAIDA_USO">Saída para Uso (quarto)</option>
            <option value="RETORNO_USO">Retorno do Uso (quarto → lavanderia)</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-codexia-light/80 mb-1">Quantidade</label>
          <input
            type="number"
            required
            min="1"
            value={form.quantidade}
            onChange={(e) => setForm({ ...form, quantidade: e.target.value })}
            className="w-full px-3 py-2 rounded-lg bg-codexia-dark border border-codexia-primary/50 text-codexia-light"
          />
        </div>
        <div>
          <label className="block text-sm text-codexia-light/80 mb-1">Origem (ex: Quarto 101)</label>
          <input
            type="text"
            value={form.origem}
            onChange={(e) => setForm({ ...form, origem: e.target.value })}
            placeholder="Opcional"
            className="w-full px-3 py-2 rounded-lg bg-codexia-dark border border-codexia-primary/50 text-codexia-light"
          />
        </div>
        <div className="flex gap-2">
          <button
            type="submit"
            className="px-4 py-2 rounded-lg bg-codexia-accent text-codexia-dark font-medium"
          >
            Registrar
          </button>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-codexia-primary/50 text-codexia-light/80"
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  );
}
