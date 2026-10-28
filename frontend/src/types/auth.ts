export interface Usuario {
  id: number
  email: string
  nombre: string
  username?: string
  es_admin: boolean
  terminos_aceptados?: boolean
  retencion_dias?: 30 | null
  version_terminos?: string | null
}

export interface RespuestaAuth {
  usuario: Usuario
}

export interface TerminosRegistro {
  version: string
  dias_retencion: number
  texto: string
  alcance: 'mensajes_nuevos'
  copias_seguridad: 'gestion_separada'
}

export interface AceptacionTerminos {
  acepta_terminos: boolean
  version_terminos: string
}
