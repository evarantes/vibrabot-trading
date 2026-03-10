import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

const TIPOS_MOV = [
  "ENTRADA_ESTOQUE",
  "SAIDA_LAVANDERIA",
  "RETORNO_LAVANDERIA",
  "SAIDA_USO",
  "RETORNO_USO",
] as const;

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const tipoId = searchParams.get("tipoId");
  const data = searchParams.get("data");
  const limit = parseInt(searchParams.get("limit") || "50");

  const where: Record<string, unknown> = {};
  if (tipoId) where.tipoId = tipoId;
  if (data) where.data = { gte: new Date(data) };

  const movs = await prisma.movimentacaoEnxoval.findMany({
    where,
    include: { tipo: true },
    orderBy: { data: "desc" },
    take: limit,
  });
  return NextResponse.json(movs);
}

export async function POST(request: Request) {
  const body = await request.json();
  const { tipoId, quantidade, data, tipoMov, origem, destino, observacao } = body;

  if (!tipoId || !quantidade || !tipoMov) {
    return NextResponse.json(
      { error: "tipoId, quantidade e tipoMov são obrigatórios" },
      { status: 400 }
    );
  }

  if (!TIPOS_MOV.includes(tipoMov)) {
    return NextResponse.json(
      { error: `tipoMov deve ser um de: ${TIPOS_MOV.join(", ")}` },
      { status: 400 }
    );
  }

  const mov = await prisma.movimentacaoEnxoval.create({
    data: {
      tipoId,
      quantidade: parseInt(quantidade),
      data: data ? new Date(data) : new Date(),
      tipoMov,
      origem: origem || null,
      destino: destino || null,
      observacao: observacao || null,
    },
    include: { tipo: true },
  });

  return NextResponse.json(mov);
}
