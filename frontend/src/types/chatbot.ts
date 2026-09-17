export interface MensajeChat {
  id: string
  contenido: string
  remitente: 'usuario' | 'asistente'
  fecha: Date
}
