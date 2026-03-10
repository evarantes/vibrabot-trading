import { useEffect, useState } from 'react'
import { Plus, BedDouble, LogOut, Trash2 } from 'lucide-react'
import { roomsApi, itemsApi, type RoomAssignment, type ItemType } from '../api'
import Modal from '../components/Modal'
import { FormField, Input, Select, TextArea } from '../components/FormField'
import EmptyState from '../components/EmptyState'
import Badge from '../components/Badge'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export default function Quartos() {
  const [atribuicoes, setAtribuicoes] = useState<RoomAssignment[]>([])
  const [itens, setItens] = useState<ItemType[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [filtroAtivo, setFiltroAtivo] = useState<1 | 0 | null>(1)
  const [quartoFiltro, setQuartoFiltro] = useState('')
  const [form, setForm] = useState({
    item_type_id: '',
    numero_quarto: '',
    andar: '',
    quantidade: '',
    observacoes: '',
    data_atribuicao: new Date().toISOString().slice(0, 16),
  })

  const carregar = () => {
    Promise.all([roomsApi.list(), itemsApi.list()])
      .then(([a, i]) => { setAtribuicoes(a.data); setItens(i.data) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { carregar() }, [])

  const salvar = async () => {
    if (!form.item_type_id || !form.numero_quarto || !form.quantidade) return
    setSaving(true)
    try {
      await roomsApi.create({
        item_type_id: Number(form.item_type_id),
        numero_quarto: form.numero_quarto,
        andar: form.andar || undefined,
        quantidade: Number(form.quantidade),
        observacoes: form.observacoes || undefined,
        data_atribuicao: new Date(form.data_atribuicao).toISOString(),
        ativo: 1,
      })
      setModalOpen(false)
      setForm({ item_type_id: '', numero_quarto: '', andar: '', quantidade: '', observacoes: '', data_atribuicao: new Date().toISOString().slice(0, 16) })
      carregar()
    } finally { setSaving(false) }
  }

  const retirar = async (a: RoomAssignment) => {
    if (!confirm(`Retirar ${a.quantidade} ${a.item_type?.nome} do quarto ${a.numero_quarto}?`)) return
    await roomsApi.retirar(a.id, { data_retirada: new Date().toISOString() })
    carregar()
  }

  const deletar = async (id: number) => {
    if (!confirm('Remover este registro?')) return
    await roomsApi.delete(id)
    carregar()
  }

  const filtrados = atribuicoes.filter(a => {
    if (filtroAtivo !== null && a.ativo !== filtroAtivo) return false
    if (quartoFiltro && !a.numero_quarto.toLowerCase().includes(quartoFiltro.toLowerCase())) return false
    return true
  })

  const emUso = atribuicoes.filter(a => a.ativo === 1)
  const totalEmUso = emUso.reduce((s, a) => s + a.quantidade, 0)
  const quartosAtivos = new Set(emUso.map(a => a.numero_quarto)).size

  // Agrupar por quarto
  const porQuarto = filtrados.reduce<Record<string, RoomAssignment[]>>((acc, a) => {
    if (!acc[a.numero_quarto]) acc[a.numero_quarto] = []
    acc[a.numero_quarto].push(a)
    return acc
  }, {})

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Enxoval nos Quartos</h2>
          <p className="text-sm text-slate-500">{quartosAtivos} quartos ativos — {totalEmUso} peças em uso</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors">
          <Plus size={16} /> Atribuir Enxoval
        </button>
      </div>

      {/* Filtros */}
      <div className="flex gap-3 flex-wrap items-center">
        <div className="flex bg-slate-900 border border-slate-800 rounded-xl p-1 gap-1">
          {[{ v: 1, l: 'Em Uso' }, { v: 0, l: 'Retirados' }, { v: null, l: 'Todos' }].map(opt => (
            <button
              key={String(opt.v)}
              onClick={() => setFiltroAtivo(opt.v as any)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filtroAtivo === opt.v ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              {opt.l}
            </button>
          ))}
        </div>
        <input
          value={quartoFiltro}
          onChange={e => setQuartoFiltro(e.target.value)}
          placeholder="Filtrar quarto..."
          className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 w-36"
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : Object.keys(porQuarto).length === 0 ? (
        <EmptyState
          icon={<BedDouble size={32} />}
          title="Nenhum enxoval atribuído"
          description="Registre os itens de enxoval distribuídos para os quartos do hotel."
          action={<button onClick={() => setModalOpen(true)} className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors">Atribuir Enxoval</button>}
        />
      ) : (
        <div className="space-y-3">
          {Object.entries(porQuarto).sort(([a], [b]) => a.localeCompare(b)).map(([quarto, lista]) => {
            const totalQuarto = lista.filter(a => a.ativo === 1).reduce((s, a) => s + a.quantidade, 0)
            const andar = lista[0]?.andar
            return (
              <div key={quarto} className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-800 flex items-center gap-3">
                  <BedDouble size={16} className="text-indigo-400" />
                  <span className="font-semibold text-white">Quarto {quarto}</span>
                  {andar && <Badge variant="slate">Andar {andar}</Badge>}
                  <span className="ml-auto text-xs text-slate-500">{totalQuarto} peças em uso</span>
                </div>
                <div className="divide-y divide-slate-800">
                  {lista.map(a => (
                    <div key={a.id} className="px-5 py-3 flex items-center gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-white">{a.item_type?.nome}</span>
                          <Badge variant={a.ativo === 1 ? 'emerald' : 'slate'}>{a.ativo === 1 ? 'Em Uso' : 'Retirado'}</Badge>
                        </div>
                        <div className="text-xs text-slate-500 mt-0.5">
                          Qtd: {a.quantidade} · {format(new Date(a.data_atribuicao), 'dd/MM/yyyy', { locale: ptBR })}
                          {a.data_retirada && ` → ${format(new Date(a.data_retirada), 'dd/MM/yyyy', { locale: ptBR })}`}
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        {a.ativo === 1 && (
                          <button onClick={() => retirar(a)} className="flex items-center gap-1.5 px-2.5 py-1.5 bg-amber-600/10 text-amber-400 border border-amber-600/20 rounded-lg text-xs hover:bg-amber-600/20 transition-colors">
                            <LogOut size={13} /> Retirar
                          </button>
                        )}
                        <button onClick={() => deletar(a.id)} className="p-2 text-slate-600 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Atribuir Enxoval ao Quarto">
        <div className="space-y-4">
          <FormField label="Tipo de Enxoval" required>
            <Select value={form.item_type_id} onChange={e => setForm(f => ({ ...f, item_type_id: e.target.value }))}>
              <option value="">Selecione...</option>
              {itens.map(i => <option key={i.id} value={i.id}>{i.nome}</option>)}
            </Select>
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Número do Quarto" required>
              <Input value={form.numero_quarto} onChange={e => setForm(f => ({ ...f, numero_quarto: e.target.value }))} placeholder="Ex: 101" />
            </FormField>
            <FormField label="Andar">
              <Input value={form.andar} onChange={e => setForm(f => ({ ...f, andar: e.target.value }))} placeholder="Ex: 1" />
            </FormField>
          </div>
          <FormField label="Quantidade" required>
            <Input type="number" min="1" value={form.quantidade} onChange={e => setForm(f => ({ ...f, quantidade: e.target.value }))} placeholder="0" />
          </FormField>
          <FormField label="Data de Atribuição" required>
            <Input type="datetime-local" value={form.data_atribuicao} onChange={e => setForm(f => ({ ...f, data_atribuicao: e.target.value }))} />
          </FormField>
          <FormField label="Observações">
            <TextArea value={form.observacoes} onChange={e => setForm(f => ({ ...f, observacoes: e.target.value }))} placeholder="Observações..." rows={2} />
          </FormField>
          <div className="flex gap-3 pt-2">
            <button onClick={() => setModalOpen(false)} className="flex-1 px-4 py-2.5 border border-slate-700 text-slate-300 rounded-xl text-sm hover:bg-slate-800 transition-colors">Cancelar</button>
            <button onClick={salvar} disabled={saving || !form.item_type_id || !form.numero_quarto || !form.quantidade} className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50">
              {saving ? 'Salvando...' : 'Atribuir'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
