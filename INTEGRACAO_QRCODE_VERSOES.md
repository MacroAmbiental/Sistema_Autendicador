# Integracao do QR Code com versoes imutaveis dos checklists

## Fluxo implementado nos fontes

1. O Sistema de Equipamentos registra um evento duravel no PostgreSQL na criacao,
   alteracao confirmada ou assinatura do checklist.
2. O dispatcher envia o evento ao backend FastAPI do Autenticador.
3. A API gera ou recebe o PDF, insere o QR Code no canto inferior esquerdo de
   cada pagina e salva o PDF final imutavel no Firebase Storage (ou armazenamento
   local configurado explicitamente em desenvolvimento).
4. Cada URL de QR identifica **a versao exata** do PDF:
   `https://SEU-DOMINIO/verificar/{document_id}/{version_id}`.
5. A pagina de verificacao apresenta titulo, versao, data, assinatura SST,
   hash SHA-256, autenticidade e aviso quando houver versao posterior.
6. A conferencia de integridade recalcuta o SHA-256 do PDF + snapshot arquivados;
   a verificacao de um arquivo enviado compara seus bytes com o PDF oficial.
7. Todas as versoes continuam acessiveis, inclusive revisoes A -> B -> A.

## Significado do resultado

- AUTENTICO / ATUAL: bytes do PDF e snapshot conferem, e nao ha versao posterior registrada.
- AUTENTICO / ANTERIOR: bytes conferem, mas outra revisao foi publicada depois.
- INTEGRIDADE COMPROMETIDA: arquivos arquivados nao batem com hashes registrados.
- ARQUIVO DIVERGENTE: um PDF enviado manualmente nao tem os mesmos bytes da versao escolhida.
- EM PROCESSAMENTO: o checklist foi alterado no Equipamentos, mas ainda nao
  foi recebido/registrado no Firebase; o operador deve aguardar, nao imprimir o PDF antigo.

O QR de um documento impresso abre os arquivos oficiais arquivados, mas nao
analisa opticamente o papel: para detectar falsificacao da folha e necessario
comparar com o PDF oficial. Uma nova revisao NAO torna um PDF antigo falso.

## Requisitos para publicar

- Configurar `VERIFICATION_BASE_URL` com o dominio publico HTTPS do frontend
  do Autenticador. Nunca utilizar `localhost` em producao.
- Backend FastAPI: `AUTH_STORAGE_MODE=firebase`, Firebase IAM/Storage privado,
  `INTEGRATION_API_KEY` e `ADMIN_API_KEY`; usar HTTPS e segredos do servidor.
- Backend Java: `AUTENTICADOR_URL`, `AUTENTICADOR_INTEGRATION_KEY` (igual a
  INTEGRATION_API_KEY) e `AUTH_SESSION_SECRET`.
- PostgreSQL: aplicar Flyway V60, V61 e V62; iniciar scheduler de envio do outbox.
- Frontend Autenticador: `VITE_AUTHENTICATOR_API_BASE_URL` (API publicamente
  acessivel) e roteamento SPA para `/verificar/*`.
- Roteiro: criar checklist; visualizar PDF com QR; abrir QR em outro celular;
  alterar resposta; confirmar versao 2; reabrir QR da versao 1 e conferir
  'autentico - versao anterior'; comparar PDF original e alterado; assinar SST;
  validar PDF semanal e historico completo.

### Observacoes de migracao

Os QR Codes antigos gerados para `/Validador/{apelido}/{documento}` NAO
identificam a versao de origem. Para esse comportamento, os PDFs precisam ser
regenerados/republicados com QR individual, sem sobrescrever as versoes antigas.

O novo endpoint Java `GET /api/relatorios/{id}/historico` retorna o historico
semanal completo como DTO; a tela Relatorios utiliza esse endpoint para
montar o PDF diagramado com todos os dias da semana, independentemente dos
filtros da tabela.

### Evidencia de teste e limites

- Backend FastAPI: 12 testes locais passaram, incluindo leitura real do QR de
  dois PDFs com versoes diferentes e deteccao de PDF alterado.
- React: os arquivos alterados passaram por validacao sintatica JSX.
- Maven/JDK: build e teste integrado Java nao foram executados neste ambiente
  (Maven e dependencias de build nao disponiveis aqui).
- React: build Vite nao foi executado sem dependencias npm.
- Firebase / PostgreSQL reais: nao conectados nesta validacao.
- Os ZIPs atualizados sao fontes para integrar e testar, nao aplicacoes implantadas.
