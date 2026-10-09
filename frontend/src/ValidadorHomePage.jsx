import { useEffect, useState } from 'react'
import { logoutFirebase, subscribeAuth } from './firebaseAuth'

export default function ValidadorHomePage() {
  const [viewer, setViewer] = useState(null)

  useEffect(() => {
    const unsubscribe = subscribeAuth((state) => {
      if (state.type === 'signed-in') {
        setViewer(state.user)
        return
      }
      window.location.replace(`/login?next=${encodeURIComponent('/validador')}`)
    })

    return () => unsubscribe()
  }, [])

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <section className="w-full max-w-2xl border border-slate-700 bg-slate-900 rounded-xl p-6">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-teal-300">Macroambiental</p>
            <h1 className="text-2xl font-semibold mt-2">Validador de documentos</h1>
            <p className="text-slate-300 mt-2">Escaneie o QR Code de um documento para abrir a validacao automaticamente.</p>
          </div>
          <button
            type="button"
            className="rounded-full border border-rose-700 px-4 py-2 text-xs text-rose-200"
            onClick={() => logoutFirebase().then(() => window.location.replace('/login'))}
          >
            Sair
          </button>
        </div>
        {viewer ? <p className="text-sm text-slate-400 mt-4">Usuario conectado: {viewer.email || '-'}</p> : null}
      </section>
    </main>
  )
}
