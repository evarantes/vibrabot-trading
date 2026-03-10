import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  const compras = await prisma.compraEnxoval.findMany({
    include: { tipo: true },
    orderBy: { dataCompra: "desc" },
  });
  return NextResponse.json(compras);
}

export async function POST(request: Request) {
  const body = await request.json();
  const { tipoId, quantidade, dataCompra, fornecedor, valorTotal, observacao } = body;

  if (!tipoId || !quantidade) {
    return NextResponse.json(
      { error: "tipoId e quantidade são obrigatórios" },
      { status: 400 }
    );
  }

  const compra = await prisma.compraEnxoval.create({
    data: {
      tipoId,
      quantidade: parseInt(quantidade),
      dataCompra: dataCompra ? new Date(dataCompra) : new Date(),
      fornecedor: fornecedor || null,
      valorTotal: valorTotal ? parseFloat(valorTotal) : null,
      observacao: observacao || null,
    },
    include: { tipo: true },
  });

  // Registrar entrada no estoque
  await prisma.movimentacaoEnxoval.create({
    data: {
      tipoId,
      quantidade: parseInt(quantidade),
      data: dataCompra ? new Date(dataCompra) : new Date(),
      tipoMov: "ENTRADA_ESTOQUE",
      origem: fornecedor || "Compra",
      observacao: observacao || null,
    },
  });

  return NextResponse.json(compra);
}
