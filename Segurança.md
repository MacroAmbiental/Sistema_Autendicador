# Segurança — Autenticador Macroambiental
O desenvolvimento deverá seguir os seguintes princípios.
### 2.1. Princípio do menor privilégio
Cada usuário, serviço ou aplicação deverá possuir somente as permissões necessárias para executar sua função.
Exemplos:
- usuários de consulta não poderão alterar documentos;
- autenticadores não poderão administrar usuários;
- usuários administrativos terão permissões específicas;
- sistemas integradores terão credenciais próprias;
- a aplicação backend terá somente as permissões de infraestrutura necessárias.
Não deverão existir permissões administrativas amplas sem necessidade.
---
## 2.2. Negação por padrão
Quando uma operação não estiver explicitamente autorizada, ela deverá ser negada.
As regras de segurança do Firebase deverão seguir preferencialmente o conceito:
```text
Negar tudo
↓
Liberar somente os casos necessários
```
Nunca deverá ser utilizado em produção um modelo equivalente a:
```text
allow read, write: if true;
```
---
# 3. Arquitetura de segurança
A arquitetura prevista é:
```text
USUÁRIO
   │
   ▼
FRONTEND
   │
   ├── Firebase Authentication
   │
   ▼
BACKEND PYTHON / FASTAPI
   │
   ├── autorização
   ├── validação
   ├── regras de negócio
   ├── auditoria
   ├── geração de hash
   └── validação de integridade
   │
   ├──────────────► Cloud Firestore
   │
   └──────────────► Cloud Storage
```
A aplicação não deverá confiar apenas no frontend.
Toda operação considerada crítica deverá ser novamente validada pelo backend.
---
# 4. Firebase Authentication
O Firebase Authentication será utilizado para identificar os usuários administrativos do sistema.
Cada usuário deverá possuir um identificador único.
Exemplo:
```text
Firebase UID
```
A aplicação deverá trabalhar futuramente com perfis e permissões.
Exemplo:
```text
ADMIN
AUTENTICADOR
AUDITOR
CONSULTA
INTEGRATION
```
A autenticação identifica o usuário.
A autorização define o que o usuário pode fazer.
Esses dois conceitos não deverão ser confundidos.
---
# 5. Controle de autorização
As permissões deverão ser verificadas antes da execução de operações críticas.
Exemplos de permissões:
```text
document:create
document:read
document:update
version:create
authentication:create
authentication:read
document:finalize
audit:read
user:create
user:update
user:disable
settings:manage
```
Um usuário autenticado não deverá automaticamente possuir acesso administrativo.
---
# 6. Segurança do Firestore
O Cloud Firestore será utilizado para armazenar principalmente:
- documentos;
- versões;
- autenticações;
- usuários;
- permissões;
- registros de auditoria;
- configurações;
- eventos.
As regras do Firestore deverão ser mantidas em:
```text
firestore.rules
```
As regras deverão ser versionadas juntamente com o código.
Toda mudança nas regras deverá ser revisada antes da implantação em produção.
---
# 7. Firebase Admin SDK
O backend Python utilizará o Firebase Admin SDK.
O Admin SDK possui privilégios de servidor e, portanto, deverá ser tratado como componente crítico da aplicação.
O backend não poderá assumir que as Firestore Security Rules irão proteger operações executadas pelo Admin SDK.
Consequentemente:
```text
Frontend
    ↓
Security Rules
Backend/Admin SDK
    ↓
IAM + regras da aplicação
```
Toda autorização realizada pelo backend deverá ser validada pelo próprio sistema antes de executar uma operação.
---
# 8. IAM
O acesso da infraestrutura Firebase/Google Cloud deverá utilizar Identity and Access Management — IAM.
Cada serviço deverá possuir apenas as permissões necessárias.
Evitar:
```text
Owner
Editor
Administrador global
```
quando permissões mais restritas forem suficientes.
Ambientes diferentes deverão utilizar identidades e configurações separadas.
Exemplo:
```text
development
staging
production
```
---
# 9. Segurança do Cloud Storage
Os arquivos PDF não deverão ser armazenados diretamente no Firestore.
Eles serão armazenados no Cloud Storage.
Estrutura prevista:
```text
documents/
   DOCUMENT_ID/
      versions/
         VERSION_ID/
            document.pdf
```
O Firestore armazenará somente informações como:
```text
storage_path
sha256
version_number
created_at
created_by
```
O acesso direto aos PDFs deverá ser controlado.
Arquivos privados não deverão ser disponibilizados por URLs públicas permanentes sem necessidade.
---
# 10. Integridade dos documentos
Cada versão de um documento deverá possuir um hash criptográfico.
Inicialmente será utilizado:
```text
SHA-256
```
O hash deverá ser calculado utilizando os bytes exatos do arquivo armazenado.
Exemplo:
```text
PDF
 ↓
SHA-256
 ↓
e98264c1...
```
Se qualquer conteúdo do arquivo for alterado:
```text
PDF alterado
 ↓
novo SHA-256
 ↓
hash diferente
```
O sistema poderá identificar que o arquivo apresentado não corresponde à versão registrada.
---
# 11. Versões dos documentos
Documentos autenticados não deverão ser simplesmente substituídos.
Toda alteração legítima deverá resultar em uma nova versão.
Exemplo:
```text
Documento
│
├── Versão 1
├── Versão 2
├── Versão 3
└── Versão 4
```
Cada versão deverá possuir no mínimo:
```text
id
document_id
version_number
sha256
storage_path
created_at
created_by
reason
previous_version_id
```
A versão anterior deverá continuar disponível para auditoria.
---
# 12. Registros imutáveis
Algumas informações deverão seguir preferencialmente o princípio de registros append-only.
Principalmente:
```text
versions
authentications
audit_logs
```
Significa que o sistema deverá preferir:
```text
CRIAR NOVO REGISTRO
```
em vez de:
```text
ALTERAR REGISTRO ANTIGO
```
Uma autenticação já concluída não deverá ser simplesmente sobrescrita.
Caso exista uma correção, deverá ser criado um novo evento informando a correção.
---
# 13. Cadeia de integridade
Além do hash individual do PDF, o projeto deverá possuir capacidade para implementar uma cadeia de integridade entre eventos.
Exemplo:
```text
Versão 1
   ↓
Hash 1
   ↓
Versão 2
   ↓
Hash 2 + referência Hash 1
   ↓
Versão 3
   ↓
Hash 3 + referência Hash 2
```
Uma implementação futura poderá possuir:
```text
previous_hash
event_hash
```
Isso permitirá detectar alterações retroativas na sequência dos registros.
---
# 14. QR Code
Cada documento deverá possuir somente um identificador público permanente.
O QR Code deverá identificar:
```text
DOCUMENTO
```
e não:
```text
AUTENTICAÇÃO
```
Exemplo:
```text
https://autenticador.macroambiental.com.br/validar/H8KMv7cP...
```
O QR Code não deverá conter diretamente:
- CPF;
- nome completo;
- senha;
- token de autenticação;
- identificador interno sequencial;
- credenciais;
- informações confidenciais;
- conteúdo completo do documento.
---
# 15. Identificador público
O identificador utilizado na URL pública deverá ser aleatório e imprevisível.
Não utilizar:
```text
/documento/1
/documento/2
/documento/3
```
Preferir algo semelhante a:
```text
H38fwKqZ81Xm7...
```
O identificador público não deverá revelar o ID interno utilizado pelo sistema.
O identificador público também não deverá ser considerado uma senha.
---
# 16. Página pública de validação
A página pública deverá exibir somente informações aprovadas para consulta externa.
Exemplos:
```text
Documento
Período
Status
Situação da integridade
Versão atual
Datas das autenticações
Status das autenticações
Autenticação final
```
Dados pessoais e informações internas não deverão ser exibidos automaticamente.
Informações confidenciais deverão permanecer em estruturas separadas.
---
# 17. Separação entre informações públicas e privadas
Não deverá existir um único documento Firestore contendo indiscriminadamente dados públicos e confidenciais quando ele puder ser lido diretamente por clientes.
Preferir estruturas separadas.
Exemplo:
```text
documents/{documentId}
    dados públicos/controlados
documents/{documentId}/private/security
    informações restritas
```
ou coleções equivalentes.
A separação reduz o risco de exposição acidental.
---
# 18. Auditoria
Todas as operações críticas deverão gerar registros de auditoria.
Exemplos:
```text
DOCUMENT_CREATED
VERSION_CREATED
DOCUMENT_AUTHENTICATED
DOCUMENT_FINALIZED
DOCUMENT_VALIDATED
LOGIN_SUCCESS
LOGIN_FAILED
PERMISSION_CHANGED
USER_CREATED
USER_DISABLED
```
Um evento de auditoria deverá possuir, quando aplicável:
```text
event_id
event_type
document_id
user_id
created_at
result
device_type
request_id
metadata
```
---
# 19. Auditoria das consultas SERTRAS
As consultas externas deverão ser registradas.
No mínimo:
```text
data e hora
documento consultado
tipo de dispositivo
resultado da validação
```
Informações adicionais poderão ser utilizadas quando forem justificadas para segurança e auditoria.
Os dados coletados deverão respeitar os princípios de necessidade e minimização.
---
# 20. Data e hora
Datas relacionadas à segurança deverão ser geradas preferencialmente no servidor.
Evitar confiar exclusivamente em datas enviadas pelo navegador.
No banco, utilizar preferencialmente timestamps em UTC.
Exemplo:
```text
2026-10-01T18:32:15Z
```
Na interface poderá ser apresentado:
```text
01/10/2026 15:32:15
```
utilizando o fuso horário configurado para a aplicação.
---
# 21. Credenciais
É expressamente proibido armazenar no código-fonte:
```text
senhas
tokens
API keys privadas
chaves criptográficas privadas
service account JSON
certificados privados
segredos de integração
```
Nunca fazer:
```python
PASSWORD = "minha_senha"
```
ou:
```python
FIREBASE_PRIVATE_KEY = "..."
```
---
# 22. Arquivo `.env`
Durante desenvolvimento local poderão ser utilizadas variáveis de ambiente.
Exemplo:
```text
.env
```
O `.env` deverá obrigatoriamente estar incluído no:
```text
.gitignore
```
Somente:
```text
.env.example
```
poderá ser enviado ao repositório.
O `.env.example` nunca deverá possuir credenciais reais.
---
# 23. Service Account
Caso uma chave JSON de Service Account seja utilizada durante desenvolvimento local, ela deverá permanecer exclusivamente na máquina do desenvolvedor.
Exemplo:
```text
backend/
   credentials/
      firebase-service-account.json
```
O diretório deverá estar no `.gitignore`.
Exemplo:
```gitignore
credentials/
*.pem
*.key
.env
```
Nenhuma chave privada deverá ser publicada no GitHub.
---
# 24. Credenciais em produção
Em produção, deverá ser preferido o uso das credenciais fornecidas pela própria infraestrutura Google Cloud/Firebase.
Evitar distribuir arquivos de Service Account manualmente entre servidores.
Segredos adicionais deverão utilizar mecanismos apropriados de gerenciamento de segredos.
---
# 25. HTTPS
Toda comunicação externa deverá utilizar:
```text
HTTPS/TLS
```
Não deverão existir endpoints de produção disponibilizados por HTTP sem criptografia.
Isso inclui:
```text
frontend → backend
backend → serviços externos
sistema de origem → autenticador
SERTRAS → autenticador
```
---
# 26. API de integração
O sistema de origem deverá possuir autenticação própria.
Não deverá reutilizar credenciais de usuários humanos para integrações automáticas.
Exemplo:
```text
Sistema de origem
      ↓
credencial da integração
      ↓
Backend Autenticador
```
A credencial deverá possuir permissões somente para os endpoints necessários.
---
# 27. Validação de entrada
Nenhum dado recebido por API deverá ser considerado confiável.
Todos os dados deverão ser validados.
Exemplo:
```text
tipos
tamanho
formato
campos obrigatórios
valores permitidos
permissões
estado atual do documento
```
A validação ocorrerá antes da execução da regra de negócio.
---
# 28. Upload seguro de PDF
Uploads deverão possuir validações.
No mínimo:
```text
tipo permitido
extensão
MIME type
tamanho máximo
estrutura esperada
hash
```
A extensão `.pdf` sozinha não deverá ser considerada prova de que o arquivo realmente é um PDF válido.
---
# 29. Nome dos arquivos
O nome enviado pelo usuário não deverá determinar diretamente o caminho de armazenamento.
Evitar:
```text
documents/{nome-enviado-pelo-usuario}
```
Preferir identificadores internos gerados pelo sistema.
Exemplo:
```text
documents/{document_id}/versions/{version_id}/document.pdf
```
Isso reduz riscos de manipulação de caminhos e colisões.
---
# 30. Proteção contra abuso
Endpoints públicos deverão possuir mecanismos contra abuso.
Poderão ser adotados:
```text
rate limiting
limites por origem
monitoramento
Firebase App Check
Cloud Armor
proteções do provedor
```
A escolha dependerá da forma final de implantação.
Nenhum endpoint público deverá permitir consumo ilimitado de recursos sem monitoramento.
---
# 31. Firebase App Check
O Firebase App Check poderá ser utilizado como camada adicional para ajudar a reduzir acessos originados de aplicações não autorizadas.
Ele deverá ser considerado uma camada adicional de defesa e não substitui:
```text
Authentication
Authorization
Security Rules
IAM
```
---
# 32. Logs
Logs deverão auxiliar diagnóstico e auditoria, mas não deverão registrar segredos.
Não registrar:
```text
senhas
tokens completos
private keys
Authorization headers
service account credentials
documentos confidenciais completos
```
Os logs deverão possuir informações suficientes para investigação sem expor desnecessariamente dados sensíveis.
---
# 33. Tratamento de erros
Erros retornados publicamente não deverão revelar detalhes internos da infraestrutura.
Evitar mensagens como:
```text
Erro PostgreSQL...
Chave privada localizada em...
Bucket interno...
Stack trace...
```
O usuário poderá receber:
```text
Não foi possível concluir a operação.
```
Enquanto os detalhes técnicos são registrados internamente.
---
# 34. Dependências
As dependências Python deverão ser mantidas atualizadas.
Bibliotecas não mantidas ou desconhecidas deverão ser evitadas.
As principais bibliotecas de segurança deverão ser consolidadas e amplamente utilizadas.
Exemplos previstos:
```text
firebase-admin
FastAPI
Pydantic
cryptography
pyHanko
```
Atualizações deverão ser testadas antes da implantação em produção.
---
# 35. Assinatura digital
O hash SHA-256 garante principalmente a verificação de integridade.
Ele não substitui necessariamente uma assinatura digital.
A arquitetura deverá permitir futuramente incorporar:
```text
assinatura criptográfica
certificado digital
PAdES
ICP-Brasil
```
sem exigir reconstrução completa do sistema.
---
# 36. Autenticação final
A autenticação final deverá possuir regras mais restritivas.
Somente usuários autorizados poderão finalizar um documento.
Antes da finalização, o backend deverá verificar:
```text
documento existente
versão atual
integridade
autenticações obrigatórias
permissão do usuário
estado do documento
```
Após finalizado, o documento não deverá aceitar modificações silenciosas.
---
# 37. Alterações após finalização
Caso seja necessário alterar um documento já finalizado:
```text
não substituir versão anterior
        ↓
criar nova versão
        ↓
registrar motivo
        ↓
registrar responsável
        ↓
registrar auditoria
        ↓
recalcular integridade
```
O histórico anterior deverá permanecer disponível.
---
# 38. Exclusão de registros
Documentos, versões, autenticações e eventos de auditoria não deverão ser excluídos livremente por usuários comuns.
Caso exista funcionalidade administrativa de exclusão, ela deverá seguir regras específicas, possuir autorização elevada e gerar auditoria.
Para registros críticos poderá ser adotado:
```text
soft delete
```
ou retenção imutável, conforme a política definida para o sistema.
---
# 39. Retenção
O período de retenção de:
```text
documentos
versões
autenticações
auditorias
```
ainda deverá ser definido.
Após definido, o sistema deverá garantir que a política seja aplicada de forma previsível e auditável.
Nenhum processo automático de exclusão deverá ser implementado antes da definição oficial da regra de retenção.
---
# 40. Backup e recuperação
Deverá existir estratégia de recuperação para dados críticos.
Devem ser considerados:
```text
Firestore
Cloud Storage
configurações
Security Rules
IAM
código-fonte
```