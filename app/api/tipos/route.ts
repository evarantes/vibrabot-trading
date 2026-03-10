import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  const tipos = await prisma.tipoEnxoval.findMany({
    orderBy: { nome: "asc" },
  });
  return NextResponse.json(tipos);
}

export async function POST(request: Request) {
  const body = await request.json();
  const { id, nome, descricao, parLevel } = body;

  if (!nome) {
    return NextResponse.json({ error: "nome é obrigatório" }, { status: 400 });
  }

  const tipo = await prisma.tipoEnxoval.create({
    data: {
      id: id || nome.toLowerCase().replace(/\s+/g, "-"),
      nome,
      descricao: descricao || null,
      parLevel: parLevel ? parseInt(parLevel) : 0,
    },
  });

  return NextResponse.json(tipo);
}
