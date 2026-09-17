import { Navigate, Route, Routes } from 'react-router-dom'
import ChatbotPage from './pages/ChatbotPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/chat" replace />} />
      <Route path="/chat" element={<ChatbotPage />} />
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  )
}

export default App
