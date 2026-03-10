import { useEffect, useState } from 'react'
import { ClipboardList, Play, Trash2, ChevronDown, ChevronUp, Eye, TrendingDown } from 'lucide-react'
import { auditApi, type AuditReport } from '../api'
import Modal from '../components/Modal'
import { FormField, Input } from '../components/FormField'
import EmptyState from '../components/EmptyState'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import ReactMarkdown from 'react-markdown'

interface AuditDetail {
  item_type_id: number
  item_nome: string
  categoria: string
  total_comprado: number
  total_estoque: number
  total_na_lavanderia: number
  total_em_uso: number
  total_contabilizado: number
  desfalque: number
  percentual_desfalque: number
}

interface PreviewData {
  totais: {
    total_comprado: number
    total_estoque: number
    total_na_lavanderia: number
    total_em_uso: number
    total_contabilizado: number
    total_desfalque: number
    percentual_desfalque_geral: number
  }
  itens_detalhados: AuditDetail[]
}

export default function Auditoria() {
  const [auditorias, setAuditorias] = useState<AuditReport[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [viewModal, setViewModal] = useState<AuditReport | null>(null)
  const [generating, setGenerating] = useState(false)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [expanded, setExpanded] = useState<number[]>([])
  const [form, setForm] = useState({
    titulo: `Auditoria ${format(new Date(), 'dd/MM/yyyy HH:mm')}`,
    periodo_inicio: '',
    periodo_fim: '',
  })

  const carregar = () => {
    auditApi.list().then(r => setAuditorias(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { carregar() }, [])

  const carregarPreview = async () => {
    setPreviewLoading(true)
    try {
      const params: Record<string, string> = {}
      if (form.periodo_inicio) params.periodo_inicio = new Date(form.periodo_inicio).toISOString()
      if (form.periodo_fim) params.periodo_fim = new Date(form.periodo_fim).toISOString()
      const r = await auditApi.preview(params)
      setPreview(r.data)
    } finally {
      setPreviewLoading(false)
    }
  }

  const gerar = async () => {
    if (!form.titulo.trim()) return
    setGenerating(true)
    try {
      await auditApi.generate({
        titulo: form.titulo,
        periodo_inicio: form.periodo_inicio ? new Date(form.periodo_inicio).toISOString() : undefined,
        periodo_fim: form.periodo_fim ? new Date(form.periodo_fim).toISOString() : undefined,
      })
      setModalOpen(false)
      setPreview(null)
      carregar()
    } finally { setGenerating(false) }
  }

  const deletar = async (id: number) => {
    if (!confirm('Remover esta auditoria?')) return
    await auditApi.delete(id)
    carregar()
  }

  const toggleExpand = (id: number) => {
    setExpanded(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const getReportDetail = (a: AuditReport): PreviewData | null => {
    try {
      const json = JSON.parse(a.relatorio_json)
      return json.resultado || null
    } catch { return null }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Auditoria de Enxoval</h2>
          <p className="text-sm text-slate-500">{auditorias.length} auditoria(s) realizada(s)</p>
        </div>
        <button onClick={() => { setModalOpen(true); setPreview(null) }} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors">
          <Play size={16} /> Nova Auditoria
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : auditorias.length === 0 ? (
        <EmptyState
          icon={<ClipboardList size={32} />}
          title="Nenhuma auditoria realizada"
          description="Gere uma auditoria para analisar o desfalque de enxoval com suporte de IA."
          action={<button onClick={() => setModalOpen(true)} className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors">Gerar Auditoria</button>}
        />
      ) : (
        <div className="space-y-3">
          {auditorias.map(a => {
            const detail = getReportDetail(a)
            const isExpanded = expanded.includes(a.id)
            const percentual = a.total_comprado && a.total_desfalque
              ? ((a.total_desfalque / a.total_comprado) * 100).toFixed(1)
              : '0'
            const severity = Number(percentual) > 10 ? 'rose' : Number(percentual) > 5 ? 'amber' : Number(percentual) > 0 ? 'amber' : 'emerald'

            return (
              <div key={a.id} className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
                <div className="p-5">
                  <div className="flex items-start gap-4">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      severity === 'rose' ? 'bg-rose-600/20' : severity === 'amber' ? 'bg-amber-600/20' : 'bg-emerald-600/20'
                    }`}>
                      <TrendingDown size={22} className={
                        severity === 'rose' ? 'text-rose-400' : severity === 'amber' ? 'text-amber-400' : 'text-emerald-400'
                      } />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-base font-semibold text-white truncate">{a.titulo}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {format(new Date(a.created_at), "dd 'de' MMMM 'de' yyyy 'às' HH:mm", { locale: ptBR })}
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
                        <div>
                          <div className="text-xs text-slate-500">Comprado</div>
                          <div className="text-sm font-semibold text-white">{a.total_comprado?.toLocaleString() || 0}</div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500">Estoque</div>
                          <div className="text-sm font-semibold text-emerald-400">{a.total_estoque?.toLocaleString() || 0}</div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500">Lavanderia</div>
                          <div className="text-sm font-semibold text-blue-400">{a.total_lavanderia?.toLocaleString() || 0}</div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500">Desfalque</div>
                          <div className={`text-sm font-bold ${(a.total_desfalque || 0) > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                            {a.total_desfalque?.toLocaleString() || 0} <span className="text-xs font-normal">({percentual}%)</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button onClick={() => setViewModal(a)} className="p-2 text-slate-500 hover:text-indigo-400 hover:bg-slate-800 rounded-lg transition-colors" title="Ver análise IA">
                        <Eye size={16} />
                      </button>
                      <button onClick={() => toggleExpand(a.id)} className="p-2 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                      <button onClick={() => deletar(a.id)} className="p-2 text-slate-600 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors">
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Detalhes expandidos */}
                {isExpanded && detail && (
                  <div className="border-t border-slate-800">
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-slate-800 bg-slate-950/50">
                            <th className="px-4 py-2.5 text-xs font-medium text-slate-500 uppercase text-left">Item</th>
                            <th className="px-4 py-2.5 text-xs font-medium text-slate-500 uppercase text-right">Comprado</th>
                            <th className="px-4 py-2.5 text-xs font-medium text-slate-500 uppercase text-right">Estoque</th>
                            <th className="px-4 py-2.5 text-xs font-medium text-slate-500 uppercase text-right">Lavanderia</th>
                            <th className="px-4 py-2.5 text-xs font-medium text-slate-500 uppercase text-right">Em Uso</th>
                            <th className="px-4 py-2.5 text-xs font-medium text-slate-500 uppercase text-right">Desfalque</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                          {detail.itens_detalhados.map(item => (
                            <tr key={item.item_type_id} className={`hover:bg-slate-800/30 transition-colors ${item.desfalque > 0 ? 'bg-rose-950/10' : ''}`}>
                              <td className="px-4 py-2.5 text-sm text-white">{item.item_nome}</td>
                              <td className="px-4 py-2.5 text-sm text-slate-400 text-right">{item.total_comprado}</td>
                              <td className="px-4 py-2.5 text-sm text-emerald-400 text-right">{item.total_estoque}</td>
                              <td className="px-4 py-2.5 text-sm text-blue-400 text-right">{item.total_na_lavanderia}</td>
                              <td className="px-4 py-2.5 text-sm text-violet-400 text-right">{item.total_em_uso}</td>
                              <td className="px-4 py-2.5 text-right">
                                <span className={`text-sm font-semibold ${item.desfalque > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                                  {item.desfalque > 0 ? `-${item.desfalque}` : '✓'}
                                  {item.desfalque > 0 && <span className="text-xs font-normal ml-1">({item.percentual_desfalque}%)</span>}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Modal Nova Auditoria */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Gerar Nova Auditoria" size="xl">
        <div className="space-y-5">
          <FormField label="Título da Auditoria" required>
            <Input value={form.titulo} onChange={e => setForm(f => ({ ...f, titulo: e.target.value }))} placeholder="Ex: Auditoria Mensal - Março 2026" />
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Período Início" hint="Opcional — filtra compras pelo período">
              <Input type="datetime-local" value={form.periodo_inicio} onChange={e => setForm(f => ({ ...f, periodo_inicio: e.target.value }))} />
            </FormField>
            <FormField label="Período Fim">
              <Input type="datetime-local" value={form.periodo_fim} onChange={e => setForm(f => ({ ...f, periodo_fim: e.target.value }))} />
            </FormField>
          </div>

          <button onClick={carregarPreview} disabled={previewLoading} className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-xl text-sm transition-colors flex items-center justify-center gap-2">
            {previewLoading ? (
              <><div className="w-4 h-4 border-2 border-slate-500 border-t-transparent rounded-full animate-spin" /> Carregando preview...</>
            ) : (
              <><Eye size={16} /> Visualizar dados antes de gerar</>
            )}
          </button>

          {/* Preview */}
          {preview && (
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="text-xs font-medium text-slate-400 uppercase">Preview da Auditoria</div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: 'Comprado', value: preview.totais.total_comprado, color: 'text-white' },
                  { label: 'Estoque', value: preview.totais.total_estoque, color: 'text-emerald-400' },
                  { label: 'Lavanderia', value: preview.totais.total_na_lavanderia, color: 'text-blue-400' },
                  { label: 'Desfalque', value: preview.totais.total_desfalque, color: preview.totais.total_desfalque > 0 ? 'text-rose-400' : 'text-emerald-400' },
                ].map(s => (
                  <div key={s.label} className="bg-slate-900 rounded-xl p-3">
                    <div className="text-xs text-slate-500">{s.label}</div>
                    <div className={`text-lg font-bold ${s.color}`}>{s.value}</div>
                  </div>
                ))}
              </div>

              {preview.itens_detalhados.filter(i => i.desfalque > 0).length > 0 && (
                <div>
                  <div className="text-xs text-rose-400 mb-2">Itens com desfalque:</div>
                  {preview.itens_detalhados.filter(i => i.desfalque > 0).map(i => (
                    <div key={i.item_type_id} className="flex justify-between text-xs py-1 border-b border-slate-800">
                      <span className="text-slate-300">{i.item_nome}</span>
                      <span className="text-rose-400 font-semibold">-{i.desfalque} ({i.percentual_desfalque}%)</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="bg-indigo-950/30 border border-indigo-900/30 rounded-xl p-3 text-xs text-indigo-300">
            🤖 A IA irá analisar os dados e gerar um relatório detalhado com diagnóstico, causas prováveis e recomendações.
            {!window.location.hostname.includes('localhost') || true ? ' A análise usará o motor heurístico interno se a chave OpenAI não estiver configurada.' : ''}
          </div>

          <div className="flex gap-3 pt-2">
            <button onClick={() => setModalOpen(false)} className="flex-1 px-4 py-2.5 border border-slate-700 text-slate-300 rounded-xl text-sm hover:bg-slate-800 transition-colors">Cancelar</button>
            <button
              onClick={gerar}
              disabled={generating || !form.titulo.trim()}
              className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {generating ? (
                <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Gerando auditoria...</>
              ) : (
                <><Play size={16} /> Gerar Auditoria com IA</>
              )}
            </button>
          </div>
        </div>
      </Modal>

      {/* Modal Análise IA */}
      <Modal open={!!viewModal} onClose={() => setViewModal(null)} title="Análise da IA" size="xl">
        {viewModal?.analise_ia && (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{viewModal.analise_ia}</ReactMarkdown>
          </div>
        )}
      </Modal>
    </div>
  )
}
