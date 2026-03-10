interface FormFieldProps {
  label: string
  required?: boolean
  children: React.ReactNode
  hint?: string
}

export function FormField({ label, required, children, hint }: FormFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-slate-300">
        {label}{required && <span className="text-rose-400 ml-1">*</span>}
      </label>
      {children}
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}
export function Input(props: InputProps) {
  return (
    <input
      {...props}
      className={`bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white
        placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30
        transition-all w-full ${props.className || ''}`}
    />
  )
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  children: React.ReactNode
}
export function Select({ children, ...props }: SelectProps) {
  return (
    <select
      {...props}
      className={`bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white
        focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30
        transition-all w-full ${props.className || ''}`}
    >
      {children}
    </select>
  )
}

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}
export function TextArea(props: TextAreaProps) {
  return (
    <textarea
      {...props}
      className={`bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white
        placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30
        transition-all w-full resize-none ${props.className || ''}`}
    />
  )
}
