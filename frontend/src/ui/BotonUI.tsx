import type { ButtonHTMLAttributes } from 'react'

function BotonUI({ className = '', children, type = 'button', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-linear-to-r from-blue-600 to-indigo-500 px-4 py-3 text-sm font-semibold text-white shadow-sm shadow-blue-200 transition hover:brightness-105 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-40 motion-reduce:transition-none ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export default BotonUI
