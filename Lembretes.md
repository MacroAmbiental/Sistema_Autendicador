# Checklist mínimo antes de produção

### 1. Antes de disponibilizar o autenticador oficialmente:

- [ ] Firestore Security Rules revisadas.
- [ ] Storage Security Rules revisadas.
- [ ] Nenhuma regra `allow read, write: if true`.
- [ ] Firebase Authentication configurado.
- [ ] Perfis e permissões configurados.
- [ ] IAM utilizando menor privilégio.
- [ ] Service Account não armazenada no repositório.
- [ ] `.env` ignorado pelo Git.
- [ ] HTTPS obrigatório.
- [ ] Upload de PDF validado.
- [ ] SHA-256 implementado.
- [ ] Versionamento implementado.
- [ ] Auditoria implementada.
- [ ] Proteção contra sobrescrita de autenticações.
- [ ] Proteção contra sobrescrita de versões.
- [ ] Validação de documentos implementada.
- [ ] Rate limiting/proteção contra abuso avaliada.
- [ ] Logs sem credenciais.
- [ ] Tratamento seguro de erros.
- [ ] Backup definido.
- [ ] Recuperação testada.
- [ ] Política de retenção definida.
- [ ] Testes automatizados executados.
- [ ] Ambiente de produção separado de desenvolvimento.
- [ ] Dependências revisadas.
- [ ] Monitoramento configurado.



### 2. Regras para commits

Nunca realizar commit contendo:

```text
.env
service-account.json
*.pem
*.key
credenciais
tokens
senhas
dados reais confidenciais
PDFs reais utilizados em produção
```

Antes de cada commit:

```bash
git status
```

deverá ser conferido.


### 3. Testes de segurança

O projeto deverá possuir testes para situações como:

```text
usuário não autenticado
usuário sem permissão
ID inexistente
arquivo alterado
hash divergente
tentativa de sobrescrever autenticação
tentativa de sobrescrever versão
documento finalizado
token inválido
PDF inválido
acesso a documento restrito
```

Security Rules também deverão ser testadas antes da publicação.


### 4. Ambientes separados

Sempre que possível existirão ambientes distintos.

```text
DEV
TEST
PROD
```

Credenciais e dados de produção não deverão ser utilizados em desenvolvimento local.

O ambiente de desenvolvimento nunca deverá ser utilizado como banco oficial de documentos autenticados.