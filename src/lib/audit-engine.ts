import { prisma } from "./prisma";

export interface AuditItemResult {
  itemId: string;
  itemName: string;
  categoryName: string;
  totalPurchased: number;
  currentStock: number;
  inLaundry: number;
  inUse: number;
  accounted: number;
  missing: number;
  percentMissing: number;
  riskLevel: "critico" | "alto" | "medio" | "baixo" | "ok";
  findings: string[];
  laundryReturnRate: number;
  avgDailyUsage: number;
}

export interface AuditSummary {
  date: Date;
  totalPurchased: number;
  totalStock: number;
  totalInLaundry: number;
  totalInUse: number;
  totalMissing: number;
  percentMissing: number;
  riskLevel: string;
  items: AuditItemResult[];
  findings: string[];
  recommendations: string[];
}

function getRiskLevel(percentMissing: number): "critico" | "alto" | "medio" | "baixo" | "ok" {
  if (percentMissing >= 20) return "critico";
  if (percentMissing >= 10) return "alto";
  if (percentMissing >= 5) return "medio";
  if (percentMissing > 0) return "baixo";
  return "ok";
}

export async function runAudit(): Promise<AuditSummary> {
  const today = new Date();
  today.setHours(23, 59, 59, 999);

  const items = await prisma.item.findMany({
    include: {
      category: true,
      purchases: true,
      laundryRecords: {
        orderBy: { date: "desc" },
      },
      stockCounts: {
        orderBy: { date: "desc" },
        take: 1,
      },
      roomUsages: {
        orderBy: { date: "desc" },
      },
    },
  });

  const auditItems: AuditItemResult[] = [];
  const globalFindings: string[] = [];
  const recommendations: string[] = [];

  let grandTotalPurchased = 0;
  let grandTotalStock = 0;
  let grandTotalInLaundry = 0;
  let grandTotalInUse = 0;

  for (const item of items) {
    const totalPurchased = item.purchases.reduce((sum, p) => sum + p.quantity, 0);

    const currentStock = item.stockCounts.length > 0 ? item.stockCounts[0].quantity : 0;

    const totalSent = item.laundryRecords.reduce((sum, r) => sum + r.sentQuantity, 0);
    const totalReturned = item.laundryRecords.reduce((sum, r) => sum + r.returnedQuantity, 0);
    const totalDamaged = item.laundryRecords.reduce((sum, r) => sum + r.damagedQuantity, 0);
    const inLaundry = Math.max(0, totalSent - totalReturned - totalDamaged);

    const todayStr = today.toISOString().split("T")[0];
    const inUse = item.roomUsages
      .filter((r) => r.date.toISOString().split("T")[0] === todayStr)
      .reduce((sum, r) => sum + r.quantity, 0);

    const accounted = currentStock + inLaundry + inUse;
    const missing = Math.max(0, totalPurchased - accounted);
    const percentMissing = totalPurchased > 0 ? (missing / totalPurchased) * 100 : 0;
    const riskLevel = getRiskLevel(percentMissing);

    const laundryReturnRate =
      totalSent > 0 ? ((totalReturned / totalSent) * 100) : 100;

    const uniqueDays = new Set(item.roomUsages.map((r) => r.date.toISOString().split("T")[0]));
    const avgDailyUsage =
      uniqueDays.size > 0
        ? item.roomUsages.reduce((sum, r) => sum + r.quantity, 0) / uniqueDays.size
        : 0;

    const findings: string[] = [];

    if (percentMissing >= 20) {
      findings.push(
        `CRITICO: ${item.name} possui ${missing} unidades desaparecidas (${percentMissing.toFixed(1)}% do total comprado)`
      );
    } else if (percentMissing >= 10) {
      findings.push(
        `ALERTA: ${item.name} possui ${missing} unidades sem rastreamento (${percentMissing.toFixed(1)}%)`
      );
    } else if (missing > 0) {
      findings.push(
        `ATENÇÃO: ${item.name} possui ${missing} unidades não localizadas (${percentMissing.toFixed(1)}%)`
      );
    }

    if (laundryReturnRate < 90 && totalSent > 0) {
      findings.push(
        `Taxa de retorno da lavanderia para ${item.name}: ${laundryReturnRate.toFixed(1)}% - possível perda na lavanderia`
      );
    }

    if (totalDamaged > totalPurchased * 0.05) {
      findings.push(
        `${item.name}: ${totalDamaged} unidades danificadas na lavanderia (${((totalDamaged / totalPurchased) * 100).toFixed(1)}% do total)`
      );
    }

    if (currentStock < item.minStock && item.minStock > 0) {
      findings.push(
        `Estoque de ${item.name} (${currentStock}) abaixo do mínimo (${item.minStock})`
      );
    }

    if (currentStock > totalPurchased && totalPurchased > 0) {
      findings.push(
        `INCONSISTÊNCIA: Estoque de ${item.name} (${currentStock}) maior que total comprado (${totalPurchased})`
      );
    }

    auditItems.push({
      itemId: item.id,
      itemName: item.name,
      categoryName: item.category.name,
      totalPurchased,
      currentStock,
      inLaundry,
      inUse,
      accounted,
      missing,
      percentMissing,
      riskLevel,
      findings,
      laundryReturnRate,
      avgDailyUsage,
    });

    grandTotalPurchased += totalPurchased;
    grandTotalStock += currentStock;
    grandTotalInLaundry += inLaundry;
    grandTotalInUse += inUse;
    globalFindings.push(...findings);
  }

  const grandMissing = Math.max(0, grandTotalPurchased - (grandTotalStock + grandTotalInLaundry + grandTotalInUse));
  const grandPercentMissing = grandTotalPurchased > 0 ? (grandMissing / grandTotalPurchased) * 100 : 0;

  if (grandPercentMissing >= 15) {
    recommendations.push(
      "Implementar controle RFID ou código de barras para rastreamento individual de peças"
    );
    recommendations.push(
      "Realizar inventário físico completo e reconciliação com registros"
    );
  }

  const criticalItems = auditItems.filter((i) => i.riskLevel === "critico");
  if (criticalItems.length > 0) {
    recommendations.push(
      `Investigar urgentemente: ${criticalItems.map((i) => i.itemName).join(", ")} - níveis críticos de desaparecimento`
    );
  }

  const lowReturnItems = auditItems.filter((i) => i.laundryReturnRate < 90);
  if (lowReturnItems.length > 0) {
    recommendations.push(
      `Auditar processo da lavanderia para: ${lowReturnItems.map((i) => i.itemName).join(", ")} - taxa de retorno abaixo de 90%`
    );
    recommendations.push(
      "Considerar trocar de fornecedor de lavanderia ou implementar contagem na coleta e entrega"
    );
  }

  const lowStockItems = auditItems.filter(
    (i) => i.currentStock < (items.find((it) => it.id === i.itemId)?.minStock ?? 0)
  );
  if (lowStockItems.length > 0) {
    recommendations.push(
      `Reabastecer estoque de: ${lowStockItems.map((i) => i.itemName).join(", ")}`
    );
  }

  if (grandPercentMissing >= 5) {
    recommendations.push(
      "Estabelecer processo de contagem diária por turno com dupla conferência"
    );
    recommendations.push(
      "Instalar câmeras nas áreas de armazenamento e lavanderia"
    );
  }

  if (recommendations.length === 0 && globalFindings.length === 0) {
    recommendations.push("Sistema de enxoval operando dentro dos parâmetros normais. Manter monitoramento regular.");
  }

  return {
    date: today,
    totalPurchased: grandTotalPurchased,
    totalStock: grandTotalStock,
    totalInLaundry: grandTotalInLaundry,
    totalInUse: grandTotalInUse,
    totalMissing: grandMissing,
    percentMissing: grandPercentMissing,
    riskLevel: getRiskLevel(grandPercentMissing),
    items: auditItems.sort((a, b) => b.percentMissing - a.percentMissing),
    findings: globalFindings,
    recommendations,
  };
}
