export type LinenCategory = "Cama" | "Banho" | "Mesa" | "Apoio";

export type MovementType =
  | "purchase"
  | "laundry_out"
  | "laundry_in"
  | "allocated_use"
  | "returned_use"
  | "loss";

export type Severity = "critico" | "alto" | "moderado" | "estavel";

export interface LinenItem {
  id: string;
  nome: string;
  categoria: LinenCategory;
  custoUnitario: number;
  minimoEstoque: number;
  compradoTotal: number;
  estoqueAtual: number;
  emLavanderia: number;
  emUso: number;
  perdasRegistradas: number;
  lavanderiaEnviadoHoje: number;
  lavanderiaRetornadoHoje: number;
  usoMovimentadoHoje: number;
  setorCritico: string;
  ultimaContagem: string;
}

export interface DailyMovement {
  id: string;
  data: string;
  itemId: string;
  tipo: MovementType;
  quantidade: number;
  setor: string;
  responsavel: string;
  observacao: string;
}

export interface ItemAudit {
  itemId: string;
  itemNome: string;
  desaparecidas: number;
  excesso: number;
  valorEmRisco: number;
  estoqueCobertura: number;
  retornoLavanderia: number;
  focoProvavel: string;
  severidade: Severity;
  mensagem: string;
}

export interface SectorRisk {
  setor: string;
  quantidadeEmRisco: number;
  valorEmRisco: number;
  itensAfetados: number;
}

export interface AuditInsight {
  titulo: string;
  descricao: string;
  severidade: Severity;
}

export interface AuditSummary {
  totalComprado: number;
  totalEstoque: number;
  totalEmLavanderia: number;
  totalEmUso: number;
  totalPerdas: number;
  totalDesaparecido: number;
  valorEmRisco: number;
  itensCriticos: ItemAudit[];
  auditoriaPorItem: ItemAudit[];
  riscosPorSetor: SectorRisk[];
  insights: AuditInsight[];
  relatorioExecutivo: string;
}
