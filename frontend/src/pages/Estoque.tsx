import { useEffect, useState } from 'react'
import { Plus, Package, Trash2 } from 'lucide-react'
import { stockApi, itemsApi, type StockMovement, type StockSummary, type ItemType } from '../api'
import Modal from '../components/Modal'
import { FormField, Input, Select, TextArea } from '../components/FormField'
import { statusBadge } from '../components/Badge'
import EmptyState from '../components/EmptyState'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const TIPOS = [
  { value: 'entrada', label: 'Entrada' },
  { value: 'saida', label: 'Saída' },
  { value: 'ajuste', label: 'Ajuste' },
  { value: 'perda', label: 'Perda' },
  { value: 'descarte', label: 'Descarte' },
]

export default function Estoque() {
  const [movimentos, setMovimentos] = useState<StockMovement[]>([])
  const [resumo, setResumo] = useState<StockSummary[]>([])
  const [itens, setItens] = useState<ItemType[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [aba, setAba] = useState<'resumo' | 'movimentos'>('resumo')
  const [form, setForm] = useState({
    item_type_id: '',
    tipo: 'entrada',
    quantidade: '',
    motivo: '',
    observacoes: '',
    data_movimento: new Date().toISOString().slice(0, 16),
  })

  const carregar = () => {
    Promise.all([stockApi.list(), stockApi.summary(), itemsApi.list()])
      .then(([m, r, i]) => {
        setMovimentos(m.data)
        setResumo(r.data)
        setItens(i.data)
      }).finally(() => setLoading(false))
  }

  useEffect(() => { carregar() }, [])

  const salvar = async () => {
    if (!form.item_type_id || !form.quantidade) return
    setSaving(true)
    try {
      await stockApi.create({
        item_type_id: Number(form.item_type_id),
        tipo: form.tipo,
        quantidade: Number(form.quantidade),
        motivo: form.motivo || undefined,
        observacoes: form.observacoes || undefined,
        data_movimento: new Date(form.data_movimento).toISOString(),
      })
      setModalOpen(false)
      setForm({ item_type_id: '', tipo: 'entrada', quantidade: '', motivo: '', observacoes: '', data_movimento: new Date().toISOString().slice(0, 16) })
      carregar()
    } finally {
      setSaving(false)
    }
  }

  const deletar = async (id: number) => {
    if (!confirm('Remover este movimento?')) return
    await stockApi.delete(id)
    carregar()
  }

  const saldoTotal = resumo.reduce((s, r) => s + r.saldo_estoque, 0)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Controle de Estoque</h2>
          <p className="text-sm text-slate-500">Saldo total: {saldoTotal.toLocaleString()} peças</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors">
          <Plus size={16} /> Novo Movimento
        </button>
      </div>

      {/* Abas */}
      <div className="flex bg-slate-900 border border-slate-800 rounded-xl p-1 gap-1">
        {(['resumo', 'movimentos'] as const).map(a => (
          <button key={a} onClick={() => setAba(a)} className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${aba === a ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}>
            {a.charAt(0).toUpperCase() + a.slice(1)}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : aba === 'resumo' ? (
        resumo.length === 0 ? (
          <EmptyState icon={<Package size={32} />} title="Sem dados de estoque" description="Registre movimentos para ver o resumo." />
        ) : (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-800 text-left">
                    <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase">Item</th>
                    <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase">Categoria</th>
                    <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase text-right">Total Comprado</th>
                    <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase text-right">Saldo Estoque</th>
                    <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase text-right">%</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {resumo.map(r => {
                    const pct = r.total_comprado > 0 ? Math.round(r.saldo_estoque / r.total_comprado * 100) : 0
                    return (
                      <tr key={r.item_type_id} className="hover:bg-slate-800/50 transition-colors">
                        <td className="px-5 py-3.5 text-sm font-medium text-white">{r.item_nome}</td>
                        <td className="px-5 py-3.5 text-sm text-slate-500 capitalize">{r.categoria}</td>
                        <td className="px-5 py-3.5 text-sm text-slate-400 text-right">{r.total_comprado}</td>
                        <td className="px-5 py-3.5 text-right">
                          <span className={`text-sm font-semibold ${r.saldo_estoque > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {r.saldo_estoque}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-16 bg-slate-800 rounded-full h-1.5">
                              <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${Math.min(100, pct)}%` }} />
                            </div>
                            <span className="text-xs text-slate-500 w-8">{pct}%</span>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )
      ) : (
        movimentos.length === 0 ? (
          <EmptyState icon={<Package size={32} />} title="Sem movimentos" description="Nenhum movimento registrado ainda." />
        ) : (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-800 text-left">
                    <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase">Item</th>
                    <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase">Tipo</th>
                    <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase text-right">Qtd</th>
                    <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase hidden md:table-cell">Motivo</th>
                    <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase">Data</th>
                    <th className="px-2 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {movimentos.map(m => (
                    <tr key={m.id} className="hover:bg-slate-800/50 transition-colors">
                      <td className="px-5 py-3.5 text-sm font-medium text-white">{m.item_type?.nome}</td>
                      <td className="px-5 py-3.5">{statusBadge(m.tipo)}</td>
                      <td className="px-5 py-3.5 text-sm font-semibold text-right">
                        <span className={m.tipo === 'entrada' || m.tipo === 'ajuste' ? 'text-emerald-400' : 'text-rose-400'}>
                          {m.tipo === 'entrada' || m.tipo === 'ajuste' ? '+' : '-'}{m.quantidade}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-sm text-slate-500 hidden md:table-cell truncate max-w-xs">{m.motivo || '—'}</td>
                      <td className="px-5 py-3.5 text-sm text-slate-400 whitespace-nowrap">
                        {format(new Date(m.data_movimento), 'dd/MM/yyyy', { locale: ptBR })}
                      </td>
                      <td className="px-2 py-3.5">
                        <button onClick={() => deletar(m.id)} className="p-2 text-slate-600 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors">
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Registrar Movimento de Estoque">
        <div className="space-y-4">
          <FormField label="Tipo de Enxoval" required>
            <Select value={form.item_type_id} onChange={e => setForm(f => ({ ...f, item_type_id: e.target.value }))}>
              <option value="">Selecione...</option>
              {itens.map(i => <option key={i.id} value={i.id}>{i.nome}</option>)}
            </Select>
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Tipo de Movimento" required>
              <Select value={form.tipo} onChange={e => setForm(f => ({ ...f, tipo: e.target.value }))}>
                {TIPOS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </Select>
            </FormField>
            <FormField label="Quantidade" required>
              <Input type="number" min="1" value={form.quantidade} onChange={e => setForm(f => ({ ...f, quantidade: e.target.value }))} placeholder="0" />
            </FormField>
          </div>
          <FormField label="Motivo">
            <Input value={form.motivo} onChange={e => setForm(f => ({ ...f, motivo: e.target.value }))} placeholder="Ex: Inventário físico" />
          </FormField>
          <FormField label="Data" required>
            <Input type="datetime-local" value={form.data_movimento} onChange={e => setForm(f => ({ ...f, data_movimento: e.target.value }))} />
          </FormField>
          <FormField label="Observações">
            <TextArea value={form.observacoes} onChange={e => setForm(f => ({ ...f, observacoes: e.target.value }))} placeholder="Observações..." rows={2} />
          </FormField>
          <div className="flex gap-3 pt-2">
            <button onClick={() => setModalOpen(false)} className="flex-1 px-4 py-2.5 border border-slate-700 text-slate-300 rounded-xl text-sm hover:bg-slate-800 transition-colors">Cancelar</button>
            <button onClick={salvar} disabled={saving || !form.item_type_id || !form.quantidade} className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50">
              {saving ? 'Salvando...' : 'Registrar'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
