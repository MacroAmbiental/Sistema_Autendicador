import { useEffect, useState } from 'react'
import { logoutToLogin, subscribeAuth } from './firebaseAuth'
import { hasTiPermission } from './permissions'

// const DEFAULT_API = 'http://127.0.0.1:8000'

const DEFAULT_API = 'https://sistema-autendicador-backend.onrender.com'

const CONNECTIONS_STORAGE_KEY = 'autenticador.savedConnections.v1'


const defaultConnection = {
  id: 'default',
  nickname: 'Conexao principal',
  apiUrl: DEFAULT_API,
  table: 'documentos',
  tables: ['documentos'],
  readScope: 'selected',
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
  const [documentsByTable, setDocumentsByTable] = useState({})
  const [health, setHealth] = useState(null)
  const [formData, setFormData] = useState(defaultForm)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [savedConnections, setSavedConnections] = useState([])
  const [selectedConnectionId, setSelectedConnectionId] = useState('')
  const [tableDraft, setTableDraft] = useState('')
  const [authReady, setAuthReady] = useState(false)
  const [idToken, setIdToken] = useState('')
  const [viewerEmail, setViewerEmail] = useState('')

  const sanitizeTables = (tables) => {
    const normalized = Array.isArray(tables) ? tables : []
    const cleaned = normalized
      .map((item) => String(item || '').trim())
      .filter(Boolean)

    const unique = [...new Set(cleaned)]
    return unique.length ? unique : ['documentos']
  }

  const normalizeConnection = (rawConnection, fallbackId = null) => {
    const tables = sanitizeTables(rawConnection?.tables || [rawConnection?.table])
    const selectedTable = String(rawConnection?.table || '').trim()
    const table = tables.includes(selectedTable) ? selectedTable : tables[0]
    return {
      id: rawConnection?.id || fallbackId || `conn-${Date.now()}`,
      nickname: String(rawConnection?.nickname || 'Sem apelido').trim() || 'Sem apelido',
      apiUrl: String(rawConnection?.apiUrl || DEFAULT_API).trim() || DEFAULT_API,
      table,
      tables,
      readScope: rawConnection?.readScope === 'all' ? 'all' : 'selected',
      token: String(rawConnection?.token || ''),
      sourceType: rawConnection?.sourceType === 'sql' ? 'sql' : 'api',
      sqlUrl: String(rawConnection?.sqlUrl || ''),
    }
  }

  const persistConnections = (connections) => {
    localStorage.setItem(CONNECTIONS_STORAGE_KEY, JSON.stringify(connections))
    setSavedConnections(connections)
  }

  const loadConnection = (connectionToLoad) => {
    const normalized = normalizeConnection(connectionToLoad)
    setConnection(normalized)
    setSelectedConnectionId(normalized.id)
    setFormData((current) => ({ ...current, collection_name: normalized.table }))
  }

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
        : typeof row.hashes === 'string'
          ? (() => {
              try {
                const parsed = JSON.parse(row.hashes)
                return Array.isArray(parsed) ? parsed : []
              } catch {
                return []
              }
            })()
        : typeof row.hash === 'string'
          ? [row.hash]
          : [],
      versions: Array.isArray(row.versions)
        ? row.versions
        : typeof row.versions === 'string'
          ? (() => {
              try {
                const parsed = JSON.parse(row.versions)
                return Array.isArray(parsed) ? parsed : []
              } catch {
                return []
              }
            })()
          : [],
      version_dates: Array.isArray(row.version_dates)
        ? row.version_dates
        : typeof row.version_dates === 'string'
          ? (() => {
              try {
                const parsed = JSON.parse(row.version_dates)
                return Array.isArray(parsed) ? parsed : []
              } catch {
                return []
              }
            })()
          : [],
      created_at: row.created_at ?? new Date().toISOString(),
      updated_at: row.updated_at ?? new Date().toISOString(),
    }))

  const getVersionSummary = (document) => {
    const hashes = Array.isArray(document?.hashes) ? document.hashes : []
    const versions = Array.isArray(document?.versions) ? document.versions : []
    const versionDates = Array.isArray(document?.version_dates) ? document.version_dates : []

    const count = versions.length || hashes.length || 0

    let dates = []
    if (versions.length) {
      dates = versions
        .map((version) => version?.created_at || version?.updated_at)
        .filter(Boolean)
    } else if (versionDates.length) {
      dates = versionDates.filter(Boolean)
    } else {
      const createdAt = document?.created_at
      const updatedAt = document?.updated_at
      if (createdAt) dates.push(createdAt)
      if (updatedAt && updatedAt !== createdAt && count > 1) dates.push(updatedAt)
    }

    const uniqueDates = [...new Set(dates)]
    const formattedDates = uniqueDates
      .map((value) => {
        const asDate = new Date(value)
        return Number.isNaN(asDate.getTime()) ? null : asDate.toLocaleString('pt-BR')
      })
      .filter(Boolean)

    return {
      count,
      formattedDates,
    }
  }

  const fetchDocuments = async (baseUrl = connection.apiUrl) => {
    try {
      if (connection.sourceType === 'sql') {
        if (!connection.sqlUrl) {
          setDocumentsByTable({})
          return []
        }

        const allTables = sanitizeTables(connection.tables)
        const tables = connection.readScope === 'all'
          ? allTables
          : [connection.table || allTables[0]]
        const settled = await Promise.allSettled(
          tables.map(async (tableName) => {
            const response = await fetch(`${baseUrl}/api/v1/sql/connect`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${idToken}`,
              },
              body: JSON.stringify({
                connection_string: connection.sqlUrl,
                table_name: tableName,
                limit: 100,
              }),
            })

            if (!response.ok) {
              const detail = await response.json().catch(() => ({}))
              throw new Error(detail.detail || `Falha ao ler a tabela ${tableName}`)
            }

            const payload = await response.json()
            return {
              tableName,
              rows: normalizeSqlDocuments(payload.rows, payload.table_name),
            }
          })
        )

        const nextDocumentsByTable = {}
        const tableErrors = []

        settled.forEach((result, index) => {
          const tableName = tables[index]
          if (result.status === 'fulfilled') {
            nextDocumentsByTable[tableName] = result.value.rows
            return
          }
          nextDocumentsByTable[tableName] = []
          tableErrors.push(`${tableName}: ${result.reason?.message || 'falha ao carregar'}`)
        })

        const loadedTables = Object.keys(nextDocumentsByTable).filter((name) => nextDocumentsByTable[name].length > 0)
        if (!loadedTables.length && tableErrors.length) {
          throw new Error(tableErrors.join(' | '))
        }

        setDocumentsByTable(nextDocumentsByTable)
        if (tableErrors.length) {
          setError(`Algumas tabelas falharam: ${tableErrors.join(' | ')}`)
        }

        return Object.values(nextDocumentsByTable).flat()
      }

      const response = await fetch(`${baseUrl}/api/v1/documents`)
      if (!response.ok) throw new Error('Falha ao ler a tabela')
      const payload = await response.json()
      const tableName = connection.table || 'documentos'
      setDocumentsByTable({ [tableName]: payload })
      return payload
    } catch (err) {
      setDocumentsByTable({})
      setError(connection.sourceType === 'sql'
        ? 'A string de conexão SQL do Render não está válida ou a tabela não pôde ser lida.'
        : 'A API respondeu, mas a tabela de documentos não pôde ser lida.')
      return []
    }
  }

  useEffect(() => {
    const unsubscribe = subscribeAuth(async (state) => {
      if (state.type === 'error') {
        setError(state.error?.message || 'Falha ao iniciar autenticacao.')
        setAuthReady(true)
        return
      }

      if (state.type === 'signed-in') {
        const token = await state.user.getIdToken()
        const allowed = await hasTiPermission(state.user)

        if (!allowed) {
          window.location.replace('/validador')
          return
        }

        setIdToken(token)
        setViewerEmail(state.user.email || '')
        setAuthReady(true)
        return
      }

      window.location.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`)
    })

    return () => unsubscribe()
  }, [])

  useEffect(() => {
    if (!authReady) return

    const stored = localStorage.getItem(CONNECTIONS_STORAGE_KEY)
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) {
          const normalizedConnections = parsed.map((item, index) => normalizeConnection(item, `conn-${index}`))
          setSavedConnections(normalizedConnections)
          loadConnection(normalizedConnections[0])
        }
      } catch {
        localStorage.removeItem(CONNECTIONS_STORAGE_KEY)
      }
    }

    fetchHealth()
    fetchDocuments()
  }, [authReady])

  const saveCurrentConnection = ({ showMessage = true } = {}) => {
    const normalized = normalizeConnection(connection, connection.id || `conn-${Date.now()}`)
    if (!normalized.nickname.trim()) {
      setError('Informe um apelido para salvar a conexão.')
      return false
    }

    const existing = savedConnections.find((item) => item.id === normalized.id)
    const updated = existing
      ? savedConnections.map((item) => (item.id === normalized.id ? normalized : item))
      : [...savedConnections, normalized]

    persistConnections(updated)
    setConnection(normalized)
    setSelectedConnectionId(normalized.id)

    if (showMessage) {
      setSuccess(`Conexão "${normalized.nickname}" salva com ${normalized.tables.length} tabela(s).`)
    }

    return true
  }

  const createNewConnection = () => {
    setConnection({
      ...defaultConnection,
      id: `conn-${Date.now()}`,
      nickname: 'Nova conexão',
    })
    setSelectedConnectionId('')
    setDocumentsByTable({})
    setFormData((current) => ({ ...current, collection_name: defaultConnection.table }))
    setError('')
    setSuccess('')
  }

  const addTableToConnection = () => {
    const tableName = tableDraft.trim()
    if (!tableName) {
      setError('Informe o nome da tabela para cadastrar.')
      return
    }

    setConnection((current) => {
      const tables = sanitizeTables([...(current.tables || []), tableName])
      const nextTable = current.table || tables[0]
      return { ...current, tables, table: nextTable }
    })
    setTableDraft('')
    setError('')
  }

  const removeTableFromConnection = (tableName) => {
    setConnection((current) => {
      const remainingTables = sanitizeTables((current.tables || []).filter((name) => name !== tableName))
      const nextTable = remainingTables.includes(current.table) ? current.table : remainingTables[0]
      setFormData((form) => ({ ...form, collection_name: nextTable }))
      return {
        ...current,
        tables: remainingTables,
        table: nextTable,
      }
    })
  }

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
      const tableCount = connection.sourceType === 'sql'
        ? (connection.readScope === 'all' ? sanitizeTables(connection.tables).length : 1)
        : 1
      setSuccess(`Conectado com sucesso em ${target}. ${rows.length} registro(s) carregados em ${tableCount} tabela(s).`)
      saveCurrentConnection({ showMessage: false })
    }
  }

  const handleSavedConnectionSelect = (event) => {
    const selectedId = event.target.value
    setSelectedConnectionId(selectedId)
    const selected = savedConnections.find((item) => item.id === selectedId)
    if (!selected) {
      return
    }
    loadConnection(selected)
    setDocumentsByTable({})
    setError('')
    setSuccess(`Conexão "${selected.nickname}" carregada.`)
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
        headers: {
          'Content-Type': 'application/json',
          ...(connection.sourceType === 'sql' ? { Authorization: `Bearer ${idToken}` } : {}),
        },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}))
        throw new Error(detail.detail || 'Não foi possível autenticar o documento.')
      }

      const document = await response.json()
      const activeTable = connection.table
      setDocumentsByTable((current) => {
        const tableRows = current[activeTable] || []
        return {
          ...current,
          [activeTable]: [document, ...tableRows],
        }
      })
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
            {!authReady ? (
              <div className="border border-[#e2e8e4] bg-white p-5 text-sm text-[#4a564f]">Validando permissao de acesso TI...</div>
            ) : null}
            <div className="mb-8">

              <div className="mb-2 flex items-center justify-between gap-3 flex-wrap">
                <div className="text-[11px] uppercase tracking-[0.25em] text-[#708278] font-bold">Acesso restrito TI</div>
                <div className="flex items-center gap-2">
                  {viewerEmail ? <span className="border border-[#e2e8e4] bg-white px-2 py-1 text-[10px] text-[#4a564f]">{viewerEmail}</span> : null}
                  <button
                    type="button"
                    onClick={logoutToLogin}
                    className="border border-rose-300 bg-white px-3 py-1 text-xs font-semibold text-rose-700"
                  >
                    Sair
                  </button>
                </div>
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
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                        Conexões salvas
                      </label>
                      <select
                        value={selectedConnectionId}
                        onChange={handleSavedConnectionSelect}
                        className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                      >
                        <option value="">Selecione uma conexão salva</option>
                        {savedConnections.map((saved) => (
                          <option key={saved.id} value={saved.id}>{saved.nickname}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                        Apelido da conexão
                      </label>
                      <input
                        value={connection.nickname}
                        onChange={(event) => setConnection((current) => ({ ...current, nickname: event.target.value }))}
                        className="w-full border border-[#e2e8e4] bg-[#f8fafc] px-3 py-3 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                        placeholder="Ex.: Produção Render"
                      />
                    </div>
                  </div>

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

                  <div className="border border-[#e2e8e4] bg-[#f8fafc] p-3">
                    <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                      Tabelas cadastradas
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {(connection.tables || []).map((tableName) => (
                        <div key={tableName} className="inline-flex items-center gap-2 border border-[#d7dfdb] bg-white px-2 py-1 text-xs">
                          <button
                            type="button"
                            onClick={() => {
                              setConnection((current) => ({ ...current, table: tableName }))
                              setFormData((current) => ({ ...current, collection_name: tableName }))
                            }}
                            className={`${connection.table === tableName ? 'text-[#1d4ed8] font-semibold' : 'text-[#4a564f]'}`}
                          >
                            {tableName}
                          </button>
                          <button
                            type="button"
                            onClick={() => removeTableFromConnection(tableName)}
                            className="text-rose-600"
                            aria-label={`Remover tabela ${tableName}`}
                          >
                            x
                          </button>
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <input
                        value={tableDraft}
                        onChange={(event) => setTableDraft(event.target.value)}
                        className="min-w-[220px] flex-1 border border-[#e2e8e4] bg-white px-3 py-2 text-sm text-[#0f1411] outline-none transition focus:border-[#2563eb]"
                        placeholder="Adicionar tabela"
                      />
                      <button
                        type="button"
                        onClick={addTableToConnection}
                        className="border border-[#2563eb] bg-white px-3 py-2 text-xs font-bold uppercase tracking-[0.12em] text-[#2563eb]"
                      >
                        Cadastrar tabela
                      </button>
                    </div>
                    <p className="mt-3 text-xs text-[#4a564f]">
                      Clique no nome da tabela para definir qual será usada ao autenticar novos documentos.
                    </p>

                    <div className="mt-3 border-t border-[#e2e8e4] pt-3">
                      <label className="mb-2 block text-[11px] uppercase tracking-[0.2em] font-bold text-[#708278]">
                        Leitura ao conectar
                      </label>
                      <div className="flex flex-wrap gap-3 text-sm text-[#4a564f]">
                        <label className="inline-flex items-center gap-2">
                          <input
                            type="radio"
                            name="read-scope"
                            checked={connection.readScope !== 'all'}
                            onChange={() => setConnection((current) => ({ ...current, readScope: 'selected' }))}
                          />
                          Apenas tabela selecionada
                        </label>
                        <label className="inline-flex items-center gap-2">
                          <input
                            type="radio"
                            name="read-scope"
                            checked={connection.readScope === 'all'}
                            onChange={() => setConnection((current) => ({ ...current, readScope: 'all' }))}
                          />
                          Todas as tabelas salvas
                        </label>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-2 sm:grid-cols-3">
                    <button
                      type="submit"
                      disabled={!authReady}
                      className="w-full bg-gradient-to-r from-[#2563eb] to-[#1d4ed8] px-4 py-3 text-sm font-bold uppercase tracking-[0.15em] text-white transition hover:from-[#1d4ed8] hover:to-[#1e40af]"
                    >
                      Conectar e ler tabelas
                    </button>
                    <button
                      type="button"
                      onClick={() => saveCurrentConnection({ showMessage: true })}
                      className="w-full border border-[#2563eb] bg-white px-4 py-3 text-sm font-bold uppercase tracking-[0.15em] text-[#2563eb] transition hover:bg-[#eff6ff]"
                    >
                      Salvar conexão
                    </button>
                    <button
                      type="button"
                      onClick={createNewConnection}
                      className="w-full border border-[#d7dfdb] bg-white px-4 py-3 text-sm font-bold uppercase tracking-[0.15em] text-[#4a564f] transition hover:bg-[#f8fafc]"
                    >
                      Nova conexão
                    </button>
                  </div>
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
                <h3 className="mb-4 text-base font-semibold text-[#0f1411]">Documentos autenticados</h3>

                <div className="space-y-4">
                  {Object.keys(documentsByTable).length === 0 ? (
                    <div className="border border-dashed border-[#dfe7e3] bg-[#f8fafc] p-5 text-sm text-[#708278]">
                      Nenhum documento autenticado nas tabelas selecionadas.
                    </div>
                  ) : (
                    Object.entries(documentsByTable).map(([tableName, tableDocuments]) => (
                      <div key={tableName} className="border border-[#e2e8e4] bg-white p-4">
                        <h4 className="mb-3 text-sm font-bold uppercase tracking-[0.16em] text-[#1f2937]">
                          Tabela: {tableName} ({tableDocuments.length})
                        </h4>
                        <div className="space-y-4">
                          {tableDocuments.length === 0 ? (
                            <div className="border border-dashed border-[#dfe7e3] bg-[#f8fafc] p-4 text-sm text-[#708278]">
                              Nenhum documento nessa tabela.
                            </div>
                          ) : tableDocuments.map((document) => (
                            <div key={`${tableName}-${document.public_id}`} className="border border-[#e2e8e4] bg-[#f8fafc] p-4">
                              {(() => {
                                const summary = getVersionSummary(document)
                                return (
                                  <>
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
                                <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.22em] text-[#708278]">Resumo de versões</p>
                                <p className="text-sm text-[#4a564f]">
                                  <span className="text-[#708278]">Quantidade:</span> {summary.count || 1}
                                </p>
                                <p className="mt-1 text-sm text-[#4a564f]">
                                  <span className="text-[#708278]">Datas:</span>{' '}
                                  {summary.formattedDates.length ? summary.formattedDates.join(' | ') : 'Não disponível'}
                                </p>
                              </div>

                              <div className="mt-4 border border-[#e2e8e4] bg-white p-3">
                                <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.22em] text-[#708278]">Hashes</p>
                                <div className="space-y-2">
                                  {(document.hashes || []).map((hash, index) => (
                                    <div
                                      key={`${tableName}-${document.public_id}-${index}`}
                                      className="border border-[#e2e8e4] bg-[#f8fafc] px-2 py-1 text-[11px] text-[#0f1411] break-all"
                                    >
                                      {index + 1}. {hash}
                                    </div>
                                  ))}
                                </div>
                              </div>
                                  </>
                                )
                              })()}
                            </div>
                          ))}
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
