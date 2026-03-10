import { prisma } from "@/lib/prisma";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const dateStr = searchParams.get("date");

  const where = dateStr
    ? {
        date: {
          gte: new Date(dateStr + "T00:00:00.000Z"),
          lte: new Date(dateStr + "T23:59:59.999Z"),
        },
      }
    : {};

  const records = await prisma.laundryRecord.findMany({
    where,
    include: { item: { include: { category: true } } },
    orderBy: { date: "desc" },
  });
  return NextResponse.json(records);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const dateValue = new Date(body.date + "T12:00:00.000Z");

  const record = await prisma.laundryRecord.upsert({
    where: {
      itemId_date: {
        itemId: body.itemId,
        date: dateValue,
      },
    },
    update: {
      sentQuantity: body.sentQuantity ?? undefined,
      returnedQuantity: body.returnedQuantity ?? undefined,
      damagedQuantity: body.damagedQuantity ?? undefined,
      notes: body.notes ?? undefined,
    },
    create: {
      itemId: body.itemId,
      date: dateValue,
      sentQuantity: body.sentQuantity || 0,
      returnedQuantity: body.returnedQuantity || 0,
      damagedQuantity: body.damagedQuantity || 0,
      notes: body.notes,
    },
    include: { item: { include: { category: true } } },
  });
  return NextResponse.json(record, { status: 201 });
}
