import { AuditInsight, AuditSummary, ItemAudit, LinenItem, SectorRisk } from "./types";

const severityRank = {
  critico: 4,
  alto: 3,
  moderado: 2,
  estavel: 1
} as const;

const formatCurrency = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0
});

function clampRatio(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }

  return Math.max(0, Math.min(value, 1));
}

function determineFocus(item: LinenItem, desaparecidas: number, retornoLavanderia: number): string {
  if (desaparecidas === 0) {
    return "Sem evidencia critica";
  }

  if (item.emLavanderia >= item.emUso && retornoLavanderia < 0.75) {
    return "Lavanderia";
  }

  if (item.emUso > item.estoqueAtual && item.estoqueAtual < item.minimoEstoque) {
    return "Governança / apartamentos";
  }

  if (item.perdasRegistradas > Math.max(10, item.compradoTotal * 0.04)) {
    return "Avarias e descarte";
  }

  return "Conciliação do estoque";
}

function determineSeverity(item: LinenItem, desaparecidas: number, retornoLavanderia: number): ItemAudit["severidade"] {
  const cobertura = item.minimoEstoque === 0 ? 1 : item.estoqueAtual / item.minimoEstoque;

  if (desaparecidas >= 20 || (desaparecidas > 0 && retornoLavanderia < 0.6)) {
    return "critico";
  }

  if (desaparecidas >= 8 || cobertura < 0.75 || retornoLavanderia < 0.75) {
    return "alto";
  }

  if (desaparecidas > 0 || cobertura < 1) {
    return "moderado";
  }

  return "estavel";
}

function buildMessage(item: LinenItem, desaparecidas: number, retornoLavanderia: number, focoProvavel: string): string {
  if (desaparecidas === 0) {
    if (item.estoqueAtual < item.minimoEstoque) {
      return "Sem falta conciliada, mas o estoque esta abaixo do minimo operacional.";
    }

    return "Fluxo conciliado para o momento, sem indicio claro de desfalque.";
  }

  if (focoProvavel === "Lavanderia") {
    return `Ha ${desaparecidas} pecas sem rastreio e o retorno diario da lavanderia esta em ${(retornoLavanderia * 100).toFixed(0)}%.`;
  }

  if (focoProvavel === "Governança / apartamentos") {
    return `Ha ${desaparecidas} pecas sem conciliacao e a maior exposicao esta nos andares, com ${item.emUso} pecas em uso.`;
  }

  if (focoProvavel === "Avarias e descarte") {
    return `As perdas registradas ja somam ${item.perdasRegistradas} pecas; revise descarte, avarias e trocas sem baixa.`;
  }

  return `Ha ${desaparecidas} pecas nao explicadas pela contagem atual; revise contagem fisica e romaneios.`;
}

export function auditItem(item: LinenItem): ItemAudit {
  const totalConciliado = item.estoqueAtual + item.emLavanderia + item.emUso + item.perdasRegistradas;
  const desaparecidas = Math.max(item.compradoTotal - totalConciliado, 0);
  const excesso = Math.max(totalConciliado - item.compradoTotal, 0);
  const retornoLavanderia = item.lavanderiaEnviadoHoje === 0 ? 1 : clampRatio(item.lavanderiaRetornadoHoje / item.lavanderiaEnviadoHoje);
  const focoProvavel = determineFocus(item, desaparecidas, retornoLavanderia);
  const severidade = determineSeverity(item, desaparecidas, retornoLavanderia);

  return {
    itemId: item.id,
    itemNome: item.nome,
    desaparecidas,
    excesso,
    valorEmRisco: desaparecidas * item.custoUnitario,
    estoqueCobertura: item.minimoEstoque === 0 ? 1 : item.estoqueAtual / item.minimoEstoque,
    retornoLavanderia,
    focoProvavel,
    severidade,
    mensagem: buildMessage(item, desaparecidas, retornoLavanderia, focoProvavel)
  };
}

function buildSectorRisk(items: LinenItem[], auditoriaPorItem: ItemAudit[]): SectorRisk[] {
  const sectorMap = new Map<string, SectorRisk>();

  auditoriaPorItem.forEach((audit) => {
    if (audit.desaparecidas === 0 && audit.severidade === "estavel") {
      return;
    }

    const item = items.find((current) => current.id === audit.itemId);

    if (!item) {
      return;
    }

    const currentRisk = sectorMap.get(item.setorCritico) ?? {
      setor: item.setorCritico,
      quantidadeEmRisco: 0,
      valorEmRisco: 0,
      itensAfetados: 0
    };

    currentRisk.quantidadeEmRisco += audit.desaparecidas;
    currentRisk.valorEmRisco += audit.valorEmRisco;
    currentRisk.itensAfetados += 1;
    sectorMap.set(item.setorCritico, currentRisk);
  });

  return [...sectorMap.values()].sort((left, right) => right.valorEmRisco - left.valorEmRisco);
}

function buildInsights(items: LinenItem[], auditoriaPorItem: ItemAudit[], riscosPorSetor: SectorRisk[]): AuditInsight[] {
  const insights: AuditInsight[] = [];
  const totalDesaparecido = auditoriaPorItem.reduce((total, item) => total + item.desaparecidas, 0);
  const itemMaisCritico = auditoriaPorItem[0];
  const topSector = riscosPorSetor[0];
  const abaixoDoMinimo = items.filter((item) => item.estoqueAtual < item.minimoEstoque);
  const lavanderiaSobPressao = items.filter((item) => {
    const audit = auditoriaPorItem.find((current) => current.itemId === item.id);
    return audit ? audit.retornoLavanderia < 0.75 : false;
  });

  if (itemMaisCritico && totalDesaparecido > 0) {
    insights.push({
      titulo: "Desfalque consolidado identificado",
      descricao: `${totalDesaparecido} pecas ainda nao foram conciliadas. O item mais sensivel e ${itemMaisCritico.itemNome}.`,
      severidade: itemMaisCritico.severidade
    });
  }

  if (topSector) {
    insights.push({
      titulo: "Foco prioritario de auditoria",
      descricao: `${topSector.setor} concentra ${topSector.quantidadeEmRisco} pecas e ${formatCurrency.format(topSector.valorEmRisco)} em risco potencial.`,
      severidade: topSector.quantidadeEmRisco > 25 ? "critico" : "alto"
    });
  }

  if (lavanderiaSobPressao.length > 0) {
    insights.push({
      titulo: "Retorno de lavanderia abaixo do ideal",
      descricao: `${lavanderiaSobPressao.length} item(ns) retornaram menos de 75% do enviado hoje. Revise romaneios, triagem e conferencia de lotes.`,
      severidade: lavanderiaSobPressao.length >= 2 ? "alto" : "moderado"
    });
  }

  if (abaixoDoMinimo.length > 0) {
    insights.push({
      titulo: "Cobertura operacional comprometida",
      descricao: `${abaixoDoMinimo.length} item(ns) estao abaixo do estoque minimo. Isso aumenta risco de compra emergencial e mascara o ponto real da perda.`,
      severidade: abaixoDoMinimo.length >= 3 ? "alto" : "moderado"
    });
  }

  if (insights.length === 0) {
    insights.push({
      titulo: "Operacao equilibrada",
      descricao: "Nao ha indicio forte de desfalque no momento, mas continue alimentando os movimentos diarios para manter a rastreabilidade.",
      severidade: "estavel"
    });
  }

  return insights;
}

function buildExecutiveReport(items: LinenItem[], auditoriaPorItem: ItemAudit[], riscosPorSetor: SectorRisk[]): string {
  const totalDesaparecido = auditoriaPorItem.reduce((total, item) => total + item.desaparecidas, 0);
  const valorEmRisco = auditoriaPorItem.reduce((total, item) => total + item.valorEmRisco, 0);
  const criticos = auditoriaPorItem.filter((item) => item.severidade === "critico").length;
  const principalSetor = riscosPorSetor[0]?.setor ?? "sem setor critico";
  const itemMaisCritico = auditoriaPorItem[0]?.itemNome ?? "nenhum item";
  const itensAbaixoDoMinimo = items.filter((item) => item.estoqueAtual < item.minimoEstoque).length;

  if (totalDesaparecido === 0) {
    return "A auditoria atual nao encontrou desfalque consolidado. O foco deve permanecer na disciplina de registros, devolucoes e contagens fisicas.";
  }

  return `A auditoria do enxoval indica ${totalDesaparecido} pecas nao conciliadas, com risco estimado de ${formatCurrency.format(valorEmRisco)}. O item mais critico e ${itemMaisCritico}, e o principal ponto de investigacao neste momento e ${principalSetor}. Existem ${criticos} item(ns) em nivel critico e ${itensAbaixoDoMinimo} item(ns) abaixo do estoque minimo, o que sugere falha combinada entre operacao diaria e conferencia de retorno.`;
}

export function generateAuditSummary(items: LinenItem[]): AuditSummary {
  const auditoriaPorItem = items
    .map(auditItem)
    .sort((left, right) => {
      const severityDifference = severityRank[right.severidade] - severityRank[left.severidade];

      if (severityDifference !== 0) {
        return severityDifference;
      }

      return right.valorEmRisco - left.valorEmRisco;
    });

  const riscosPorSetor = buildSectorRisk(items, auditoriaPorItem);
  const insights = buildInsights(items, auditoriaPorItem, riscosPorSetor);

  return {
    totalComprado: items.reduce((total, item) => total + item.compradoTotal, 0),
    totalEstoque: items.reduce((total, item) => total + item.estoqueAtual, 0),
    totalEmLavanderia: items.reduce((total, item) => total + item.emLavanderia, 0),
    totalEmUso: items.reduce((total, item) => total + item.emUso, 0),
    totalPerdas: items.reduce((total, item) => total + item.perdasRegistradas, 0),
    totalDesaparecido: auditoriaPorItem.reduce((total, item) => total + item.desaparecidas, 0),
    valorEmRisco: auditoriaPorItem.reduce((total, item) => total + item.valorEmRisco, 0),
    itensCriticos: auditoriaPorItem.filter((item) => item.severidade === "critico" || item.severidade === "alto"),
    auditoriaPorItem,
    riscosPorSetor,
    insights,
    relatorioExecutivo: buildExecutiveReport(items, auditoriaPorItem, riscosPorSetor)
  };
}
