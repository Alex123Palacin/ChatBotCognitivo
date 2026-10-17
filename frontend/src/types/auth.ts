export interface Usuario {
  id: number
  email: string
  nombre: string
  username?: string
  es_admin: boolean
}

export interface RespuestaAuth {
  usuario: Usuario
}
