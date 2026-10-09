import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import VerificationPage from './VerificationPage.jsx'
import AdminPage from './AdminPage.jsx'
import ValidadorPage from './ValidadorPage.jsx'
import ValidadorHomePage from './ValidadorHomePage.jsx'
import LoginPage from './LoginPage.jsx'

const path = window.location.pathname.toLowerCase()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {path === '/validador' || path === '/validador/'
      ? <ValidadorHomePage />
      : path.startsWith('/validador/')
      ? <ValidadorPage />
      : path.startsWith('/login')
        ? <LoginPage />
      : path.startsWith('/verificar/')
        ? <VerificationPage />
        : path.startsWith('/administracao')
          ? <AdminPage />
          : <App />}
  </StrictMode>,
)
