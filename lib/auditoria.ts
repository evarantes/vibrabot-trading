import { prisma } from "./prisma";
import { startOfDay, subDays } from "date-fns";

export type EstadoEnxoval = {
  tipoId: string;
  tipoNome: string;
  totalCompras: number;
  emEstoque: number;
  naLavanderia: number;
  emUso: number;
  totalAtual: number;
  desfalque: number;
  parLevel: number;
};

export type ResumoAuditoria = {
  data: Date;
  totalCompras: number;
  totalEstoque: number;
  totalLavanderia: number;
  totalEmUso: number;
  totalEsperado: number;
  totalAtual: number;
  desfalque: number;
  porTipo: EstadoEnxoval[];
};

export async function calcularEstadoEnxoval(data: Date): Promise<ResumoAuditoria> {
  const tipos = await prisma.tipoEnxoval.findMany();
  const dataInicio = startOfDay(data);

  const compras = await prisma.compraEnxoval.findMany({
    where: { dataCompra: { lte: dataInicio } },
  });

  const movimentacoes = await prisma.movimentacaoEnxoval.findMany({
    where: { data: { lte: dataInicio } },
  });

  const porTipo: EstadoEnxoval[] = tipos.map((tipo) => {
    const comprasTipo = compras.filter((c) => c.tipoId === tipo.id);
    const totalCompras = comprasTipo.reduce((s, c) => s + c.quantidade, 0);

    const movsTipo = movimentacoes
      .filter((m) => m.tipoId === tipo.id)
      .sort((a, b) => a.data.getTime() - b.data.getTime());

    let emEstoque = 0;
    let naLavanderia = 0;
    let emUso = 0;

    for (const m of movsTipo) {
      switch (m.tipoMov) {
        case "ENTRADA_ESTOQUE":
          emEstoque += m.quantidade;
          break;
        case "SAIDA_LAVANDERIA":
          emEstoque -= m.quantidade;
          naLavanderia += m.quantidade;
          break;
        case "RETORNO_LAVANDERIA":
          naLavanderia -= m.quantidade;
          emEstoque += m.quantidade;
          break;
        case "SAIDA_USO":
          emEstoque -= m.quantidade;
          emUso += m.quantidade;
          break;
        case "RETORNO_USO":
          emUso -= m.quantidade;
          naLavanderia += m.quantidade; // Sai do quarto e vai para lavanderia
          break;
      }
    }

    // Se não há movimentações, estoque = compras (tudo novo)
    if (movsTipo.length === 0 && totalCompras > 0) {
      emEstoque = totalCompras;
    }

    const totalAtual = emEstoque + naLavanderia + emUso;
    const desfalque = totalCompras - totalAtual;

    return {
      tipoId: tipo.id,
      tipoNome: tipo.nome,
      totalCompras,
      emEstoque,
      naLavanderia,
      emUso,
      totalAtual,
      desfalque,
      parLevel: tipo.parLevel,
    };
  });

  const totalCompras = porTipo.reduce((s, t) => s + t.totalCompras, 0);
  const totalEstoque = porTipo.reduce((s, t) => s + t.emEstoque, 0);
  const totalLavanderia = porTipo.reduce((s, t) => s + t.naLavanderia, 0);
  const totalEmUso = porTipo.reduce((s, t) => s + t.emUso, 0);
  const totalAtual = porTipo.reduce((s, t) => s + t.totalAtual, 0);
  const desfalque = porTipo.reduce((s, t) => s + t.desfalque, 0);

  return {
    data: dataInicio,
    totalCompras,
    totalEstoque,
    totalLavanderia,
    totalEmUso,
    totalEsperado: totalCompras,
    totalAtual,
    desfalque,
    porTipo,
  };
}

export async function obterHistoricoAuditoria(dias: number = 30) {
  const hoje = new Date();
  const snapshots = await prisma.snapshotAuditoria.findMany({
    where: {
      data: { gte: subDays(hoje, dias) },
    },
    orderBy: { data: "desc" },
  });
  return snapshots;
}
