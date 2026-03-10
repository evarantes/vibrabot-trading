import { prisma } from "@/lib/prisma";
import { NextResponse } from "next/server";

export async function GET() {
  const [items, purchases, laundryRecords, stockCounts, roomUsages, lastAudit] =
    await Promise.all([
      prisma.item.findMany({ include: { category: true } }),
      prisma.purchase.findMany(),
      prisma.laundryRecord.findMany(),
      prisma.item.findMany({
        include: {
          stockCounts: { orderBy: { date: "desc" }, take: 1 },
        },
      }),
      prisma.roomUsage.findMany(),
      prisma.auditReport.findFirst({ orderBy: { date: "desc" } }),
    ]);

  const totalPurchased = purchases.reduce((sum, p) => sum + p.quantity, 0);
  const totalInvested = purchases.reduce((sum, p) => sum + p.totalPrice, 0);
  const totalStock = stockCounts.reduce(
    (sum, i) => sum + (i.stockCounts[0]?.quantity ?? 0),
    0
  );
  const totalSentLaundry = laundryRecords.reduce(
    (sum, r) => sum + r.sentQuantity,
    0
  );
  const totalReturnedLaundry = laundryRecords.reduce(
    (sum, r) => sum + r.returnedQuantity,
    0
  );
  const totalDamaged = laundryRecords.reduce(
    (sum, r) => sum + r.damagedQuantity,
    0
  );
  const totalInLaundry = Math.max(
    0,
    totalSentLaundry - totalReturnedLaundry - totalDamaged
  );

  const today = new Date().toISOString().split("T")[0];
  const totalInUse = roomUsages
    .filter((r) => r.date.toISOString().split("T")[0] === today)
    .reduce((sum, r) => sum + r.quantity, 0);

  const totalMissing = Math.max(
    0,
    totalPurchased - (totalStock + totalInLaundry + totalInUse)
  );

  const laundryByDay = laundryRecords.reduce(
    (acc, r) => {
      const day = r.date.toISOString().split("T")[0];
      if (!acc[day]) acc[day] = { sent: 0, returned: 0 };
      acc[day].sent += r.sentQuantity;
      acc[day].returned += r.returnedQuantity;
      return acc;
    },
    {} as Record<string, { sent: number; returned: number }>
  );

  const purchasesByMonth = purchases.reduce(
    (acc, p) => {
      const month = p.purchaseDate.toISOString().slice(0, 7);
      if (!acc[month]) acc[month] = { quantity: 0, total: 0 };
      acc[month].quantity += p.quantity;
      acc[month].total += p.totalPrice;
      return acc;
    },
    {} as Record<string, { quantity: number; total: number }>
  );

  return NextResponse.json({
    summary: {
      totalItems: items.length,
      totalCategories: new Set(items.map((i) => i.categoryId)).size,
      totalPurchased,
      totalInvested,
      totalStock,
      totalInLaundry,
      totalInUse,
      totalMissing,
      totalDamaged,
      laundryReturnRate:
        totalSentLaundry > 0
          ? ((totalReturnedLaundry / totalSentLaundry) * 100).toFixed(1)
          : "100",
    },
    charts: {
      laundryByDay: Object.entries(laundryByDay)
        .sort(([a], [b]) => a.localeCompare(b))
        .slice(-30)
        .map(([date, data]) => ({ date, ...data })),
      purchasesByMonth: Object.entries(purchasesByMonth)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([month, data]) => ({ month, ...data })),
      distribution: {
        stock: totalStock,
        lavanderia: totalInLaundry,
        emUso: totalInUse,
        desaparecido: totalMissing,
      },
    },
    lastAudit,
  });
}
