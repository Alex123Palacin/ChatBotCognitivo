import type { ButtonHTMLAttributes } from 'react'

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  etiqueta: string
}

function IconButtonUI({ etiqueta, className = '', children, type = 'button', ...props }: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={etiqueta}
      title={etiqueta}
      className={`inline-flex size-11 shrink-0 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-40 motion-reduce:transition-none ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export default IconButtonUI
