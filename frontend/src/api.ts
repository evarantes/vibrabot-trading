import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export default api

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ItemType {
  id: number
  nome: string
  categoria: string
  descricao?: string
  created_at: string
}

export interface Purchase {
  id: number
  item_type_id: number
  quantidade: number
  fornecedor?: string
  valor_unitario?: number
  nota_fiscal?: string
  observacoes?: string
  data_compra: string
  created_at: string
  item_type?: ItemType
}

export interface StockMovement {
  id: number
  item_type_id: number
  tipo: string
  quantidade: number
  motivo?: string
  observacoes?: string
  data_movimento: string
  created_at: string
  item_type?: ItemType
}

export interface StockSummary {
  item_type_id: number
  item_nome: string
  categoria: string
  total_comprado: number
  saldo_estoque: number
}

export interface LaundryRecord {
  id: number
  item_type_id: number
  quantidade_enviada: number
  quantidade_retornada: number
  lavanderia_nome?: string
  data_envio: string
  data_retorno?: string
  status: string
  observacoes?: string
  created_at: string
  item_type?: ItemType
}

export interface RoomAssignment {
  id: number
  item_type_id: number
  numero_quarto: string
  andar?: string
  quantidade: number
  data_atribuicao: string
  data_retirada?: string
  ativo: number
  observacoes?: string
  created_at: string
  item_type?: ItemType
}

export interface AuditReport {
  id: number
  titulo: string
  periodo_inicio?: string
  periodo_fim?: string
  relatorio_json: string
  analise_ia?: string
  total_comprado?: number
  total_estoque?: number
  total_lavanderia?: number
  total_em_uso?: number
  total_desfalque?: number
  created_at: string
}

export interface DashboardStats {
  total_tipos_item: number
  total_comprado: number
  total_estoque: number
  total_na_lavanderia: number
  total_em_uso: number
  total_desfalque: number
  percentual_desfalque: number
  alertas: string[]
  ultimas_auditorias: AuditReport[]
}

// ── API Calls ─────────────────────────────────────────────────────────────────

export const itemsApi = {
  list: () => api.get<ItemType[]>('/items/'),
  create: (data: Omit<ItemType, 'id' | 'created_at'>) => api.post<ItemType>('/items/', data),
  update: (id: number, data: Omit<ItemType, 'id' | 'created_at'>) => api.put<ItemType>(`/items/${id}`, data),
  delete: (id: number) => api.delete(`/items/${id}`),
}

export const purchasesApi = {
  list: (params?: Record<string, string>) => api.get<Purchase[]>('/purchases/', { params }),
  create: (data: Omit<Purchase, 'id' | 'created_at' | 'item_type'>) => api.post<Purchase>('/purchases/', data),
  delete: (id: number) => api.delete(`/purchases/${id}`),
}

export const stockApi = {
  list: (params?: Record<string, string>) => api.get<StockMovement[]>('/stock/', { params }),
  create: (data: Omit<StockMovement, 'id' | 'created_at' | 'item_type'>) => api.post<StockMovement>('/stock/', data),
  summary: () => api.get<StockSummary[]>('/stock/summary'),
  delete: (id: number) => api.delete(`/stock/${id}`),
}

export const laundryApi = {
  list: (params?: Record<string, string>) => api.get<LaundryRecord[]>('/laundry/', { params }),
  create: (data: Omit<LaundryRecord, 'id' | 'created_at' | 'item_type'>) => api.post<LaundryRecord>('/laundry/', data),
  registerReturn: (id: number, data: { quantidade_retornada: number; data_retorno: string; status?: string }) =>
    api.patch<LaundryRecord>(`/laundry/${id}/retorno`, data),
  pendentes: () => api.get<LaundryRecord[]>('/laundry/pendentes'),
  summary: () => api.get('/laundry/summary'),
  delete: (id: number) => api.delete(`/laundry/${id}`),
}

export const roomsApi = {
  list: (params?: Record<string, string>) => api.get<RoomAssignment[]>('/rooms/', { params }),
  create: (data: Omit<RoomAssignment, 'id' | 'created_at' | 'item_type'>) => api.post<RoomAssignment>('/rooms/', data),
  retirar: (id: number, data: { data_retirada: string }) => api.patch<RoomAssignment>(`/rooms/${id}/retirar`, data),
  emUsoSummary: () => api.get('/rooms/em-uso/summary'),
  quartos: () => api.get('/rooms/quartos'),
  delete: (id: number) => api.delete(`/rooms/${id}`),
}

export const auditApi = {
  list: () => api.get<AuditReport[]>('/audit/'),
  get: (id: number) => api.get<AuditReport>(`/audit/${id}`),
  preview: (params?: { periodo_inicio?: string; periodo_fim?: string }) =>
    api.get('/audit/preview', { params }),
  generate: (data: { titulo: string; periodo_inicio?: string; periodo_fim?: string }) =>
    api.post<AuditReport>('/audit/gerar', data),
  delete: (id: number) => api.delete(`/audit/${id}`),
}

export const dashboardApi = {
  stats: () => api.get<DashboardStats>('/dashboard/stats'),
}
