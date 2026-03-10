import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ShoppingCart, Package, WashingMachine, BedDouble,
  AlertTriangle, TrendingDown, ClipboardList, ArrowRight
} from 'lucide-react'
import { dashboardApi, type DashboardStats } from '../api'
import StatCard from '../components/StatCard'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts'

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444']

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dashboardApi.stats().then(r => setStats(r.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  if (!stats) return null

  const pieData = [
    { name: 'Estoque', value: stats.total_estoque },
    { name: 'Lavanderia', value: stats.total_na_lavanderia },
    { name: 'Em Uso', value: stats.total_em_uso },
    { name: 'Desfalque', value: stats.total_desfalque },
  ].filter(d => d.value > 0)

  const barData = stats.ultimas_auditorias.slice(0, 5).reverse().map(a => ({
    name: format(new Date(a.created_at), 'dd/MM', { locale: ptBR }),
    Comprado: a.total_comprado || 0,
    Contabilizado: (a.total_estoque || 0) + (a.total_lavanderia || 0) + (a.total_em_uso || 0),
    Desfalque: a.total_desfalque || 0,
  }))

  return (
    <div className="space-y-6">
      {/* Alertas */}
      {stats.alertas.length > 0 && (
        <div className="space-y-2">
          {stats.alertas.map((alerta, i) => (
            <div key={i} className="bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3 flex items-center gap-3">
              <AlertTriangle size={16} className="text-amber-400 flex-shrink-0" />
              <span className="text-sm text-amber-300">{alerta}</span>
            </div>
          ))}
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Comprado"
          value={stats.total_comprado.toLocaleString()}
          subtitle="peças adquiridas"
          icon={<ShoppingCart size={20} />}
          color="indigo"
        />
        <StatCard
          title="Em Estoque"
          value={stats.total_estoque.toLocaleString()}
          subtitle="peças disponíveis"
          icon={<Package size={20} />}
          color="emerald"
        />
        <StatCard
          title="Na Lavanderia"
          value={stats.total_na_lavanderia.toLocaleString()}
          subtitle="peças enviadas"
          icon={<WashingMachine size={20} />}
          color="blue"
        />
        <StatCard
          title="Em Uso"
          value={stats.total_em_uso.toLocaleString()}
          subtitle="peças nos quartos"
          icon={<BedDouble size={20} />}
          color="violet"
        />
      </div>

      {/* Desfalque em destaque */}
      <div className={`rounded-2xl border p-5 flex items-center gap-5 ${
        stats.total_desfalque === 0
          ? 'bg-emerald-900/20 border-emerald-800/30'
          : stats.percentual_desfalque > 10
          ? 'bg-rose-900/20 border-rose-800/30'
          : 'bg-amber-900/20 border-amber-800/30'
      }`}>
        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0 ${
          stats.total_desfalque === 0 ? 'bg-emerald-600/20' : 'bg-rose-600/20'
        }`}>
          <TrendingDown size={28} className={stats.total_desfalque === 0 ? 'text-emerald-400' : 'text-rose-400'} />
        </div>
        <div className="flex-1">
          <div className="text-3xl font-bold text-white">{stats.total_desfalque.toLocaleString()} peças</div>
          <div className="text-slate-400 text-sm mt-1">
            Desfalque total detectado — <span className={`font-semibold ${
              stats.total_desfalque === 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}>{stats.percentual_desfalque}% do total comprado</span>
          </div>
        </div>
        <Link
          to="/auditoria"
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
        >
          Auditar <ArrowRight size={16} />
        </Link>
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Distribuição */}
        {pieData.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <h3 className="font-semibold text-white mb-4">Distribuição do Enxoval</h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }: { name?: string; percent?: number }) => `${name || ''} ${((percent || 0) * 100).toFixed(0)}%`}>
                  {pieData.map((_, idx) => <Cell key={idx} fill={COLORS[idx % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => [`${v} peças`]} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Histórico de auditorias */}
        {barData.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <h3 className="font-semibold text-white mb-4">Histórico de Auditorias</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 12 }}
                  labelStyle={{ color: '#fff' }}
                />
                <Legend />
                <Bar dataKey="Comprado" fill="#6366f1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Contabilizado" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Desfalque" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Últimas auditorias */}
      {stats.ultimas_auditorias.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl">
          <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <ClipboardList size={18} className="text-indigo-400" />
              Últimas Auditorias
            </h3>
            <Link to="/auditoria" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
              Ver todas <ArrowRight size={12} />
            </Link>
          </div>
          <div className="divide-y divide-slate-800">
            {stats.ultimas_auditorias.map(a => (
              <div key={a.id} className="px-5 py-3.5 flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate">{a.titulo}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {format(new Date(a.created_at), "dd 'de' MMMM 'de' yyyy", { locale: ptBR })}
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className={`text-sm font-semibold ${(a.total_desfalque || 0) > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {(a.total_desfalque || 0) > 0 ? `-${a.total_desfalque}` : '✓'} peças
                  </div>
                  <div className="text-xs text-slate-500">{a.total_comprado} compradas</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick start */}
      {stats.total_comprado === 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center">
          <div className="text-4xl mb-3">🏨</div>
          <h3 className="text-white font-semibold text-lg mb-2">Bem-vindo ao CodexiaAuditor!</h3>
          <p className="text-slate-400 text-sm mb-5 max-w-md mx-auto">
            Para começar, cadastre os tipos de enxoval do seu hotel e registre as compras realizadas.
          </p>
          <div className="flex flex-wrap gap-3 justify-center">
            <Link to="/itens" className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors">
              Cadastrar Enxoval
            </Link>
            <Link to="/compras" className="bg-slate-800 hover:bg-slate-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors">
              Registrar Compras
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
