import { useEffect, useState } from 'react'
import { logoutToLogin } from './firebaseAuth'

const BASE = (import.meta.env.VITE_AUTHENTICATOR_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')

export default function VerificationPage() {
  const [, prefix, docId, versionId] = window.location.pathname.split('/')
  const [data, setData] = useState(null)
  const [versions, setVersions] = useState([])
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(false)
  const [comparison, setComparison] = useState(null)
  const [file, setFile] = useState(null)

  useEffect(() => {
    if (prefix !== 'verificar' || !docId || !versionId) {
      setError('Link de verificacao incompleto.'); return
    }
    const documentId = encodeURIComponent(docId)
    const version = encodeURIComponent(versionId)
    fetch(`${BASE}/api/v1/verify/${documentId}/${version}`).then(async (resp) => {
      if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'Documento nao encontrado')
      const payload = await resp.json()

      // NUNCA redirecionar o QR de uma versao a pagina generica: isso perderia
      // a identidade do PDF que foi escaneado.
      setData(payload)
      const list = await fetch(`${BASE}/api/v1/checklists/${documentId}/versions`)
      if (list.ok) setVersions((await list.json()).versions || [])
    }).catch(err => setError(err.message || 'Falha na consulta'))
  }, [prefix, docId, versionId])

  async function compare(e) {
    e.preventDefault()
    if (!file) return
    setChecking(true)
    setComparison(null)
    try {
      const form = new FormData()
      form.set('file', file)
      const response = await fetch(`${BASE}/api/v1/verify/${encodeURIComponent(docId)}/${encodeURIComponent(versionId)}/file`, {
        method: 'POST', body: form,
      })
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Falha na comparacao')
      setComparison(await response.json())
    } catch (err) { setComparison({ valid: false, error: err.message }) }
    finally { setChecking(false) }
  }

  return (
    <main className="max-w-5xl mx-auto p-5 md:p-12 text-slate-100">
      <header className="flex items-center justify-between gap-5 mb-10">
        <div><p className="text-sm text-teal-300 uppercase tracking-widest">Macroambiental</p><h1 className="text-3xl font-semibold mt-1">Verificacao de documentos</h1></div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-slate-600 px-4 py-2 text-sm">Portal SERTRAS</span>
          <button type="button" onClick={logoutToLogin} className="rounded-full border border-rose-700 px-4 py-2 text-xs text-rose-200">Sair</button>
        </div>
      </header>
      {error ? <p role="alert" className="rounded-xl bg-red-950 border border-red-700 p-5">{error}</p> : !data ?
        <p className="text-slate-300">Consultando autenticacao e auditoria...</p> : <>
          <section className="rounded-xl bg-slate-900 border border-slate-700 p-6 mb-6">
            <div className="flex gap-4 items-start justify-between">
              <div><h2 className="text-xl font-medium">{data.title}</h2><p className="text-sm text-slate-400 mt-2 break-all">Documento: {docId}</p></div>
              <strong className={`rounded-lg px-4 py-2 text-sm ${data.valid ? 'bg-emerald-900 text-emerald-100' : 'bg-red-900 text-red-100'}`}>{data.valid ? (data.is_latest ? 'AUTENTICO - VERSAO ATUAL' : 'AUTENTICO - VERSAO ANTERIOR') : 'INTEGRIDADE COMPROMETIDA'}</strong>
            </div>
            <dl className="grid sm:grid-cols-2 gap-4 mt-6 text-sm">
              <div><dt className="text-slate-400">Versao verificada</dt><dd className="text-lg font-semibold">{data.number} de {data.latest_version}</dd></div>
              <div><dt className="text-slate-400">Historico</dt><dd className="text-lg font-semibold">{data.is_latest ? 'Versao mais recente' : 'Existe versao posterior'}</dd></div>
              <div><dt className="text-slate-400">Assinaturas</dt><dd>{data.signature_status === 'assinado' ? 'Versao com assinatura SST' : 'Aguardando SST'}</dd></div>
              <div><dt className="text-slate-400">Registro UTC</dt><dd>{new Date(data.created_at).toLocaleString('pt-BR')}</dd></div>
            </dl>
            <p className="text-xs text-slate-400 mt-5 break-all">Hash SHA-256 do arquivo: {data.pdf_hash}</p>
            <p className="text-xs text-slate-400 mt-2">A autenticidade se refere a esta versao especifica. Alteracoes posteriores geram novas versoes, sem falsificar as antigas. Um papel impresso deve ser comparado ao PDF oficial.</p>
            {data.valid && !data.is_latest && <p role="status" className="mt-3 text-amber-300 text-sm font-semibold">Existe uma versao mais recente deste checklist. Consulte o historico abaixo antes de utilizar esta impressao.</p>}
            {data.valid && <a href={`${BASE}${data.pdf_path}`} target="_blank" rel="noreferrer" className="inline-block mt-6 rounded-md bg-teal-500 text-slate-950 font-semibold px-5 py-3">Abrir PDF oficial com QR Code</a>}
          </section>
          <section className="rounded-xl bg-slate-900 border border-slate-700 p-6 mb-6">
            <h2 className="text-lg font-semibold">Comparar um arquivo PDF</h2>
            <p className="text-slate-300 text-sm mt-2 mb-4">Envie o PDF original para verificar se seus bytes correspondem exatamente a esta versao.</p>
            <form onSubmit={compare} className="flex flex-wrap items-center gap-3">
              <input aria-label="Arquivo PDF" type="file" accept=".pdf,application/pdf" onChange={e => setFile(e.target.files?.[0] || null)} className="max-w-full text-sm" />
              <button disabled={!file || checking} type="submit" className="rounded-md border border-teal-500 px-4 py-2 disabled:opacity-50">{checking ? 'Verificando...' : 'Verificar arquivo'}</button>
            </form>
            {comparison && <p role="status" className={`mt-4 ${comparison.valid ? 'text-emerald-300' : 'text-red-300'}`}>{comparison.valid ? 'Arquivo identico ao registrado.' : (comparison.error || 'Arquivo diferente do PDF autenticado.')}</p>}
          </section>
          <section className="rounded-xl bg-slate-900 border border-slate-700 p-6">
            <h2 className="text-lg font-semibold mb-4">Historico do mesmo documento</h2>
            <ol className="space-y-3">
              {versions.map(v => <li key={v.version_id} className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-700 pb-3">
                <div><span className="font-semibold">Versao {v.number}</span><span className="text-sm text-slate-400 ml-3">{new Date(v.created_at).toLocaleString('pt-BR')}</span><p className="text-sm text-slate-300">{v.signature_status === 'assinado' ? 'Com assinatura SST' : 'Em execucao'}</p></div>
                <a className="text-teal-300 underline text-sm" href={`/verificar/${encodeURIComponent(docId)}/${encodeURIComponent(v.version_id)}`}>Consultar esta versao</a>
              </li>)}
            </ol>
          </section>
        </>}
    </main>
  )
}
