import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import VerificationPage from './VerificationPage.jsx'
import AdminPage from './AdminPage.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {window.location.pathname.startsWith('/verificar/') ? <VerificationPage /> : window.location.pathname.startsWith('/administracao') ? <AdminPage /> : <App />}
  </StrictMode>,
)
