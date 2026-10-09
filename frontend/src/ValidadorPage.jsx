import { useEffect, useState } from 'react'
import { logoutFirebase, subscribeAuth } from './firebaseAuth'

const BASE = (import.meta.env.VITE_AUTHENTICATOR_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')

export default function ValidadorPage() {
  const [, prefix, sourceAlias, documentId] = window.location.pathname.split('/')
  const [data, setData] = useState(null)
  const [versions, setVersions] = useState([])
  const [error, setError] = useState('')
  const [file, setFile] = useState(null)
  const [checking, setChecking] = useState(false)
  const [comparison, setComparison] = useState(null)
  const [viewer, setViewer] = useState(null)
  const [idToken, setIdToken] = useState('')
  const [authReady, setAuthReady] = useState(false)

  useEffect(() => {
    const unsubscribe = subscribeAuth(async (state) => {
      if (state.type === 'error') {
        setError(state.error?.message || 'Falha ao iniciar autenticacao Firebase.')
        setAuthReady(true)
        return
      }

      if (state.type === 'signed-in') {
        const token = await state.user.getIdToken()
        setViewer(state.user)
        setIdToken(token)
        setAuthReady(true)
        return
      }

      const next = encodeURIComponent(window.location.pathname)
      window.location.replace(`/login?next=${next}`)
    })

    return () => unsubscribe()
  }, [])

  useEffect(() => {
    if ((prefix || '').toLowerCase() !== 'validador' || !sourceAlias || !documentId) {
      setError('Link de validacao incompleto.')
      return
    }

    if (!authReady || !idToken) return

    fetch(`${BASE}/api/v1/validator/${encodeURIComponent(sourceAlias)}/${encodeURIComponent(documentId)}`, {
      headers: {
        Authorization: `Bearer ${idToken}`,
      },
    })
      .then(async (response) => {
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}))
          throw new Error(detail.detail || 'Documento nao encontrado para este apelido')
        }
        return response.json()
      })
      .then((payload) => {
        setData(payload)
        setVersions(payload.versions || [])
      })
      .catch((err) => setError(err.message || 'Falha na consulta de validacao'))
  }, [prefix, sourceAlias, documentId, authReady, idToken])

  async function compareFile(event) {
    event.preventDefault()
    if (!file) return
    setChecking(true)
    setComparison(null)
    try {
      const body = new FormData()
      body.set('file', file)
      const response = await fetch(`${BASE}/api/v1/validator/${encodeURIComponent(sourceAlias)}/${encodeURIComponent(documentId)}/file`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
        body,
      })
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}))
        throw new Error(detail.detail || 'Falha ao comparar o arquivo')
      }
      setComparison(await response.json())
    } catch (err) {
      setComparison({ valid: false, error: err.message || 'Nao foi possivel validar o arquivo.' })
    } finally {
      setChecking(false)
    }
  }

  return (
    <main className="max-w-5xl mx-auto p-5 md:p-12 text-slate-100">
      <header className="flex items-center justify-between gap-5 mb-10">
        <div>
          <p className="text-sm text-teal-300 uppercase tracking-widest">Macroambiental</p>
          <h1 className="text-3xl font-semibold mt-1">Validador de documento</h1>
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <span className="rounded-full border border-slate-600 px-4 py-2 text-sm">Equipe: {sourceAlias}</span>
          {viewer ? <span className="rounded-full border border-slate-700 px-4 py-2 text-xs text-slate-300">{viewer.email}</span> : null}
          {viewer ? (
            <button
              type="button"
              className="rounded-full border border-rose-700 px-4 py-2 text-xs text-rose-200"
              onClick={() => logoutFirebase().then(() => window.location.replace('/login'))}
            >
              Sair
            </button>
          ) : null}
        </div>
      </header>

      {error ? (
        <p role="alert" className="rounded-xl bg-red-950 border border-red-700 p-5">{error}</p>
      ) : !authReady ? (
        <p className="text-slate-300">Validando sessao...</p>
      ) : !data ? (
        <p className="text-slate-300">Consultando autenticidade do documento...</p>
      ) : (
        <>
          <section className="rounded-xl bg-slate-900 border border-slate-700 p-6 mb-6">
            <div className="flex gap-4 items-start justify-between">
              <div>
                <h2 className="text-xl font-medium">{data.title}</h2>
                <p className="text-sm text-slate-400 mt-2 break-all">Documento: {data.document_id}</p>
              </div>
              <strong className={`rounded-lg px-4 py-2 text-sm ${data.valid ? 'bg-emerald-900 text-emerald-100' : 'bg-red-900 text-red-100'}`}>
                {data.valid ? 'DOCUMENTO AUTENTICO' : 'INTEGRIDADE COMPROMETIDA'}
              </strong>
            </div>

            <dl className="grid sm:grid-cols-2 gap-4 mt-6 text-sm">
              <div>
                <dt className="text-slate-400">Versao atual</dt>
                <dd className="text-lg font-semibold">{data.version_number}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Total de versoes</dt>
                <dd className="text-lg font-semibold">{versions.length}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Tipo</dt>
                <dd>{data.document_type || '-'}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Assinatura</dt>
                <dd>{data.signature_status || '-'}</dd>
              </div>
            </dl>

            <p className="text-xs text-slate-400 mt-5 break-all">Hash SHA-256: {data.pdf_hash}</p>
            {data.valid ? (
              <a
                href={`${BASE}${data.pdf_path}`}
                target="_blank"
                rel="noreferrer"
                className="inline-block mt-6 rounded-md bg-teal-500 text-slate-950 font-semibold px-5 py-3"
              >
                Abrir PDF oficial
              </a>
            ) : null}
          </section>

          <section className="rounded-xl bg-slate-900 border border-slate-700 p-6 mb-6">
            <h2 className="text-lg font-semibold">Verificar se o PDF foi modificado</h2>
            <p className="text-slate-300 text-sm mt-2 mb-4">Envie o PDF para comparar com a versao autenticada mais recente deste documento.</p>
            <form onSubmit={compareFile} className="flex flex-wrap items-center gap-3">
              <input
                aria-label="Arquivo PDF"
                type="file"
                accept=".pdf,application/pdf"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
                className="max-w-full text-sm"
              />
              <button disabled={!file || checking} type="submit" className="rounded-md border border-teal-500 px-4 py-2 disabled:opacity-50">
                {checking ? 'Validando...' : 'Comparar arquivo'}
              </button>
            </form>
            {comparison ? (
              <p role="status" className={`mt-4 ${comparison.valid ? 'text-emerald-300' : 'text-red-300'}`}>
                {comparison.valid ? 'Arquivo identico ao autenticado.' : (comparison.error || 'Arquivo diverge do PDF autenticado.')}
              </p>
            ) : null}
          </section>

          <section className="rounded-xl bg-slate-900 border border-slate-700 p-6">
            <h2 className="text-lg font-semibold mb-4">Versoes e equipes que alteraram o documento</h2>
            <p className="text-amber-200 text-sm mb-4">Esta consulta mostra a ultima versao do documento. Para autenticar uma impressao antiga, abra a versao correspondente abaixo ou leia o QR Code especifico presente no PDF.</p>
            <ol className="space-y-3">
              {versions.map((version) => (
                <li key={version.version_id} className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-700 pb-3">
                  <div>
                    <span className="font-semibold">Versao {version.number}</span>
                    <span className="text-sm text-slate-400 ml-3">{version.created_at ? new Date(version.created_at).toLocaleString('pt-BR') : '-'}</span>
                    <p className="text-sm text-slate-300">Equipe: {version.team_name || '-'}</p>
                  </div>
                  <a className="text-teal-300 underline text-sm" href={`/verificar/${encodeURIComponent(documentId)}/${encodeURIComponent(version.version_id)}`}>
                    Abrir detalhe da versao
                  </a>
                </li>
              ))}
            </ol>
          </section>
        </>
      )}
    </main>
  )
}
