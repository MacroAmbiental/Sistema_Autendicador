import { useEffect, useState } from 'react'

const DEFAULT_API = 'http://127.0.0.1:8000'

const defaultConnection = {
  apiUrl: DEFAULT_API,
  table: 'documentos',
  token: '',
  sourceType: 'api',
  sqlUrl: '',
}

const defaultForm = {
  title: '',
  document_type: '',
  reference_period: '',
  owner_name: '',
  content: '',
  collection_name: 'documentos',
}

const FEATURES = [
  { label: 'Conexão', tone: 'border-slate-700 bg-slate-900/80' },
  { label: 'Tabela', tone: 'border-slate-700 bg-slate-900/80' },
  { label: 'Hashes', tone: 'border-slate-700 bg-slate-900/80' },
  { label: 'Validação', tone: 'border-slate-700 bg-slate-900/80' },
]

function StatCard({ label, value, muted = false }) {
  return (
    <div className="border border-slate-800 bg-slate-900 p-4">
      <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">{label}</p>
      <p className={`mt-3 text-base font-medium ${muted ? 'text-slate-200' : 'text-white'}`}>
        {value}
      </p>
    </div>
  )
}

function App() {
  const [connection, setConnection] = useState(defaultConnection)
  const [documents, setDocuments] = useState([])
  const [health, setHealth] = useState(null)
  const [formData, setFormData] = useState(defaultForm)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const fetchHealth = async () => {
    try {
      const response = await fetch(`${connection.apiUrl}/api/v1/health`)
      if (!response.ok) throw new Error('Falha ao consultar a API')
      const payload = await response.json()
      setHealth(payload)
      return payload
    } catch (err) {
      setHealth({ status: 'offline', application: 'Autenticador Macroambiental', environment: 'desconectado' })
      setError('Não foi possível conectar com a API informada.')
      return null
    }
  }

  const normalizeSqlDocuments = (rows, tableName) =>
    (rows || []).map((row, index) => ({
      internal_id: row.id ?? row.internal_id ?? `sql-${index}`,
      public_id: row.public_id ?? `sql-${index}`,
      title: row.title ?? row.nome ?? `Registro ${index + 1}`,
      document_type: row.document_type ?? row.tipo ?? 'sql-table',
      reference_period: row.reference_period ?? row.periodo ?? '',
      owner_name: row.owner_name ?? row.responsavel ?? '',
      collection_name: row.collection_name ?? tableName,
      content: row.content ?? row.conteudo ?? '',
      status: row.status ?? 'sql',
      hashes: Array.isArray(row.hashes)
        ? row.hashes
        : typeof row.hash === 'string'
          ? [row.hash]
          : [],
      created_at: row.created_at ?? new Date().toISOString(),
      updated_at: row.updated_at ?? new Date().toISOString(),
    }))

  const fetchDocuments = async (baseUrl = connection.apiUrl) => {
    try {
      if (connection.sourceType === 'sql') {
        if (!connection.sqlUrl) {
          setDocuments([])
          return []
        }

        const response = await fetch(`${baseUrl}/api/v1/sql/connect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            connection_string: connection.sqlUrl,
            table_name: connection.table,
            limit: 100,
          }),
        })

        if (!response.ok) {
          const detail = await response.json().catch(() => ({}))
          throw new Error(detail.detail || 'Falha ao ler a tabela SQL')
        }

        const payload = await response.json()
        const normalizedRows = normalizeSqlDocuments(payload.rows, payload.table_name)
        setDocuments(normalizedRows)
        return normalizedRows
      }

      const response = await fetch(`${baseUrl}/api/v1/documents`)
      if (!response.ok) throw new Error('Falha ao ler a tabela')
      const payload = await response.json()
      setDocuments(payload)
      return payload
    } catch (err) {
      setDocuments([])
      setError(connection.sourceType === 'sql'
        ? 'A string de conexão SQL do Render não está válida ou a tabela não pôde ser lida.'
        : 'A API respondeu, mas a tabela de documentos não pôde ser lida.')
      return []
    }
  }

  useEffect(() => {
    fetchHealth()
    fetchDocuments()
  }, [])

  const handleConnection = async (event) => {
    event.preventDefault()
    setError('')
    setSuccess('')

    if (connection.sourceType === 'sql' && !connection.sqlUrl) {
      setError('Informe a string de conexão do Render para conectar na tabela SQL.')
      return
    }

    const apiHealth = await fetchHealth()
    const rows = await fetchDocuments(connection.apiUrl)
    const target = connection.sourceType === 'sql' ? 'Render SQL' : 'API'

    if (!rows || rows.length === 0) {
      setError(
        connection.sourceType === 'sql'
          ? `Não foi possível ler registros da tabela ${connection.table}. Verifique a conexão e o nome da tabela.`
          : `Não foi possível conectar com a API informada.`
      )
      return
    }

    if (apiHealth || connection.sourceType === 'sql') {
      setSuccess(`Conectado com sucesso em ${target}. ${rows.length} registro(s) carregados da tabela ${connection.table}.`)
    }
  }

  const handleChange = (event) => {
    const { name, value } = event.target
    setFormData((current) => ({ ...current, [name]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')

    try {
      const payload = {
        ...formData,
        collection_name: connection.table || formData.collection_name,
      }

      const endpoint = connection.sourceType === 'sql'
        ? `${connection.apiUrl}/api/v1/sql/documents`
        : `${connection.apiUrl}/api/v1/documents`

      const body = connection.sourceType === 'sql'
        ? {
            ...payload,
            connection_string: connection.sqlUrl,
            table_name: connection.table,
          }
        : payload

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}))
        throw new Error(detail.detail || 'Não foi possível autenticar o documento.')
      }

      const document = await response.json()
      setDocuments((current) => [document, ...current])
      setFormData({ ...defaultForm, collection_name: connection.table })
      setSuccess(`Documento autenticado. ${document.hashes.length || 1} hash(es) registrados.`)
      if (connection.sourceType === 'sql') {
        await fetchDocuments(connection.apiUrl)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const stats = [
    { label: 'Status', value: health?.status || '...', primary: true },
    { label: 'Aplicação', value: health?.application || 'Carregando...', muted: true },
    { label: 'Ambiente', value: health?.environment || 'Carregando...', muted: true },
  ]

  return (
    <div className="min-h-screen bg-[#f5f7fa] text-[#0f1411]">
      <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="w-full">
          <div className="space-y-8">
            <div className="mb-8">

              <div className="mb-2 text-[11px] uppercase tracking-[0.25em] text-[#708278] font-bold">
                Acesso restrito
              </div>
              <h2 className="font-black text-3xl sm:text-4xl tracking-tight text-[#0f1411]">
                Autenticador
              </h2>
              <p className="mt-2 text-sm text-[#4a564f]">
                Conecte a API, selecione a coleção e autentique os documentos com histórico criptografado.
              </p>
            </div>

            <div className="space-y-6">
              <section className="border border-[#e2e8e4] bg-white p-5">
                <div className="mb-4 flex items-center justify-between gap-3 border-b border-[#e2e8e4] pb-3">
                  <h3 className="text-base font-semibold text-[#0f1411]">Conexão da API</h3>
                  <span className="border border-slate-300 bg-slate-50 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-slate-600">
                    {connection.apiUrl}
                  </span>
                </div>

                <form className="space-y-4" onSubmit={handleConnection}>
                  <div>
                    <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                      Tipo de conexão
                    </label>
                    <select
                      value={connection.sourceType}
                      onChange={(event) => setConnection((current) => ({ ...current, sourceType: event.target.value }))}
                      className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                    >
                      <option value="api">API</option>
                      <option value="sql">SQL (Render)</option>
                    </select>
                  </div>

                  <div>
                    <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                      {connection.sourceType === 'sql' ? 'URL da API do backend' : 'URL da API'}
                    </label>
                    <input
                      value={connection.apiUrl}
                      onChange={(event) => setConnection((current) => ({ ...current, apiUrl: event.target.value }))}
                      className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                      placeholder="https://api.exemplo.com"
                    />
                  </div>

                  {connection.sourceType === 'sql' ? (
                    <div>
                      <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                        String de conexão Render (Postgres)
                      </label>
                      <input
                        value={connection.sqlUrl}
                        onChange={(event) => setConnection((current) => ({ ...current, sqlUrl: event.target.value }))}
                        className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                        placeholder="postgresql://user:password@host:5432/database"
                      />
                    </div>
                  ) : (
                    <div>
                      <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                        Token / chave
                      </label>
                      <input
                        type="password"
                        value={connection.token}
                        onChange={(event) => setConnection((current) => ({ ...current, token: event.target.value }))}
                        className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                        placeholder="Bearer token"
                      />
                    </div>
                  )}

                  <div>
                    <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                      Tabela / coleção
                    </label>
                    <input
                      value={connection.table}
                      onChange={(event) => {
                        const value = event.target.value
                        setConnection((current) => ({ ...current, table: value }))
                        setFormData((current) => ({ ...current, collection_name: value }))
                      }}
                      className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                      placeholder="documentos"
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full bg-gradient-to-r from-[#2563eb] to-[#1d4ed8] px-4 py-3 text-sm font-bold uppercase tracking-[0.15em] text-white transition hover:from-[#1d4ed8] hover:to-[#1e40af]"
                  >
                    Conectar e ler tabela
                  </button>
                </form>

                <div className="mt-6 border border-[#e2e8e4] bg-[#f8fafc] p-4">
                  <p className="text-[10px] uppercase tracking-[0.22em] text-[#708278]">Observação</p>
                  <p className="mt-3 text-sm leading-6 text-[#4a564f]">
                    O autenticador valida cada documento da coleção e mantém um histórico de hashes. Toda alteração gera um novo hash criptografado, preservando a cadeia de integridade do registro.
                  </p>
                </div>

                {error ? (
                  <div className="mt-4 border border-rose-500/50 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                    {error}
                  </div>
                ) : null}

                {success ? (
                  <div className="mt-4 border border-emerald-500/50 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                    {success}
                  </div>
                ) : null}
              </section>

              <section className="border border-[#e2e8e4] bg-white p-5">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h3 className="text-base font-semibold text-[#0f1411]">Autenticar novo documento</h3>
                  <div className="inline-flex items-center gap-2 border border-[#e2e8e4] bg-[#f8fafc] px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-[#708278]">
                    <span className={`h-2 w-2 ${health?.status === 'ok' ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                    {health?.status === 'ok' ? 'Online' : 'Offline'}
                  </div>
                </div>

                <form className="space-y-4" onSubmit={handleSubmit}>
                  <div>
                    <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                      Título
                    </label>
                    <input
                      name="title"
                      value={formData.title}
                      onChange={handleChange}
                      className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                      placeholder="Ex.: Relatório de monitoramento"
                    />
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                        Tipo
                      </label>
                      <input
                        name="document_type"
                        value={formData.document_type}
                        onChange={handleChange}
                        className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                        placeholder="Ex.: Laudo"
                      />
                    </div>

                    <div>
                      <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                        Período
                      </label>
                      <input
                        name="reference_period"
                        value={formData.reference_period}
                        onChange={handleChange}
                        className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                        placeholder="2026/Q4"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                      Responsável
                    </label>
                    <input
                      name="owner_name"
                      value={formData.owner_name}
                      onChange={handleChange}
                      className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                      placeholder="Nome do responsável"
                    />
                  </div>

                  <div>
                    <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                      Conteúdo do documento
                    </label>
                    <textarea
                      name="content"
                      value={formData.content}
                      onChange={handleChange}
                      rows="5"
                      className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                      placeholder="Conteúdo do arquivo ou texto a ser autenticado"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-gradient-to-r from-[#2563eb] to-[#1d4ed8] px-4 py-3 text-sm font-bold uppercase tracking-[0.15em] text-white transition hover:from-[#1d4ed8] hover:to-[#1e40af] disabled:opacity-50"
                  >
                    {loading ? 'Autenticando...' : 'Autenticar documento'}
                  </button>
                </form>
              </section>

              <section className="border border-[#e2e8e4] bg-white p-5">
                <h3 className="mb-4 text-base font-semibold text-[#0f1411]">Documentos autenticados</h3>

                <div className="space-y-4">
                  {documents.length === 0 ? (
                    <div className="border border-dashed border-[#dfe7e3] bg-[#f8fafc] p-5 text-sm text-[#708278]">
                      Nenhum documento autenticado na tabela selecionada.
                    </div>
                  ) : (
                    documents.map((document) => (
                      <div key={document.public_id} className="border border-[#e2e8e4] bg-[#f8fafc] p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-base font-medium text-[#0f1411]">{document.title}</p>
                          <span className="border border-[#dfe7e3] bg-white px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-[#4a564f]">
                            {document.status}
                          </span>
                        </div>

                        <div className="mt-3 space-y-2 text-sm text-[#4a564f]">
                          <p><span className="text-[#708278]">Coleção:</span> {document.collection_name}</p>
                          <p><span className="text-[#708278]">Tipo:</span> {document.document_type}</p>
                          <p><span className="text-[#708278]">Responsável:</span> {document.owner_name || 'Não informado'}</p>
                        </div>

                        <div className="mt-4 border border-[#e2e8e4] bg-white p-3">
                          <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.22em] text-[#708278]">Hashes</p>
                          <div className="space-y-2">
                            {document.hashes.map((hash, index) => (
                              <div
                                key={`${document.public_id}-${index}`}
                                className="border border-[#e2e8e4] bg-[#f8fafc] px-2 py-1 text-[11px] text-[#0f1411] break-all"
                              >
                                {index + 1}. {hash}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </section>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
