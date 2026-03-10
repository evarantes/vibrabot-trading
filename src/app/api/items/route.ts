import { prisma } from "@/lib/prisma";
import { NextRequest, NextResponse } from "next/server";

export async function GET() {
  const items = await prisma.item.findMany({
    include: { category: true },
    orderBy: { name: "asc" },
  });
  return NextResponse.json(items);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const item = await prisma.item.create({
    data: {
      categoryId: body.categoryId,
      name: body.name,
      description: body.description,
      unit: body.unit || "unidade",
      minStock: body.minStock || 0,
    },
    include: { category: true },
  });
  return NextResponse.json(item, { status: 201 });
}
