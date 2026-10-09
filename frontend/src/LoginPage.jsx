import { useMemo, useState } from 'react'
import { loginWithEmailPassword } from './firebaseAuth'
import { hasTiPermission } from './permissions'

export default function LoginPage() {
  const params = useMemo(() => new URLSearchParams(window.location.search), [])
  const nextPath = params.get('next') || '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      const user = await loginWithEmailPassword(email, password)
      const isTi = await hasTiPermission(user)

      if (nextPath && nextPath !== '/') {
        window.location.replace(nextPath)
        return
      }

      window.location.replace(isTi ? '/' : '/validador')
    } catch (err) {
      setError(err.message || 'Falha no login. Confira email e senha.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <section className="w-full max-w-md border border-slate-700 bg-slate-900 p-6 rounded-xl">
        <p className="text-xs uppercase tracking-[0.2em] text-teal-300">Macroambiental</p>
        <h1 className="text-2xl font-semibold mt-2">Login do Validador</h1>
        <p className="text-sm text-slate-400 mt-2">A sessao fica ativa por 30 dias neste dispositivo.</p>

        <form onSubmit={handleSubmit} className="space-y-4 mt-6">
          <div>
            <label className="text-sm text-slate-300 block mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full border border-slate-600 bg-slate-950 rounded-md p-3"
              placeholder="email@empresa.com"
              autoComplete="email"
              required
            />
          </div>

          <div>
            <label className="text-sm text-slate-300 block mb-2">Senha</label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full border border-slate-600 bg-slate-950 rounded-md p-3"
              placeholder="******"
              autoComplete="current-password"
              required
            />
          </div>

          {error ? <p role="alert" className="text-sm text-rose-300">{error}</p> : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-teal-500 text-slate-950 py-3 font-semibold disabled:opacity-50"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </section>
    </main>
  )
}
