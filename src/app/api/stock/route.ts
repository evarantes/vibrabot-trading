import { prisma } from "@/lib/prisma";
import { NextRequest, NextResponse } from "next/server";

export async function GET() {
  const items = await prisma.item.findMany({
    include: {
      category: true,
      stockCounts: {
        orderBy: { date: "desc" },
        take: 1,
      },
      purchases: true,
    },
    orderBy: { name: "asc" },
  });

  const stockData = items.map((item) => ({
    id: item.id,
    name: item.name,
    category: item.category.name,
    categoryId: item.categoryId,
    unit: item.unit,
    minStock: item.minStock,
    currentStock: item.stockCounts[0]?.quantity ?? 0,
    lastCountDate: item.stockCounts[0]?.date ?? null,
    totalPurchased: item.purchases.reduce((sum, p) => sum + p.quantity, 0),
  }));

  return NextResponse.json(stockData);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const dateValue = new Date(body.date + "T12:00:00.000Z");

  const stockCount = await prisma.stockCount.upsert({
    where: {
      itemId_date: {
        itemId: body.itemId,
        date: dateValue,
      },
    },
    update: {
      quantity: body.quantity,
      location: body.location,
      notes: body.notes,
    },
    create: {
      itemId: body.itemId,
      date: dateValue,
      quantity: body.quantity,
      location: body.location,
      notes: body.notes,
    },
    include: { item: true },
  });
  return NextResponse.json(stockCount, { status: 201 });
}
