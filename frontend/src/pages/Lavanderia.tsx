import { useEffect, useState } from 'react'
import { Plus, WashingMachine, CheckCircle, Trash2 } from 'lucide-react'
import { laundryApi, itemsApi, type LaundryRecord, type ItemType } from '../api'
import Modal from '../components/Modal'
import { FormField, Input, Select, TextArea } from '../components/FormField'
import { statusBadge } from '../components/Badge'
import EmptyState from '../components/EmptyState'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export default function Lavanderia() {
  const [registros, setRegistros] = useState<LaundryRecord[]>([])
  const [itens, setItens] = useState<ItemType[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [retornoModal, setRetornoModal] = useState<LaundryRecord | null>(null)
  const [saving, setSaving] = useState(false)
  const [filtro, setFiltro] = useState<'todos' | 'pendente' | 'parcial' | 'completo'>('todos')
  const [form, setForm] = useState({
    item_type_id: '',
    quantidade_enviada: '',
    lavanderia_nome: '',
    observacoes: '',
    data_envio: new Date().toISOString().slice(0, 16),
  })
  const [retornoForm, setRetornoForm] = useState({
    quantidade_retornada: '',
    data_retorno: new Date().toISOString().slice(0, 16),
  })

  const carregar = () => {
    Promise.all([laundryApi.list(), itemsApi.list()])
      .then(([r, i]) => { setRegistros(r.data); setItens(i.data) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { carregar() }, [])

  const salvar = async () => {
    if (!form.item_type_id || !form.quantidade_enviada) return
    setSaving(true)
    try {
      await laundryApi.create({
        item_type_id: Number(form.item_type_id),
        quantidade_enviada: Number(form.quantidade_enviada),
        quantidade_retornada: 0,
        lavanderia_nome: form.lavanderia_nome || undefined,
        observacoes: form.observacoes || undefined,
        data_envio: new Date(form.data_envio).toISOString(),
        status: 'pendente',
      })
      setModalOpen(false)
      setForm({ item_type_id: '', quantidade_enviada: '', lavanderia_nome: '', observacoes: '', data_envio: new Date().toISOString().slice(0, 16) })
      carregar()
    } finally { setSaving(false) }
  }

  const registrarRetorno = async () => {
    if (!retornoModal || !retornoForm.quantidade_retornada) return
    setSaving(true)
    try {
      await laundryApi.registerReturn(retornoModal.id, {
        quantidade_retornada: Number(retornoForm.quantidade_retornada),
        data_retorno: new Date(retornoForm.data_retorno).toISOString(),
      })
      setRetornoModal(null)
      carregar()
    } finally { setSaving(false) }
  }

  const deletar = async (id: number) => {
    if (!confirm('Remover este registro?')) return
    await laundryApi.delete(id)
    carregar()
  }

  const filtrados = registros.filter(r => filtro === 'todos' || r.status === filtro)
  const pendentes = registros.filter(r => r.status === 'pendente' || r.status === 'parcial')
  const totalNaLavanderia = pendentes.reduce((s, r) => s + (r.quantidade_enviada - r.quantidade_retornada), 0)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Controle de Lavanderia</h2>
          <p className="text-sm text-slate-500">
            {pendentes.length} lote(s) pendente(s) — {totalNaLavanderia} peças na lavanderia
          </p>
        </div>
        <button onClick={() => setModalOpen(true)} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors">
          <Plus size={16} /> Registrar Envio
        </button>
      </div>

      {/* Filtros */}
      <div className="flex gap-2 flex-wrap">
        {(['todos', 'pendente', 'parcial', 'completo'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFiltro(f)}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-colors border ${
              filtro === f
                ? 'bg-indigo-600/20 text-indigo-400 border-indigo-600/30'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f === 'pendente' && pendentes.filter(p => p.status === 'pendente').length > 0 && (
              <span className="ml-1.5 bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded-md">
                {pendentes.filter(p => p.status === 'pendente').length}
              </span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filtrados.length === 0 ? (
        <EmptyState
          icon={<WashingMachine size={32} />}
          title="Nenhum registro de lavanderia"
          description="Registre os envios de enxoval para a lavanderia e controle os retornos."
          action={<button onClick={() => setModalOpen(true)} className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors">Registrar Envio</button>}
        />
      ) : (
        <div className="space-y-3">
          {filtrados.map(r => (
            <div key={r.id} className={`bg-slate-900 border rounded-2xl p-4 ${r.status === 'pendente' || r.status === 'parcial' ? 'border-amber-800/30' : 'border-slate-800'}`}>
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-white">{r.item_type?.nome}</span>
                    {statusBadge(r.status)}
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
                    <div>
                      <div className="text-xs text-slate-500">Enviado</div>
                      <div className="text-sm font-semibold text-white">{r.quantidade_enviada}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500">Retornado</div>
                      <div className={`text-sm font-semibold ${r.quantidade_retornada < r.quantidade_enviada ? 'text-amber-400' : 'text-emerald-400'}`}>
                        {r.quantidade_retornada}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500">Diferença</div>
                      <div className={`text-sm font-semibold ${r.quantidade_enviada - r.quantidade_retornada > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                        {r.quantidade_enviada - r.quantidade_retornada}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500">Lavanderia</div>
                      <div className="text-sm text-slate-300">{r.lavanderia_nome || '—'}</div>
                    </div>
                  </div>
                  <div className="flex gap-4 mt-2 text-xs text-slate-500">
                    <span>Envio: {format(new Date(r.data_envio), 'dd/MM/yyyy', { locale: ptBR })}</span>
                    {r.data_retorno && <span>Retorno: {format(new Date(r.data_retorno), 'dd/MM/yyyy', { locale: ptBR })}</span>}
                  </div>
                  {r.observacoes && <p className="text-xs text-slate-500 mt-1">{r.observacoes}</p>}
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {(r.status === 'pendente' || r.status === 'parcial') && (
                    <button
                      onClick={() => {
                        setRetornoModal(r)
                        setRetornoForm({ quantidade_retornada: String(r.quantidade_enviada - r.quantidade_retornada), data_retorno: new Date().toISOString().slice(0, 16) })
                      }}
                      className="flex items-center gap-1.5 px-3 py-2 bg-emerald-600/20 text-emerald-400 border border-emerald-600/20 rounded-xl text-xs hover:bg-emerald-600/30 transition-colors"
                    >
                      <CheckCircle size={14} /> Retorno
                    </button>
                  )}
                  <button onClick={() => deletar(r.id)} className="p-2 text-slate-600 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors">
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Envio */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Registrar Envio para Lavanderia">
        <div className="space-y-4">
          <FormField label="Tipo de Enxoval" required>
            <Select value={form.item_type_id} onChange={e => setForm(f => ({ ...f, item_type_id: e.target.value }))}>
              <option value="">Selecione...</option>
              {itens.map(i => <option key={i.id} value={i.id}>{i.nome}</option>)}
            </Select>
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Quantidade Enviada" required>
              <Input type="number" min="1" value={form.quantidade_enviada} onChange={e => setForm(f => ({ ...f, quantidade_enviada: e.target.value }))} placeholder="0" />
            </FormField>
            <FormField label="Data de Envio" required>
              <Input type="datetime-local" value={form.data_envio} onChange={e => setForm(f => ({ ...f, data_envio: e.target.value }))} />
            </FormField>
          </div>
          <FormField label="Nome da Lavanderia">
            <Input value={form.lavanderia_nome} onChange={e => setForm(f => ({ ...f, lavanderia_nome: e.target.value }))} placeholder="Ex: Lavanderia Brilho" />
          </FormField>
          <FormField label="Observações">
            <TextArea value={form.observacoes} onChange={e => setForm(f => ({ ...f, observacoes: e.target.value }))} placeholder="Observações..." rows={2} />
          </FormField>
          <div className="flex gap-3 pt-2">
            <button onClick={() => setModalOpen(false)} className="flex-1 px-4 py-2.5 border border-slate-700 text-slate-300 rounded-xl text-sm hover:bg-slate-800 transition-colors">Cancelar</button>
            <button onClick={salvar} disabled={saving || !form.item_type_id || !form.quantidade_enviada} className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50">
              {saving ? 'Salvando...' : 'Registrar Envio'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Modal Retorno */}
      <Modal open={!!retornoModal} onClose={() => setRetornoModal(null)} title="Registrar Retorno da Lavanderia" size="sm">
        {retornoModal && (
          <div className="space-y-4">
            <div className="bg-slate-800 rounded-xl p-3 text-sm">
              <div className="text-white font-medium">{retornoModal.item_type?.nome}</div>
              <div className="text-slate-400 mt-1">Enviado: <span className="text-white">{retornoModal.quantidade_enviada}</span> | Já retornado: <span className="text-white">{retornoModal.quantidade_retornada}</span></div>
            </div>
            <FormField label="Quantidade Retornada" required>
              <Input
                type="number"
                min="0"
                max={retornoModal.quantidade_enviada}
                value={retornoForm.quantidade_retornada}
                onChange={e => setRetornoForm(f => ({ ...f, quantidade_retornada: e.target.value }))}
                placeholder="0"
              />
            </FormField>
            <FormField label="Data do Retorno" required>
              <Input type="datetime-local" value={retornoForm.data_retorno} onChange={e => setRetornoForm(f => ({ ...f, data_retorno: e.target.value }))} />
            </FormField>
            <div className="flex gap-3 pt-2">
              <button onClick={() => setRetornoModal(null)} className="flex-1 px-4 py-2.5 border border-slate-700 text-slate-300 rounded-xl text-sm hover:bg-slate-800 transition-colors">Cancelar</button>
              <button onClick={registrarRetorno} disabled={saving || !retornoForm.quantidade_retornada} className="flex-1 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50">
                {saving ? 'Salvando...' : 'Confirmar Retorno'}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
