import { NextResponse } from "next/server";
import { startOfDay } from "date-fns";
import { calcularEstadoEnxoval } from "@/lib/auditoria";
import { analisarAuditoriaIA } from "@/lib/ia-auditoria";
import { prisma } from "@/lib/prisma";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const dataParam = searchParams.get("data");
  const data = startOfDay(dataParam ? new Date(dataParam) : new Date());

  const resumo = await calcularEstadoEnxoval(data);
  return NextResponse.json(resumo);
}

export async function POST(request: Request) {
  const { analiseIA } = await request.json().catch(() => ({}));
  const data = startOfDay(new Date());

  const resumo = await calcularEstadoEnxoval(data);

  let analiseIATexto = "";
  if (analiseIA) {
    analiseIATexto = await analisarAuditoriaIA(resumo);
  }

  await prisma.snapshotAuditoria.upsert({
    where: { data },
    update: {
      totalCompras: resumo.totalCompras,
      totalEstoque: resumo.totalEstoque,
      totalLavanderia: resumo.totalLavanderia,
      totalEmUso: resumo.totalEmUso,
      totalEsperado: resumo.totalCompras,
      desfalque: resumo.desfalque,
      detalhes: JSON.stringify(resumo.porTipo),
      analiseIA: analiseIATexto || undefined,
    },
    create: {
      data,
      totalCompras: resumo.totalCompras,
      totalEstoque: resumo.totalEstoque,
      totalLavanderia: resumo.totalLavanderia,
      totalEmUso: resumo.totalEmUso,
      totalEsperado: resumo.totalCompras,
      desfalque: resumo.desfalque,
      detalhes: JSON.stringify(resumo.porTipo),
      analiseIA: analiseIATexto || undefined,
    },
  });

  return NextResponse.json({
    ...resumo,
    analiseIA: analiseIATexto,
  });
}
