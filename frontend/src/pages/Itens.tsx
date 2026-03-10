import { useEffect, useState } from 'react'
import { Plus, Package, Pencil, Trash2 } from 'lucide-react'
import { itemsApi, type ItemType } from '../api'
import Modal from '../components/Modal'
import { FormField, Input, Select, TextArea } from '../components/FormField'
import Badge from '../components/Badge'
import EmptyState from '../components/EmptyState'

const categorias = ['cama', 'banho', 'mesa', 'outros']

const catColor: Record<string, 'indigo' | 'blue' | 'amber' | 'slate'> = {
  cama: 'indigo',
  banho: 'blue',
  mesa: 'amber',
  outros: 'slate',
}

const itensDefault = [
  { nome: 'Lençol Solteiro', categoria: 'cama', descricao: 'Lençol para cama solteiro' },
  { nome: 'Lençol Casal', categoria: 'cama', descricao: 'Lençol para cama casal' },
  { nome: 'Fronha', categoria: 'cama', descricao: 'Fronha para travesseiro' },
  { nome: 'Cobertor', categoria: 'cama', descricao: 'Cobertor para cama' },
  { nome: 'Toalha de Banho', categoria: 'banho', descricao: 'Toalha grande de banho' },
  { nome: 'Toalha de Rosto', categoria: 'banho', descricao: 'Toalha de rosto' },
  { nome: 'Toalha de Pés', categoria: 'banho', descricao: 'Tapete/toalha para pés' },
  { nome: 'Roupão', categoria: 'banho', descricao: 'Roupão de banho' },
  { nome: 'Guardanapo', categoria: 'mesa', descricao: 'Guardanapo para mesa' },
  { nome: 'Toalha de Mesa', categoria: 'mesa', descricao: 'Toalha para mesa de jantar' },
]

export default function Itens() {
  const [itens, setItens] = useState<ItemType[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editItem, setEditItem] = useState<ItemType | null>(null)
  const [form, setForm] = useState({ nome: '', categoria: 'cama', descricao: '' })
  const [saving, setSaving] = useState(false)

  const carregar = () => {
    itemsApi.list().then(r => setItens(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { carregar() }, [])

  const abrirModal = (item?: ItemType) => {
    if (item) {
      setEditItem(item)
      setForm({ nome: item.nome, categoria: item.categoria, descricao: item.descricao || '' })
    } else {
      setEditItem(null)
      setForm({ nome: '', categoria: 'cama', descricao: '' })
    }
    setModalOpen(true)
  }

  const salvar = async () => {
    if (!form.nome.trim()) return
    setSaving(true)
    try {
      if (editItem) {
        await itemsApi.update(editItem.id, form)
      } else {
        await itemsApi.create(form)
      }
      setModalOpen(false)
      carregar()
    } finally {
      setSaving(false)
    }
  }

  const deletar = async (id: number) => {
    if (!confirm('Deseja remover este item?')) return
    await itemsApi.delete(id)
    carregar()
  }

  const popularItensDefault = async () => {
    if (!confirm(`Deseja cadastrar ${itensDefault.length} tipos de enxoval padrão?`)) return
    setSaving(true)
    for (const item of itensDefault) {
      try { await itemsApi.create(item) } catch {}
    }
    setSaving(false)
    carregar()
  }

  const grupos = categorias.reduce<Record<string, ItemType[]>>((acc, cat) => {
    acc[cat] = itens.filter(i => i.categoria === cat)
    return acc
  }, {})

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Tipos de Enxoval</h2>
          <p className="text-sm text-slate-500">{itens.length} tipo(s) cadastrado(s)</p>
        </div>
        <div className="flex gap-2">
          {itens.length === 0 && (
            <button
              onClick={popularItensDefault}
              disabled={saving}
              className="text-sm text-slate-300 hover:text-white border border-slate-700 hover:border-slate-600 px-3 py-2 rounded-xl transition-colors"
            >
              Usar padrão
            </button>
          )}
          <button
            onClick={() => abrirModal()}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
          >
            <Plus size={16} /> Novo Item
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : itens.length === 0 ? (
        <EmptyState
          icon={<Package size={32} />}
          title="Nenhum tipo de enxoval cadastrado"
          description="Cadastre os tipos de enxoval do seu hotel para começar a auditoria."
          action={
            <div className="flex gap-2">
              <button onClick={popularItensDefault} className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors">
                Usar padrão
              </button>
              <button onClick={() => abrirModal()} className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors">
                Cadastrar manualmente
              </button>
            </div>
          }
        />
      ) : (
        <div className="space-y-4">
          {categorias.map(cat => grupos[cat]?.length > 0 && (
            <div key={cat} className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-800 flex items-center gap-2">
                <Badge variant={catColor[cat]}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</Badge>
                <span className="text-xs text-slate-600">{grupos[cat].length} item(ns)</span>
              </div>
              <div className="divide-y divide-slate-800">
                {grupos[cat].map(item => (
                  <div key={item.id} className="px-5 py-3 flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-white">{item.nome}</div>
                      {item.descricao && <div className="text-xs text-slate-500 mt-0.5 truncate">{item.descricao}</div>}
                    </div>
                    <div className="flex items-center gap-1">
                      <button onClick={() => abrirModal(item)} className="p-2 text-slate-500 hover:text-indigo-400 hover:bg-slate-800 rounded-lg transition-colors">
                        <Pencil size={15} />
                      </button>
                      <button onClick={() => deletar(item.id)} className="p-2 text-slate-500 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors">
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editItem ? 'Editar Item' : 'Novo Tipo de Enxoval'}>
        <div className="space-y-4">
          <FormField label="Nome" required>
            <Input
              value={form.nome}
              onChange={e => setForm(f => ({ ...f, nome: e.target.value }))}
              placeholder="Ex: Toalha de Banho"
            />
          </FormField>
          <FormField label="Categoria" required>
            <Select value={form.categoria} onChange={e => setForm(f => ({ ...f, categoria: e.target.value }))}>
              {categorias.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
            </Select>
          </FormField>
          <FormField label="Descrição">
            <TextArea
              value={form.descricao}
              onChange={e => setForm(f => ({ ...f, descricao: e.target.value }))}
              placeholder="Descrição opcional..."
              rows={3}
            />
          </FormField>
          <div className="flex gap-3 pt-2">
            <button onClick={() => setModalOpen(false)} className="flex-1 px-4 py-2.5 border border-slate-700 text-slate-300 rounded-xl text-sm hover:bg-slate-800 transition-colors">
              Cancelar
            </button>
            <button
              onClick={salvar}
              disabled={saving || !form.nome.trim()}
              className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
            >
              {saving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
