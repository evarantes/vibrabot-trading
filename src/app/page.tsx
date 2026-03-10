"use client";

import { useEffect, useState } from "react";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import Badge from "@/components/Badge";
import {
  ShoppingCart,
  Package,
  WashingMachine,
  BedDouble,
  AlertTriangle,
  DollarSign,
  TrendingUp,
  Percent,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface DashboardData {
  summary: {
    totalItems: number;
    totalCategories: number;
    totalPurchased: number;
    totalInvested: number;
    totalStock: number;
    totalInLaundry: number;
    totalInUse: number;
    totalMissing: number;
    totalDamaged: number;
    laundryReturnRate: string;
  };
  charts: {
    laundryByDay: { date: string; sent: number; returned: number }[];
    purchasesByMonth: { month: string; quantity: number; total: number }[];
    distribution: {
      stock: number;
      lavanderia: number;
      emUso: number;
      desaparecido: number;
    };
  };
  lastAudit: {
    riskLevel: string;
    percentMissing: number;
    findings: string;
    date: string;
  } | null;
}

const COLORS = ["#22c55e", "#3b82f6", "#f59e0b", "#ef4444"];

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/dashboard")
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-muted">Carregando dashboard...</div>
      </div>
    );
  }

  if (!data) return null;

  const { summary, charts } = data;

  const pieData = [
    { name: "Em Estoque", value: charts.distribution.stock },
    { name: "Lavanderia", value: charts.distribution.lavanderia },
    { name: "Em Uso", value: charts.distribution.emUso },
    { name: "Desaparecido", value: charts.distribution.desaparecido },
  ].filter((d) => d.value > 0);

  const riskVariant =
    data.lastAudit?.riskLevel === "critico"
      ? "danger"
      : data.lastAudit?.riskLevel === "alto"
        ? "warning"
        : data.lastAudit?.riskLevel === "medio"
          ? "warning"
          : "success";

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Visão geral do enxoval hoteleiro"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard
          title="Total Comprado"
          value={summary.totalPurchased}
          subtitle={`${formatCurrency(summary.totalInvested)} investido`}
          icon={ShoppingCart}
          color="blue"
        />
        <StatCard
          title="Em Estoque"
          value={summary.totalStock}
          subtitle={`${summary.totalItems} itens cadastrados`}
          icon={Package}
          color="green"
        />
        <StatCard
          title="Na Lavanderia"
          value={summary.totalInLaundry}
          subtitle={`Taxa retorno: ${summary.laundryReturnRate}%`}
          icon={WashingMachine}
          color="cyan"
        />
        <StatCard
          title="Em Uso"
          value={summary.totalInUse}
          subtitle="Nos quartos hoje"
          icon={BedDouble}
          color="purple"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard
          title="Desaparecidos"
          value={summary.totalMissing}
          subtitle="Peças não localizadas"
          icon={AlertTriangle}
          color="red"
        />
        <StatCard
          title="Danificados"
          value={summary.totalDamaged}
          subtitle="Na lavanderia"
          icon={AlertTriangle}
          color="yellow"
        />
        <StatCard
          title="Investimento Total"
          value={formatCurrency(summary.totalInvested)}
          icon={DollarSign}
          color="green"
        />
        <StatCard
          title="Taxa de Retorno"
          value={`${summary.laundryReturnRate}%`}
          subtitle="Lavanderia"
          icon={Percent}
          color="cyan"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl border border-card-border p-5">
          <h3 className="text-sm font-semibold text-foreground mb-4">
            Distribuição do Enxoval
          </h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                  label={({ name, percent }) =>
                    `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`
                  }
                >
                  {pieData.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[280px] text-muted text-sm">
              Sem dados para exibir
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-card-border p-5">
          <h3 className="text-sm font-semibold text-foreground mb-4">
            Lavanderia - Últimos 30 dias
          </h3>
          {charts.laundryByDay.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={charts.laundryByDay}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => v.slice(5)}
                />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar
                  dataKey="sent"
                  name="Enviado"
                  fill="#3b82f6"
                  radius={[2, 2, 0, 0]}
                />
                <Bar
                  dataKey="returned"
                  name="Retornado"
                  fill="#22c55e"
                  radius={[2, 2, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[280px] text-muted text-sm">
              Sem dados de lavanderia
            </div>
          )}
        </div>
      </div>

      {data.lastAudit && (
        <div className="bg-white rounded-xl border border-card-border p-5">
          <div className="flex items-center gap-3 mb-3">
            <TrendingUp className="w-5 h-5 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">
              Última Auditoria
            </h3>
            <Badge variant={riskVariant}>
              Risco {data.lastAudit.riskLevel.toUpperCase()}
            </Badge>
          </div>
          <p className="text-sm text-muted">
            {data.lastAudit.percentMissing.toFixed(1)}% de desfalque detectado
          </p>
          {data.lastAudit.findings && (
            <ul className="mt-2 space-y-1">
              {JSON.parse(data.lastAudit.findings)
                .slice(0, 5)
                .map((f: string, i: number) => (
                  <li key={i} className="text-sm text-muted flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                    {f}
                  </li>
                ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
