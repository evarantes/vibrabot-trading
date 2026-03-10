"use client";

import { useEffect, useState, useCallback } from "react";
import PageHeader from "@/components/PageHeader";
import Badge from "@/components/Badge";
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingDown,
  Lightbulb,
  RefreshCw,
  BarChart3,
} from "lucide-react";
import type { AuditItemResult } from "@/lib/audit-engine";

interface AuditResponse {
  report: {
    id: string;
    date: string;
    totalPurchased: number;
    totalStock: number;
    totalInLaundry: number;
    totalInUse: number;
    totalMissing: number;
    percentMissing: number;
    riskLevel: string;
    findings: string;
    recommendations: string;
    status: string;
  };
  details: {
    items: AuditItemResult[];
    findings: string[];
    recommendations: string[];
  };
}

interface HistoryReport {
  id: string;
  date: string;
  totalMissing: number;
  percentMissing: number;
  riskLevel: string;
  status: string;
}

const riskColors: Record<string, string> = {
  critico: "bg-red-500",
  alto: "bg-orange-500",
  medio: "bg-amber-500",
  baixo: "bg-yellow-400",
  ok: "bg-emerald-500",
};

const riskBadge: Record<string, "danger" | "warning" | "success" | "info"> = {
  critico: "danger",
  alto: "warning",
  medio: "warning",
  baixo: "info",
  ok: "success",
};

export default function AuditoriaPage() {
  const [auditResult, setAuditResult] = useState<AuditResponse | null>(null);
  const [history, setHistory] = useState<HistoryReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);

  const loadHistory = useCallback(() => {
    fetch("/api/audit")
      .then((r) => r.json())
      .then((d) => {
        setHistory(d);
        setHistoryLoading(false);
      });
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const runAudit = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/audit", { method: "POST" });
      const data = await res.json();
      setAuditResult(data);
      loadHistory();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Auditoria Inteligente"
        description="Análise por IA para detectar discrepâncias e desfalques no enxoval"
        action={
          <button
            onClick={runAudit}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors disabled:opacity-50"
          >
            {loading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <ShieldCheck className="w-4 h-4" />
            )}
            {loading ? "Analisando..." : "Executar Auditoria"}
          </button>
        }
      />

      {auditResult && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-card-border p-6">
            <div className="flex items-center gap-3 mb-4">
              <div
                className={`w-4 h-4 rounded-full ${riskColors[auditResult.report.riskLevel]}`}
              />
              <h2 className="text-lg font-bold">Resultado da Auditoria</h2>
              <Badge variant={riskBadge[auditResult.report.riskLevel]} size="md">
                Risco {auditResult.report.riskLevel.toUpperCase()}
              </Badge>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
              <div className="text-center p-3 bg-blue-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">
                  {auditResult.report.totalPurchased}
                </p>
                <p className="text-xs text-blue-600">Comprado</p>
              </div>
              <div className="text-center p-3 bg-emerald-50 rounded-lg">
                <p className="text-2xl font-bold text-emerald-600">
                  {auditResult.report.totalStock}
                </p>
                <p className="text-xs text-emerald-600">Em Estoque</p>
              </div>
              <div className="text-center p-3 bg-cyan-50 rounded-lg">
                <p className="text-2xl font-bold text-cyan-600">
                  {auditResult.report.totalInLaundry}
                </p>
                <p className="text-xs text-cyan-600">Na Lavanderia</p>
              </div>
              <div className="text-center p-3 bg-purple-50 rounded-lg">
                <p className="text-2xl font-bold text-purple-600">
                  {auditResult.report.totalInUse}
                </p>
                <p className="text-xs text-purple-600">Em Uso</p>
              </div>
              <div className="text-center p-3 bg-red-50 rounded-lg">
                <p className="text-2xl font-bold text-red-600">
                  {auditResult.report.totalMissing}
                </p>
                <p className="text-xs text-red-600">
                  Desaparecido ({auditResult.report.percentMissing.toFixed(1)}%)
                </p>
              </div>
            </div>

            <div className="w-full bg-slate-100 rounded-full h-4 mb-2 overflow-hidden">
              <div className="h-full flex">
                {auditResult.report.totalPurchased > 0 && (
                  <>
                    <div
                      className="bg-emerald-500 h-full"
                      style={{
                        width: `${(auditResult.report.totalStock / auditResult.report.totalPurchased) * 100}%`,
                      }}
                    />
                    <div
                      className="bg-cyan-500 h-full"
                      style={{
                        width: `${(auditResult.report.totalInLaundry / auditResult.report.totalPurchased) * 100}%`,
                      }}
                    />
                    <div
                      className="bg-purple-500 h-full"
                      style={{
                        width: `${(auditResult.report.totalInUse / auditResult.report.totalPurchased) * 100}%`,
                      }}
                    />
                    <div
                      className="bg-red-500 h-full"
                      style={{
                        width: `${(auditResult.report.totalMissing / auditResult.report.totalPurchased) * 100}%`,
                      }}
                    />
                  </>
                )}
              </div>
            </div>
            <div className="flex gap-4 text-xs text-muted">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> Estoque
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-cyan-500" /> Lavanderia
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-purple-500" /> Em Uso
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500" /> Desaparecido
              </span>
            </div>
          </div>

          {auditResult.details.findings.length > 0 && (
            <div className="bg-white rounded-xl border border-card-border p-6">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <h3 className="text-lg font-bold">Achados da Auditoria</h3>
              </div>
              <div className="space-y-2">
                {auditResult.details.findings.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-100 rounded-lg"
                  >
                    {f.includes("CRITICO") ? (
                      <XCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                    ) : f.includes("ALERTA") ? (
                      <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
                    ) : (
                      <TrendingDown className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                    )}
                    <p className="text-sm">{f}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {auditResult.details.recommendations.length > 0 && (
            <div className="bg-white rounded-xl border border-card-border p-6">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="w-5 h-5 text-blue-500" />
                <h3 className="text-lg font-bold">Recomendações da IA</h3>
              </div>
              <div className="space-y-2">
                {auditResult.details.recommendations.map((r, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-100 rounded-lg"
                  >
                    <CheckCircle className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                    <p className="text-sm">{r}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {auditResult.details.items.length > 0 && (
            <div className="bg-white rounded-xl border border-card-border p-6">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-bold">Detalhamento por Item</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-card-border">
                      <th className="px-3 py-2 text-left text-xs font-semibold text-muted uppercase">Item</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold text-muted uppercase">Comprado</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold text-muted uppercase">Estoque</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold text-muted uppercase">Lavanderia</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold text-muted uppercase">Em Uso</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold text-muted uppercase">Desaparecido</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold text-muted uppercase">% Perda</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold text-muted uppercase">Risco</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-card-border">
                    {auditResult.details.items.map((item) => (
                      <tr key={item.itemId} className="hover:bg-slate-50">
                        <td className="px-3 py-2">
                          <div className="font-medium text-sm">{item.itemName}</div>
                          <div className="text-xs text-muted">{item.categoryName}</div>
                        </td>
                        <td className="px-3 py-2 text-center text-sm">{item.totalPurchased}</td>
                        <td className="px-3 py-2 text-center text-sm">{item.currentStock}</td>
                        <td className="px-3 py-2 text-center text-sm">{item.inLaundry}</td>
                        <td className="px-3 py-2 text-center text-sm">{item.inUse}</td>
                        <td className="px-3 py-2 text-center text-sm font-semibold text-red-600">
                          {item.missing}
                        </td>
                        <td className="px-3 py-2 text-center text-sm">
                          {item.percentMissing.toFixed(1)}%
                        </td>
                        <td className="px-3 py-2 text-center">
                          <Badge variant={riskBadge[item.riskLevel]}>
                            {item.riskLevel.toUpperCase()}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {!auditResult && !historyLoading && (
        <div className="bg-white rounded-xl border border-card-border p-12 text-center">
          <ShieldCheck className="w-16 h-16 text-primary mx-auto mb-4 opacity-30" />
          <h3 className="text-lg font-semibold mb-2">Nenhuma auditoria executada</h3>
          <p className="text-muted text-sm mb-4">
            Clique em &quot;Executar Auditoria&quot; para a IA analisar todo o enxoval,
            identificar discrepâncias e gerar recomendações.
          </p>
          <p className="text-muted text-xs">
            A auditoria cruza dados de compras, estoque, lavanderia e uso nos quartos
            para encontrar onde estão os desfalques.
          </p>
        </div>
      )}

      {history.length > 0 && (
        <div className="mt-6 bg-white rounded-xl border border-card-border p-6">
          <h3 className="text-lg font-bold mb-4">Histórico de Auditorias</h3>
          <div className="space-y-2">
            {history.map((h) => (
              <div
                key={h.id}
                className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-3 h-3 rounded-full ${riskColors[h.riskLevel]}`}
                  />
                  <span className="text-sm font-medium">
                    {new Date(h.date).toLocaleDateString("pt-BR")}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-muted">
                    {h.totalMissing} desaparecidos ({h.percentMissing.toFixed(1)}%)
                  </span>
                  <Badge variant={riskBadge[h.riskLevel]}>
                    {h.riskLevel.toUpperCase()}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
