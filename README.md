# Sistema Autenticador Macroambiental

Este repositório reúne a concepção inicial do sistema de autenticação e rastreabilidade documental para documentos do tipo PDF/semiautomatizados, com foco em integridade, histórico, auditoria e validação pública.

## Visão geral

O sistema foi pensado para permitir que um documento tenha:

- um identificador único permanente;
- um QR Code único para validação;
- múltiplas autenticações vinculadas ao mesmo documento;
- histórico de versões e um registro de auditoria;
- validação pública sem expor dados sensíveis;
- controle de acesso e segurança por camadas.

## Estrutura base do projeto

- `backend/app` — aplicação FastAPI
- `backend/app/core` — configuração e integrações (Firebase, settings)
- `backend/app/api` — rotas da API e endpoints de saúde
- `backend/tests` — testes automatizados
- `firebase/` — recursos locais e configurações do Firebase

## Objetivos principais

- autenticar documentos sem gerar QR Codes duplicados;
- registrar autenticações por evento e por versão;
- permitir rastreabilidade do ciclo de vida do documento;
- garantir integridade via hashes e versões;
- reduzir risco de alteração indevida do arquivo original.

## Execução local

1. Entre na pasta do backend.
2. Crie um ambiente virtual.
3. Instale as dependências com `pip install -r requirements.txt`.
4. Inicie a API com `uvicorn app.main:app --reload`.
5. Acesse a UI básica em `/frontend` e a API em `/api/v1/health`.

## Observações de segurança

- nunca versionar `.env` com segredos;
- manter chaves e credenciais fora do repositório;
- revisar Firestore Security Rules antes de produção;
- usar ambiente separado para desenvolvimento e produção.

## Status da etapa atual

- FastAPI configurado
- API de health funcionando
- Firebase conectado via ADC local
- frontend básico pronto para visualizar o status da aplicação
