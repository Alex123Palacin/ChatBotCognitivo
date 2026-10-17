import { Navigate, Outlet, Route, Routes, useLocation, useParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import ChatbotPage from '../pages/ChatbotPage'
import LoginPage from '../pages/LoginPage'
import RegistroPage from '../pages/RegistroPage'
import AdminPage from '../pages/admin/AdminPage'
import AlumnoPage from '../pages/admin/AlumnoPage'
import ReporteAlumnoPage from '../pages/admin/ReporteAlumnoPage'
import LoginAdminPage from '../pages/admin/LoginAdminPage'

function RutaProtegida({ admin = false }: { admin?: boolean }) {
  const { usuario } = useAuth()
  if (!usuario) return <Navigate to={admin ? '/administrador' : '/login'} replace />
  if (admin && !usuario.es_admin) return <Navigate to="/chat" replace />
  if (!admin && usuario.es_admin) return <Navigate to="/administrador" replace />
  return <Outlet />
}

function RutaPublica() {
  const { usuario } = useAuth()
  return usuario ? <Navigate to={usuario.es_admin ? '/administrador' : '/chat'} replace /> : <Outlet />
}

function EntradaAdministrador() {
  const { usuario } = useAuth()
  if (!usuario) return <LoginAdminPage />
  return usuario.es_admin ? <AdminPage /> : <Navigate to="/chat" replace />
}

function RutaAdminAntigua() {
  const { pathname, search, hash } = useLocation()
  return <Navigate to={{ pathname: pathname.replace(/^\/admin(?=\/|$)/i, '/administrador'), search, hash }} replace />
}

function RutaReportesAlumno() {
  const { id } = useParams()
  return <Navigate to={`/administrador/alumnos/${id}`} replace />
}

function AppRoutes() {
  const { usuario, cargando } = useAuth()
  if (cargando) return <div role="status" className="flex min-h-dvh items-center justify-center bg-slate-50 text-sm text-slate-500">Comprobando tu sesión…</div>
  return (
    <Routes key={usuario?.id ?? 'publico'}>
      <Route element={<RutaPublica />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/registro" element={<RegistroPage />} />
      </Route>
      <Route element={<RutaProtegida />}><Route path="/chat" element={<ChatbotPage />} /></Route>
      <Route path="/administrador" element={<EntradaAdministrador />} />
      <Route element={<RutaProtegida admin />}>
        <Route path="/administrador/alumnos" element={<AdminPage />} />
        <Route path="/administrador/alumnos/:id" element={<AlumnoPage />} />
        <Route path="/administrador/alumnos/:id/reportes" element={<RutaReportesAlumno />} />
        <Route path="/administrador/reportes/:id" element={<ReporteAlumnoPage />} />
      </Route>
      <Route path="/admin/*" element={<RutaAdminAntigua />} />
      <Route path="*" element={<Navigate to={usuario ? usuario.es_admin ? '/administrador' : '/chat' : '/login'} replace />} />
    </Routes>
  )
}

export default AppRoutes
