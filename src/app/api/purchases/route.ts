import { prisma } from "@/lib/prisma";
import { NextRequest, NextResponse } from "next/server";

export async function GET() {
  const purchases = await prisma.purchase.findMany({
    include: { item: { include: { category: true } } },
    orderBy: { purchaseDate: "desc" },
  });
  return NextResponse.json(purchases);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const purchase = await prisma.purchase.create({
    data: {
      itemId: body.itemId,
      quantity: body.quantity,
      unitPrice: body.unitPrice || 0,
      totalPrice: (body.quantity || 0) * (body.unitPrice || 0),
      supplier: body.supplier,
      invoiceNumber: body.invoiceNumber,
      purchaseDate: new Date(body.purchaseDate),
      notes: body.notes,
    },
    include: { item: { include: { category: true } } },
  });
  return NextResponse.json(purchase, { status: 201 });
}
