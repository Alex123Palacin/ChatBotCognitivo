import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  etiqueta: string
}

function InputUI({ etiqueta, id, className = '', ...props }: InputProps) {
  return (
    <label htmlFor={id} className="block text-sm font-medium text-slate-700">
      {etiqueta}
      <input
        id={id}
        className={`mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 font-normal text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-3 focus:ring-blue-100 disabled:bg-slate-50 ${className}`}
        {...props}
      />
    </label>
  )
}

export default InputUI
