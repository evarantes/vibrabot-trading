interface BadgeProps {
  children: React.ReactNode
  variant?: 'indigo' | 'emerald' | 'amber' | 'rose' | 'slate' | 'blue'
}

const variants = {
  indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
  emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  rose: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
  slate: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
  blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
}

export default function Badge({ children, variant = 'slate' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-lg border text-xs font-medium ${variants[variant]}`}>
      {children}
    </span>
  )
}

export function statusBadge(status: string) {
  const map: Record<string, { label: string; variant: BadgeProps['variant'] }> = {
    pendente: { label: 'Pendente', variant: 'amber' },
    parcial: { label: 'Parcial', variant: 'blue' },
    completo: { label: 'Completo', variant: 'emerald' },
    entrada: { label: 'Entrada', variant: 'emerald' },
    saida: { label: 'Saída', variant: 'rose' },
    ajuste: { label: 'Ajuste', variant: 'blue' },
    perda: { label: 'Perda', variant: 'rose' },
    descarte: { label: 'Descarte', variant: 'slate' },
  }
  const config = map[status] || { label: status, variant: 'slate' as const }
  return <Badge variant={config.variant}>{config.label}</Badge>
}
