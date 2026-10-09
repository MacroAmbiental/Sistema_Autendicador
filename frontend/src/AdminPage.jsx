import { useState } from 'react'

const API = (import.meta.env.VITE_AUTHENTICATOR_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')

export default function AdminPage() {
  const [key, setKey] = useState('')
  const [docs, setDocs] = useState([])
  const [audits, setAudits] = useState([])
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [loaded, setLoaded] = useState(false)

  async function consultar(event) {
    event.preventDefault()
    setError(''); setPending(true)
    try {
      if (!key) throw new Error('Informe a credencial de administracao.')
      const headers = { 'X-Admin-Key': key }
      const [d, a] = await Promise.all([
        fetch(`${API}/api/v1/admin/checklists?limit=100`, { headers }),
        fetch(`${API}/api/v1/admin/audits?limit=100`, { headers }),
      ])
      if (!d.ok || !a.ok) throw new Error('Credencial invalida ou servico indisponivel.')
      setDocs(await d.json()); setAudits(await a.json()); setLoaded(true)
    } catch (err) { setError(err.message || 'Nao foi possivel consultar o painel.'); setLoaded(false) }
    finally { setPending(false) }
  }

  return <main className="max-w-6xl mx-auto p-5 md:p-12 text-slate-100">
    <header className="mb-8"><p className="text-sm tracking-widest text-teal-300 uppercase">Macroambiental · Gestao restrita</p>
      <h1 className="text-3xl font-bold mt-2">Painel do autenticador</h1>
      <p className="text-slate-400 mt-2">Consulte documentos autenticados e auditorias. A chave fica apenas na memoria da pagina.</p></header>
    <form onSubmit={consultar} className="flex flex-wrap items-end gap-3 mb-8 p-5 border border-slate-700 rounded-xl bg-slate-900">
      <label className="flex-1 min-w-60 text-sm">Credencial administrativa
        <input value={key} type="password" autoComplete="off" onChange={e => setKey(e.target.value)} className="w-full block bg-slate-950 border border-slate-600 rounded-md p-3 mt-2" />
      </label>
      <button type="submit" disabled={pending} className="px-5 py-3 rounded-md bg-teal-400 text-slate-950 font-semibold disabled:opacity-50">{pending ? 'Carregando...' : 'Consultar'}</button>
    </form>
    {error && <p role="alert" className="rounded-md bg-red-950 p-4 border border-red-700 mb-5">{error}</p>}
    {loaded && <>
      <p className="text-slate-400 mb-7">Amostra dos ultimos registros: {docs.length} documentos e {audits.length} consultas (limite de 100 em cada lista).</p>
      <section className="rounded-xl bg-slate-900 border border-slate-700 p-5 mb-6">
        <h2 className="text-xl font-semibold mb-4">Documentos cadastrados</h2>
        <div className="overflow-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-slate-600"><th className="p-3">Documento</th><th className="p-3">Versoes</th><th className="p-3">Atualizado em</th></tr></thead>
          <tbody>{docs.map(doc => <tr className="border-b border-slate-800" key={doc.document_id}><td className="p-3 break-all">{doc.title || doc.document_id}<div className="text-slate-400 text-xs">{doc.document_id}</div></td><td className="p-3">{doc.latest_version}</td><td className="p-3">{doc.updated_at ? new Date(doc.updated_at).toLocaleString('pt-BR') : '-'}</td></tr>)}</tbody></table></div>
        {!docs.length && <p className="text-slate-400">Nenhum documento cadastrado.</p>}
      </section>
      <section className="rounded-xl bg-slate-900 border border-slate-700 p-5">
        <h2 className="text-xl font-semibold mb-4">Auditoria de consultas</h2>
        <div className="overflow-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-slate-600"><th className="p-3">Data e hora (Brasil)</th><th className="p-3">Dispositivo</th><th className="p-3">Documento / versao</th><th className="p-3">Resultado</th></tr></thead>
          <tbody>{audits.map(row => <tr className="border-b border-slate-800" key={row.audit_id}><td className="p-3 whitespace-nowrap">{row.datetime_br}</td><td className="p-3">{row.device}</td><td className="p-3 break-all">{row.document_id} / {row.version_id?.slice(0, 10)}</td><td className="p-3">{row.result}</td></tr>)}</tbody></table></div>
        {!audits.length && <p className="text-slate-400">Sem consultas registradas.</p>}
      </section>
    </>}
  </main>
}
