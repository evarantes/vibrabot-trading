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

  const usages = await prisma.roomUsage.findMany({
    where,
    include: { item: { include: { category: true } } },
    orderBy: [{ date: "desc" }, { roomNumber: "asc" }],
  });
  return NextResponse.json(usages);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const usage = await prisma.roomUsage.create({
    data: {
      itemId: body.itemId,
      date: new Date(body.date + "T12:00:00.000Z"),
      roomNumber: body.roomNumber,
      quantity: body.quantity || 1,
      notes: body.notes,
    },
    include: { item: { include: { category: true } } },
  });
  return NextResponse.json(usage, { status: 201 });
}

export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) {
    return NextResponse.json({ error: "ID é obrigatório" }, { status: 400 });
  }

  await prisma.roomUsage.delete({ where: { id } });
  return NextResponse.json({ success: true });
}
