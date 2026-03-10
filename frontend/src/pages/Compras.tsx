import { useEffect, useState } from 'react'
import { Plus, ShoppingCart, Trash2 } from 'lucide-react'
import { purchasesApi, itemsApi, type Purchase, type ItemType } from '../api'
import Modal from '../components/Modal'
import { FormField, Input, Select, TextArea } from '../components/FormField'
import EmptyState from '../components/EmptyState'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export default function Compras() {
  const [compras, setCompras] = useState<Purchase[]>([])
  const [itens, setItens] = useState<ItemType[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    item_type_id: '',
    quantidade: '',
    fornecedor: '',
    valor_unitario: '',
    nota_fiscal: '',
    observacoes: '',
    data_compra: new Date().toISOString().slice(0, 16),
  })

  const carregar = () => {
    Promise.all([
      purchasesApi.list(),
      itemsApi.list(),
    ]).then(([c, i]) => {
      setCompras(c.data)
      setItens(i.data)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { carregar() }, [])

  const salvar = async () => {
    if (!form.item_type_id || !form.quantidade || !form.data_compra) return
    setSaving(true)
    try {
      await purchasesApi.create({
        item_type_id: Number(form.item_type_id),
        quantidade: Number(form.quantidade),
        fornecedor: form.fornecedor || undefined,
        valor_unitario: form.valor_unitario ? Number(form.valor_unitario) : undefined,
        nota_fiscal: form.nota_fiscal || undefined,
        observacoes: form.observacoes || undefined,
        data_compra: new Date(form.data_compra).toISOString(),
      })
      setModalOpen(false)
      setForm({ item_type_id: '', quantidade: '', fornecedor: '', valor_unitario: '', nota_fiscal: '', observacoes: '', data_compra: new Date().toISOString().slice(0, 16) })
      carregar()
    } finally {
      setSaving(false)
    }
  }

  const deletar = async (id: number) => {
    if (!confirm('Remover esta compra?')) return
    await purchasesApi.delete(id)
    carregar()
  }

  const totalComprado = compras.reduce((s, c) => s + c.quantidade, 0)
  const totalValor = compras.reduce((s, c) => s + ((c.valor_unitario || 0) * c.quantidade), 0)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Registro de Compras</h2>
          <p className="text-sm text-slate-500">{compras.length} compra(s) — {totalComprado.toLocaleString()} peças no total</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
        >
          <Plus size={16} /> Nova Compra
        </button>
      </div>

      {/* Resumo */}
      {compras.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
            <div className="text-2xl font-bold text-white">{totalComprado.toLocaleString()}</div>
            <div className="text-sm text-slate-400">Peças Compradas</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
            <div className="text-2xl font-bold text-white">{compras.length}</div>
            <div className="text-sm text-slate-400">Ordens de Compra</div>
          </div>
          {totalValor > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
              <div className="text-2xl font-bold text-white">
                {totalValor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </div>
              <div className="text-sm text-slate-400">Valor Total</div>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : compras.length === 0 ? (
        <EmptyState
          icon={<ShoppingCart size={32} />}
          title="Nenhuma compra registrada"
          description="Registre as compras de enxoval realizadas para iniciar o controle."
          action={
            <button onClick={() => setModalOpen(true)} className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors">
              Registrar Compra
            </button>
          }
        />
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-800 text-left">
                  <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase">Item</th>
                  <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase">Qtd</th>
                  <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase hidden sm:table-cell">Fornecedor</th>
                  <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase hidden md:table-cell">NF</th>
                  <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase hidden lg:table-cell">Valor Unit.</th>
                  <th className="px-5 py-3 text-xs font-medium text-slate-500 uppercase">Data</th>
                  <th className="px-2 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {compras.map(c => (
                  <tr key={c.id} className="hover:bg-slate-800/50 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="text-sm font-medium text-white">{c.item_type?.nome}</div>
                      <div className="text-xs text-slate-500">{c.item_type?.categoria}</div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="text-sm font-semibold text-indigo-400">{c.quantidade}</span>
                    </td>
                    <td className="px-5 py-3.5 hidden sm:table-cell text-sm text-slate-400">{c.fornecedor || '—'}</td>
                    <td className="px-5 py-3.5 hidden md:table-cell text-sm text-slate-400">{c.nota_fiscal || '—'}</td>
                    <td className="px-5 py-3.5 hidden lg:table-cell text-sm text-slate-400">
                      {c.valor_unitario ? c.valor_unitario.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '—'}
                    </td>
                    <td className="px-5 py-3.5 text-sm text-slate-400 whitespace-nowrap">
                      {format(new Date(c.data_compra), 'dd/MM/yyyy', { locale: ptBR })}
                    </td>
                    <td className="px-2 py-3.5">
                      <button onClick={() => deletar(c.id)} className="p-2 text-slate-600 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors">
                        <Trash2 size={15} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Registrar Compra">
        <div className="space-y-4">
          <FormField label="Tipo de Enxoval" required>
            <Select value={form.item_type_id} onChange={e => setForm(f => ({ ...f, item_type_id: e.target.value }))}>
              <option value="">Selecione...</option>
              {itens.map(i => <option key={i.id} value={i.id}>{i.nome}</option>)}
            </Select>
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Quantidade" required>
              <Input type="number" min="1" value={form.quantidade} onChange={e => setForm(f => ({ ...f, quantidade: e.target.value }))} placeholder="0" />
            </FormField>
            <FormField label="Valor Unitário (R$)">
              <Input type="number" step="0.01" min="0" value={form.valor_unitario} onChange={e => setForm(f => ({ ...f, valor_unitario: e.target.value }))} placeholder="0,00" />
            </FormField>
          </div>
          <FormField label="Fornecedor">
            <Input value={form.fornecedor} onChange={e => setForm(f => ({ ...f, fornecedor: e.target.value }))} placeholder="Nome do fornecedor" />
          </FormField>
          <FormField label="Nota Fiscal">
            <Input value={form.nota_fiscal} onChange={e => setForm(f => ({ ...f, nota_fiscal: e.target.value }))} placeholder="Número da NF" />
          </FormField>
          <FormField label="Data da Compra" required>
            <Input type="datetime-local" value={form.data_compra} onChange={e => setForm(f => ({ ...f, data_compra: e.target.value }))} />
          </FormField>
          <FormField label="Observações">
            <TextArea value={form.observacoes} onChange={e => setForm(f => ({ ...f, observacoes: e.target.value }))} placeholder="Observações..." rows={2} />
          </FormField>
          <div className="flex gap-3 pt-2">
            <button onClick={() => setModalOpen(false)} className="flex-1 px-4 py-2.5 border border-slate-700 text-slate-300 rounded-xl text-sm hover:bg-slate-800 transition-colors">
              Cancelar
            </button>
            <button onClick={salvar} disabled={saving || !form.item_type_id || !form.quantidade} className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50">
              {saving ? 'Salvando...' : 'Registrar'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
