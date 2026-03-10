import { DailyMovement, LinenItem } from "./types";

export const initialItems: LinenItem[] = [
  {
    id: "lencol-casal-premium",
    nome: "Lençol casal premium",
    categoria: "Cama",
    custoUnitario: 85,
    minimoEstoque: 90,
    compradoTotal: 320,
    estoqueAtual: 72,
    emLavanderia: 118,
    emUso: 96,
    perdasRegistradas: 12,
    lavanderiaEnviadoHoje: 44,
    lavanderiaRetornadoHoje: 26,
    usoMovimentadoHoje: 38,
    setorCritico: "Lavanderia terceirizada",
    ultimaContagem: "2026-03-10 06:30"
  },
  {
    id: "toalha-banho-hotelaria",
    nome: "Toalha de banho hotelaria",
    categoria: "Banho",
    custoUnitario: 48,
    minimoEstoque: 140,
    compradoTotal: 540,
    estoqueAtual: 120,
    emLavanderia: 166,
    emUso: 210,
    perdasRegistradas: 18,
    lavanderiaEnviadoHoje: 58,
    lavanderiaRetornadoHoje: 33,
    usoMovimentadoHoje: 44,
    setorCritico: "Governança e lavanderia",
    ultimaContagem: "2026-03-10 06:30"
  },
  {
    id: "fronha-5070",
    nome: "Fronha 50x70",
    categoria: "Cama",
    custoUnitario: 18,
    minimoEstoque: 220,
    compradoTotal: 690,
    estoqueAtual: 210,
    emLavanderia: 150,
    emUso: 280,
    perdasRegistradas: 14,
    lavanderiaEnviadoHoje: 62,
    lavanderiaRetornadoHoje: 50,
    usoMovimentadoHoje: 56,
    setorCritico: "Andares e rouparia",
    ultimaContagem: "2026-03-10 06:30"
  },
  {
    id: "toalha-piso",
    nome: "Toalha de piso",
    categoria: "Apoio",
    custoUnitario: 22,
    minimoEstoque: 85,
    compradoTotal: 400,
    estoqueAtual: 60,
    emLavanderia: 132,
    emUso: 150,
    perdasRegistradas: 20,
    lavanderiaEnviadoHoje: 41,
    lavanderiaRetornadoHoje: 21,
    usoMovimentadoHoje: 35,
    setorCritico: "Lavanderia interna",
    ultimaContagem: "2026-03-10 06:30"
  },
  {
    id: "cobertor-queen",
    nome: "Cobertor queen",
    categoria: "Cama",
    custoUnitario: 140,
    minimoEstoque: 24,
    compradoTotal: 96,
    estoqueAtual: 18,
    emLavanderia: 12,
    emUso: 54,
    perdasRegistradas: 4,
    lavanderiaEnviadoHoje: 8,
    lavanderiaRetornadoHoje: 4,
    usoMovimentadoHoje: 5,
    setorCritico: "Rouparia central",
    ultimaContagem: "2026-03-10 06:30"
  }
];

export const initialMovements: DailyMovement[] = [
  {
    id: "mov-001",
    data: "2026-03-10 05:50",
    itemId: "toalha-banho-hotelaria",
    tipo: "laundry_out",
    quantidade: 32,
    setor: "Lavanderia",
    responsavel: "Equipe rouparia",
    observacao: "Envio do lote da madrugada para terceirizada."
  },
  {
    id: "mov-002",
    data: "2026-03-10 06:10",
    itemId: "lencol-casal-premium",
    tipo: "laundry_in",
    quantidade: 16,
    setor: "Lavanderia",
    responsavel: "Recebimento",
    observacao: "Retorno parcial com divergencia de 4 pecas no romaneio."
  },
  {
    id: "mov-003",
    data: "2026-03-10 07:15",
    itemId: "fronha-5070",
    tipo: "allocated_use",
    quantidade: 30,
    setor: "Governança",
    responsavel: "Supervisão de andares",
    observacao: "Reposicao de quartos em check-out."
  },
  {
    id: "mov-004",
    data: "2026-03-10 08:20",
    itemId: "toalha-piso",
    tipo: "loss",
    quantidade: 6,
    setor: "Lavanderia interna",
    responsavel: "Controle operacional",
    observacao: "Avarias por rasgo identificadas na triagem."
  },
  {
    id: "mov-005",
    data: "2026-03-10 09:10",
    itemId: "cobertor-queen",
    tipo: "returned_use",
    quantidade: 3,
    setor: "Rouparia",
    responsavel: "Camareira lider",
    observacao: "Retorno de apartamentos bloqueados para manutencao."
  },
  {
    id: "mov-006",
    data: "2026-03-10 10:05",
    itemId: "toalha-banho-hotelaria",
    tipo: "purchase",
    quantidade: 20,
    setor: "Compras",
    responsavel: "Suprimentos",
    observacao: "Reposicao emergencial aprovada pela gerencia."
  }
];
