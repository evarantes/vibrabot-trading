interface StatCardProps {
  title: string
  value: number | string
  subtitle?: string
  icon: React.ReactNode
  color?: 'indigo' | 'emerald' | 'amber' | 'rose' | 'blue' | 'violet'
  trend?: { value: number; label: string }
}

const colorMap = {
  indigo: 'bg-indigo-600/20 text-indigo-400 border-indigo-600/20',
  emerald: 'bg-emerald-600/20 text-emerald-400 border-emerald-600/20',
  amber: 'bg-amber-600/20 text-amber-400 border-amber-600/20',
  rose: 'bg-rose-600/20 text-rose-400 border-rose-600/20',
  blue: 'bg-blue-600/20 text-blue-400 border-blue-600/20',
  violet: 'bg-violet-600/20 text-violet-400 border-violet-600/20',
}

export default function StatCard({ title, value, subtitle, icon, color = 'indigo', trend }: StatCardProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col gap-3 hover:border-slate-700 transition-colors">
      <div className="flex items-start justify-between">
        <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${colorMap[color]}`}>
          {icon}
        </div>
        {trend && (
          <span className={`text-xs font-medium px-2 py-1 rounded-lg ${
            trend.value > 0 ? 'bg-rose-500/10 text-rose-400' : 'bg-emerald-500/10 text-emerald-400'
          }`}>
            {trend.value > 0 ? '▲' : '▼'} {Math.abs(trend.value)}%
          </span>
        )}
      </div>
      <div>
        <div className="text-2xl font-bold text-white">{value}</div>
        <div className="text-sm text-slate-400 mt-0.5">{title}</div>
        {subtitle && <div className="text-xs text-slate-600 mt-1">{subtitle}</div>}
      </div>
    </div>
  )
}
