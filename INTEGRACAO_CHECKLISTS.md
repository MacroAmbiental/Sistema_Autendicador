# Autenticador Macroambiental — versoes de checklists

## Entrega implementada

- `POST /api/v1/checklists/versions`: servidor de equipamentos envia um evento com identificador idempotente, documento logico, JSON das respostas e PDF opcional; autenticador cria uma versao imutavel, inclui QR na margem **inferior esquerda de cada pagina** e calcula hashes SHA-256 do PDF final e do snapshot JSON.
- Documento logico semanal estavel: varias alteracoes diarias e a assinatura do SST podem produzir versoes sob o mesmo ID, cada uma com PDF/JSON independentes e `previous_version`.
- `GET /api/v1/verify/{document_id}/{version_id}`: compara hash dos bytes arquivados com os hashes do registro e audita o acesso (data/hora Sao Paulo, Desktop/Mobile, IDs, resultado).
- `GET /api/v1/verify/{document_id}/{version_id}/pdf`: disponibiliza PDF oficial, verifica hash e audita a leitura.
- `POST /api/v1/verify/{document_id}/{version_id}/file`: compara PDF fornecido byte a byte via hash.
- `GET /api/v1/checklists/{document_id}/versions`: historico de todas as versoes do documento.
- `GET /api/v1/admin/checklists` e `/api/v1/admin/audits`: painel administrativo com credencial separada; acesso web em `/administracao`.
- Portal publico de consulta React/Vite em `/verificar/{document_id}/{version_id}`.

## Instalar e configurar (backend FastAPI)

```bash
cd backend
python -m venv .venv
# Ative o ambiente virtual conforme seu sistema operacional.
pip install -r requirements.txt
cp .env.example .env
# Edite .env ANTES de iniciar. Nunca versione credenciais verdadeiras.
python -m uvicorn app.main:app --reload --port 8000
python -m pytest -q
```

Em producao, configure **APP_ENV=production** e **AUTH_STORAGE_MODE=firebase**. Configure `FIREBASE_PROJECT_ID`, `FIREBASE_STORAGE_BUCKET`, Application Default Credentials/service account de menor privilegio com acesso a Firestore e ao bucket privado, `INTEGRATION_API_KEY` (somente servidor-servidor), `ADMIN_API_KEY` (independente), `VERIFICATION_BASE_URL` (origem do site React) e `CORS_ORIGINS` (origens React autorizadas). Nao exponha as chaves no JavaScript do navegador. Ative HTTPS e proteja e monitore os segredos no ambiente de hospedagem.

Firestore cria indice `autenticacoes_checklists/{document_id}/versoes/{version_id}` e colecao `auditoria_consultas`. PDFs/JSON ficam em `checklists/{document_id}/{version_id}.pdf|json` no Cloud Storage com condicao de **nao sobrescrever** (`if_generation_match=0`). O armazenamento local (`AUTH_STORAGE_MODE=local`) existe **somente para desenvolvimento e testes**, explicitamente configurado; nao deve ser usado em producao.

## Frontend do Autenticador

```bash
cd frontend
npm ci
# Configure frontend/.env com VITE_AUTHENTICATOR_API_BASE_URL=https://API_AUTENTICADOR
npm run dev
```

Configure o provedor de hospedagem do SPA para redirecionar as URLs `/verificar/*` e `/administracao` a `/index.html` (exemplo em `frontend/public/_redirects`). O endpoint de auditorias administrativas exige o header `X-Admin-Key`; o de registro de versoes exige `X-Integration-Key`.

## Observacoes de seguranca e operacao

- A verificacao confirma integridade criptografica **dos bytes do PDF e do snapshot JSON arquivados**. Nao detecta semanticamente se o preenchimento original era verdadeiro e nao valida uma folha de papel sem conferencia contra o PDF oficial.
- As imagens de assinatura dos checklists NAO sao assinaturas digitais certificadas (ICP-Brasil). A integridade da versao e a autenticacao de usuario sao controles distintos.
- Versao antiga pode continuar autentica e apenas estar superada por outra. O portal informa quando nao e a ultima versao.
- O PDF automatico dos eventos de salvamento e um comprovante legivel simplificado da alteracao. O PDF diagramado da tela de Relatorios, com assinaturas, tambem e autenticado como sua propria versao; o snapshot integral continua preservado.
- **Retencao legal**: como nao foi fornecido um periodo oficial de retencao, este codigo NAO executa exclusao automatica. Defina regra documental, politicas de backup, retencao/lock do Storage, seguranca IAM e eventual Firestore TTL antes de producao; nunca apague versoes anteriores casualmente.
- Validacao real do Firebase/Storage, hospedagem, autorizacoes e integracao ponta-a-ponta exige as credenciais e a infraestrutura do cliente; nao foi executada nesta entrega. Os testes locais podem usar armazenamento local isolado.
- As rotas legadas experimentais `/api/v1/documents` estao desabilitadas em `APP_ENV=production`; o antigo conector SQL que aceitava DSN arbitrario **nao esta roteado**.

## Testes

`cd backend && python -m pytest -q` verifica criacao de versoes, QR embutido, hashes, alteracao indevida, historico, auditoria e bloqueio da antiga rota SQL; em desenvolvimento local usa o modo `local` configurado apenas dentro dos testes.
