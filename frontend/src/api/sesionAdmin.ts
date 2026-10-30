const CLAVE = 'chatbot-admin-pestana'
let tokenMemoria = ''

export function tokenAdmin(): string {
  try { return sessionStorage.getItem(CLAVE) || tokenMemoria }
  catch { return tokenMemoria }
}

export function guardarTokenAdmin(token: string): void {
  tokenMemoria = token
  try {
    if (token) sessionStorage.setItem(CLAVE, token)
    else sessionStorage.removeItem(CLAVE)
  } catch { /* Sin almacenamiento, el acceso dura solo en esta página. */ }
}
