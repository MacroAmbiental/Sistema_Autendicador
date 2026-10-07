
## Objetivo do sistema

O sistema terá como finalidade **autenticar e validar documentos PDF gerados por outro sistema**, garantindo que o documento não tenha sido alterado de forma indevida e mantendo um **histórico completo de todas as autenticações, alterações e versões realizadas**.

A segurança faz parte da arquitetura central do projeto.

Os principais objetivos são garantir:

- integridade dos documentos;
- autenticidade dos registros;
- rastreabilidade das operações;
- controle de acesso;
- confidencialidade das informações restritas;
- preservação do histórico;
- auditabilidade;
- proteção contra alterações não autorizadas;
- disponibilidade dos documentos;
- segurança das credenciais e chaves;
- proteção da interface pública de validação.


Um requisito fundamental do sistema é permitir que **um mesmo documento possua várias autenticações ao longo de seu ciclo de vida**, sem gerar um novo QR Code para cada autenticação.

### Exemplo de utilização

O sistema deverá atender ao seguinte cenário:

Existe um **documento semanal**, utilizado durante toda a semana.

Esse documento é preenchido e assinado diariamente por diferentes pessoas:

- Segunda-feira → preenchimento e assinatura do responsável pelo dia;
- Terça-feira → preenchimento e assinatura de outro responsável;
- Quarta-feira → preenchimento e assinatura de outro responsável;
- Quinta-feira → preenchimento e assinatura de outro responsável;
- Sexta-feira → preenchimento e assinatura de outro responsável;
- No final da semana → uma pessoa responsável realiza a autenticação/conferência final do documento.

Nesse cenário, **não deverão ser criados vários documentos independentes** e nem vários QR Codes.

O sistema deverá tratar todo o conjunto como **um único documento semanal**, possuindo um **identificador único e um único QR Code permanente**.

Cada assinatura/autenticação diária deverá ser registrada individualmente dentro desse documento.

Portanto:

**Documento semanal único**  
↓  
**Um único identificador**  
↓  
**Um único QR Code**  
↓  
**Várias autenticações vinculadas ao documento**  
↓  
**Uma autenticação por dia, quando aplicável**  
↓  
**Autenticação/conferência final no encerramento da semana**

Ao escanear o QR Code, o sistema deverá apresentar o documento e **todos os dias que já foram autenticados**, incluindo as respectivas informações de cada autenticação.

---

# Autenticações múltiplas dentro de um mesmo documento

O sistema deverá possuir o conceito de **autenticação por evento**, permitindo que um mesmo documento tenha várias autenticações.

Cada autenticação deverá ser registrada separadamente e vinculada ao documento principal.

Uma autenticação deverá possuir, no mínimo:

- Identificador único da autenticação;
- Identificador do documento ao qual pertence;
- Data de referência da autenticação;
- Data e hora em que a autenticação foi realizada;
- Usuário responsável pela autenticação;
- Identificação do responsável, quando disponível;
- Tipo da autenticação;
- Hash correspondente ao estado do documento naquele momento;
- Informações adicionais ou observações;
- Status da autenticação;
- Registro de auditoria;
- Informações sobre a versão do documento associada à autenticação.

### Exemplo

O documento semanal poderá possuir registros semelhantes a:

| Dia | Status | Responsável | Data/hora | Hash/Versão |
|---|---|---|---|---|
| Segunda | Autenticado | Usuário A | 01/10/2026 17:32 | Hash X |
| Terça | Autenticado | Usuário B | 02/10/2026 17:45 | Hash Y |
| Quarta | Autenticado | Usuário C | 03/10/2026 18:02 | Hash Z |
| Quinta | Pendente | — | — | — |
| Sexta | Pendente | — | — | — |
| Final | Pendente | — | — | — |

Posteriormente, quando as demais autenticações forem realizadas, o mesmo documento deverá ser atualizado.

**O QR Code continuará sendo o mesmo.**

---

# QR Code único por documento

O sistema deverá utilizar um **QR Code único por documento**, e não um QR Code diferente para cada autenticação.

O QR Code deverá conter preferencialmente apenas um **identificador público único ou uma URL de validação**, evitando colocar diretamente dentro do QR Code informações sensíveis ou grandes quantidades de dados.

Exemplo conceitual:

`https://autenticador.exemplo.com/validar/{identificador-publico}`

O identificador deverá ser suficientemente aleatório e não deverá expor informações internas ou sequenciais do banco de dados.

### Regra fundamental

Enquanto o documento continuar sendo o mesmo documento semanal, seu QR Code deverá permanecer o mesmo.

As novas autenticações serão registradas no banco de dados e vinculadas ao mesmo identificador.

Dessa forma:

**QR Code → Documento → Autenticações → Histórico → Versões**

e não:

**QR Code → Uma única assinatura**

---

# Validação do documento semanal

Ao escanear o QR Code, o usuário deverá ser direcionado para uma **tela pública de validação**.

Essa tela deverá apresentar claramente:

### Identificação do documento

- Identificador do documento;
- Tipo de documento;
- Período de referência;
- Data de criação;
- Status atual;
- Versão atual;
- Hash atual;
- QR Code/identificador de validação.

### Situação das autenticações

A tela deverá apresentar uma visão semelhante a:

**Autenticações do documento**

| Data | Situação | Responsável | Data/hora da autenticação |
|---|---|---|---|
| Segunda-feira | ✅ Autenticado | João | 01/10/2026 17:32 |
| Terça-feira | ✅ Autenticado | Maria | 02/10/2026 17:45 |
| Quarta-feira | ✅ Autenticado | Carlos | 03/10/2026 18:02 |
| Quinta-feira | ⏳ Pendente | — | — |
| Sexta-feira | ⏳ Pendente | — | — |
| Autenticação final | ⏳ Pendente | — | — |

O sistema deverá permitir identificar rapidamente:

- Quais dias já foram autenticados;
- Quais dias ainda estão pendentes;
- Quem realizou cada autenticação;
- Quando cada autenticação foi realizada;
- Qual versão do documento estava vigente;
- Qual hash estava associado à autenticação;
- Se existe alguma inconsistência;
- Se o documento foi alterado após alguma autenticação.

---

# Status geral do documento

O documento deverá possuir um status geral calculado pelo sistema.

Exemplos:

### 🟢 Documento válido

Todas as verificações de integridade foram aprovadas e as autenticações existentes são válidas.

### 🟡 Documento em andamento

O documento ainda possui autenticações pendentes.

Por exemplo:

> Documento semanal registrado. 3 de 5 dias autenticados.

### 🔴 Documento alterado

O arquivo apresentado não corresponde ao hash registrado para a versão correspondente ou apresenta alguma inconsistência de integridade.

### 🔴 Documento inválido

O identificador não existe, a assinatura/autenticação não é válida ou existem outras inconsistências que impeçam a comprovação da autenticidade.

### 🔵 Documento finalizado

Todas as autenticações previstas foram realizadas e a autenticação/conferência final foi concluída.

---

# Modelo de ciclo de vida do documento

O documento deverá possuir um ciclo de vida claramente definido.

Exemplo:

**CRIADO**  
↓  
**EM PREENCHIMENTO**  
↓  
**AUTENTICAÇÕES DIÁRIAS**  
↓  
**TODOS OS DIAS AUTENTICADOS**  
↓  
**AUTENTICAÇÃO FINAL**  
↓  
**FINALIZADO**

O sistema deverá impedir que uma autenticação já concluída seja simplesmente sobrescrita.

Qualquer correção deverá gerar um novo evento ou uma nova versão, preservando o registro anterior.

---

# Hash e integridade por autenticação

O sistema deverá utilizar **hash criptográfico forte**, preferencialmente SHA-256 ou algoritmo equivalente considerado seguro no momento da implementação.

O hash deverá ser calculado sobre o conteúdo relevante do documento.

Sempre que o documento sofrer uma alteração legítima, deverá ser criada uma nova versão.

Cada versão deverá possuir:

- Identificador da versão;
- Hash;
- Data e hora;
- Usuário ou sistema responsável;
- Motivo da alteração;
- Documento correspondente;
- Relação com a versão anterior.

Cada autenticação deverá apontar para a versão do documento que estava vigente no momento da autenticação.

Isso é importante para que seja possível responder:

> "Qual era exatamente o estado do documento quando essa pessoa realizou a autenticação?"

---

# Cadeia de integridade

As versões deverão formar uma cadeia de histórico.

Conceitualmente:

**Versão 1**  
Hash: H1  
↓  
**Versão 2**  
Hash: H2  
↓  
**Versão 3**  
Hash: H3  
↓  
**Versão 4**  
Hash: H4

Cada nova versão deverá preservar a referência à versão anterior.

Sempre que possível, deverá ser utilizada uma estrutura que dificulte alterações retroativas no histórico.

O sistema deverá ser capaz de detectar:

- Alteração do arquivo;
- Alteração de metadados;
- Exclusão indevida de uma autenticação;
- Alteração de uma autenticação;
- Alteração de uma versão;
- Alteração do responsável;
- Alteração da data/hora registrada;
- Inconsistência na cadeia de integridade.

---

# Autenticação versus versão do documento

O sistema deverá separar conceitualmente:

### Documento

Representa o documento semanal como uma entidade única.

### Versão

Representa uma determinada versão/conteúdo do arquivo.

### Autenticação

Representa um evento em que uma pessoa ou sistema confirmou/autenticou aquele documento ou determinado dia.

### Auditoria

Representa o registro das operações realizadas no sistema.

Essa separação é importante para permitir múltiplas autenticações no mesmo documento sem criar vários documentos independentes.

---

# Funcionamento da autenticação diária

Quando um responsável realizar a autenticação de determinado dia:

1. O sistema deverá identificar o documento semanal;
2. Identificar o dia que está sendo autenticado;
3. Identificar o usuário responsável;
4. Validar suas permissões;
5. Verificar a versão atual do documento;
6. Calcular/verificar o hash;
7. Registrar a autenticação;
8. Registrar data e hora;
9. Registrar a versão correspondente;
10. Registrar o hash correspondente;
11. Registrar o evento no log de auditoria;
12. Atualizar o status geral do documento.

O QR Code do documento **não deverá ser alterado**.

---

# Autenticação final

Após o preenchimento e autenticação de todos os dias previstos, o documento poderá passar por uma **autenticação final**.

A autenticação final deverá ser realizada por um usuário com permissão específica.

O sistema deverá registrar:

- Responsável pela autenticação final;
- Data e hora;
- Versão final;
- Hash final;
- Resultado da conferência;
- Observações;
- Identificador da autenticação final;
- Registro de auditoria.

Após a finalização, o sistema deverá possuir mecanismos para impedir alterações não autorizadas.

Qualquer alteração posterior deverá gerar uma nova versão e deixar o documento novamente sujeito às regras de validação definidas pelo sistema.

---

# Histórico apresentado na validação

A tela pública de validação deverá apresentar uma linha do tempo do documento.

Exemplo:

**Documento criado**  
01/10/2026 — Sistema de origem

↓  

**Segunda-feira autenticada**  
01/10/2026 17:32 — Usuário A

↓

**Terça-feira autenticada**  
02/10/2026 17:45 — Usuário B

↓

**Quarta-feira autenticada**  
03/10/2026 18:02 — Usuário C

↓

**Quinta-feira autenticada**  
04/10/2026 17:50 — Usuário D

↓

**Sexta-feira autenticada**  
05/10/2026 18:10 — Usuário E

↓

**Autenticação final**  
05/10/2026 19:00 — Usuário responsável

↓

**Documento finalizado**

---

# API de integração

O sistema autenticador deverá ser integrado ao sistema responsável pela geração dos documentos por meio de uma API segura.

A API deverá permitir, no mínimo:

- Criar um documento;
- Registrar uma nova versão;
- Consultar um documento;
- Registrar uma autenticação;
- Consultar autenticações;
- Consultar o histórico;
- Validar um documento;
- Finalizar um documento;
- Consultar o status de um documento.

A API deverá possuir autenticação própria e controle de autorização.

Deverá existir uma distinção clara entre:

- API utilizada pelo sistema gerador;
- API utilizada pelos usuários;
- API/endpoints públicos utilizados pela validação do QR Code.

---

# Banco de dados

O autenticador deverá possuir uma tela de configuração na qual seja possível selecionar/configurar o **banco de dados ou coleção** utilizado para armazenar os registros.

A arquitetura deverá permitir trabalhar com diferentes bancos de dados por meio de uma camada de abstração.

O sistema não deverá ficar fortemente acoplado a um único banco.

O modelo deverá contemplar, conceitualmente, entidades semelhantes a:

- Documentos;
- Versões;
- Autenticações;
- Usuários;
- Permissões;
- Auditoria;
- Chaves/credenciais;
- Configurações;
- Eventos.

Um documento poderá possuir **N versões e N autenticações**, sendo que cada autenticação deverá estar vinculada ao documento e à versão correspondente.

---

# Segurança

O projeto deverá priorizar segurança desde a arquitetura inicial.

Deverão ser utilizadas bibliotecas consolidadas para:

- Criptografia;
- Hashes;
- Autenticação;
- Autorização;
- Assinatura digital;
- Comunicação HTTPS/TLS;
- Geração de QR Code;
- Validação de PDF;
- Controle de acesso;
- Logs;
- Auditoria;
- Proteção de credenciais;
- Gerenciamento de chaves.

Credenciais, tokens e chaves criptográficas não deverão ser armazenados diretamente no código-fonte.

Deverão ser utilizadas variáveis de ambiente, secret managers ou mecanismos equivalentes.

---

# Assinatura digital

O sistema deverá avaliar a utilização de **assinatura digital criptográfica** além do hash.

O hash deverá ser utilizado para verificação de integridade.

Quando necessário, a assinatura digital deverá ser utilizada para proporcionar também:

- Autenticidade;
- Não repúdio;
- Identificação do signatário;
- Proteção contra alterações.

A arquitetura deverá permitir incorporar certificados digitais e mecanismos de assinatura posteriormente sem exigir uma reestruturação completa do sistema.

---

# QR Code e privacidade

O QR Code não deverá conter diretamente:

- Nome completo dos usuários;
- CPF;
- Dados sensíveis;
- Informações internas do banco;
- Senhas;
- Tokens de acesso;
- Dados completos do documento.

Deverá conter somente um identificador público seguro ou URL de validação.

O sistema deverá controlar cuidadosamente quais informações podem ser exibidas publicamente.

---

# Interface administrativa

O sistema deverá possuir uma interface web administrativa para usuários autorizados.

Deverá permitir:

- Cadastrar documentos;
- Consultar documentos;
- Visualizar versões;
- Visualizar autenticações;
- Visualizar histórico;
- Registrar/gerenciar autenticações;
- Finalizar documentos;
- Consultar auditoria;
- Gerenciar usuários;
- Gerenciar permissões;
- Configurar banco de dados;
- Configurar integração com APIs;
- Configurar parâmetros do sistema.

---

# Interface pública de validação

A interface pública deverá ser acessível através do QR Code.

O usuário não deverá precisar possuir uma conta para consultar a autenticidade pública do documento, salvo quando houver necessidade de informações restritas.

A página deverá ser simples e clara.

Deverá apresentar:

**Documento:** Documento semanal X  
**Período:** Semana XX  
**Status:** 🟢 Válido  
**Autenticações:** 5/5  
**Autenticação final:** Concluída

E abaixo:

**Histórico de autenticações**

- Segunda-feira — Autenticado — Responsável — Data/hora;
- Terça-feira — Autenticado — Responsável — Data/hora;
- Quarta-feira — Autenticado — Responsável — Data/hora;
- Quinta-feira — Autenticado — Responsável — Data/hora;
- Sexta-feira — Autenticado — Responsável — Data/hora;
- Autenticação final — Concluída — Responsável — Data/hora.

Também deverá existir uma seção para consulta das versões e da integridade do documento.

---

# Fluxo completo

O fluxo principal deverá funcionar da seguinte maneira:

**1. Sistema de origem gera o documento semanal**  
↓  
**2. Sistema autenticador recebe o documento pela API**  
↓  
**3. Sistema cria um identificador único para o documento**  
↓  
**4. Sistema calcula o hash da primeira versão**  
↓  
**5. Sistema registra o documento e sua primeira versão**  
↓  
**6. Sistema gera um QR Code único para o documento**  
↓  
**7. QR Code é incorporado ao documento**  
↓  
**8. Documento é disponibilizado para utilização durante a semana**  
↓  
**9. Responsável realiza a autenticação do primeiro dia**  
↓  
**10. Sistema registra a autenticação e a versão correspondente**  
↓  
**11. Responsável realiza a autenticação do segundo dia**  
↓  
**12. Sistema registra a segunda autenticação no mesmo documento**  
↓  
**13. Processo continua para os demais dias**  
↓  
**14. O mesmo QR Code continua sendo utilizado durante todo o processo**  
↓  
**15. Responsável realiza a autenticação final**  
↓  
**16. Sistema registra a autenticação final**  
↓  
**17. Documento é marcado como finalizado**  
↓  
**18. Usuário escaneia o QR Code**  
↓  
**19. Sistema localiza o documento pelo identificador único**  
↓  
**20. Sistema verifica a integridade e o histórico**  
↓  
**21. Sistema apresenta todas as autenticações realizadas**  
↓  
**22. Sistema apresenta as versões e respectivos hashes**  
↓  
**23. Sistema informa claramente se o documento é válido, inválido, alterado, pendente ou finalizado.**

---

# Requisito fundamental

O sistema deverá respeitar obrigatoriamente a seguinte regra:

> **Um documento semanal deve possuir um único identificador público e um único QR Code durante todo o seu ciclo de vida. Esse documento poderá possuir múltiplas autenticações, inclusive uma autenticação diferente para cada dia da semana e uma autenticação final. Todas essas autenticações deverão permanecer vinculadas ao mesmo documento e poderão ser consultadas através do mesmo QR Code.**

Portanto, **uma nova autenticação não deve criar um novo documento nem um novo QR Code**.

O QR Code identifica o **documento**, enquanto as autenticações identificam os **eventos de validação realizados ao longo do tempo**.

---

# Requisito de rastreabilidade

O sistema deverá permitir reconstruir todo o histórico do documento.

Deverá ser possível responder:

- Quando o documento foi criado?
- Quem o criou?
- Qual era seu hash original?
- Qual versão estava vigente em determinado dia?
- Quem autenticou cada dia?
- Quando cada autenticação foi realizada?
- Qual era o hash naquele momento?
- Houve alguma alteração depois da autenticação?
- Quem realizou a alteração?
- Qual foi o motivo?
- Qual é a versão atual?
- Qual é o hash atual?
- O documento está finalizado?
- Todas as autenticações previstas foram realizadas?
- A autenticação final foi realizada?
- O arquivo apresentado atualmente corresponde a alguma versão registrada?

---

# Arquitetura

A aplicação deverá ser desenvolvida de forma modular, separando pelo menos:

- **API de integração**;
- **Módulo de autenticação e autorização**;
- **Módulo de gerenciamento de documentos**;
- **Módulo de versões**;
- **Módulo de gerenciamento de autenticações**;
- **Módulo de geração e validação de hashes**;
- **Módulo de histórico e auditoria**;
- **Módulo de QR Code**;
- **Módulo de assinatura digital**;
- **Módulo de conexão com banco de dados**;
- **Interface web de administração**;
- **Interface pública de validação**.

A tecnologia deverá ser escolhida visando:

- Segurança;
- Escalabilidade;
- Desempenho;
- Manutenibilidade;
- Facilidade de testes;
- Facilidade de implantação;
- Separação de responsabilidades;
- Baixo acoplamento.

---

# Tecnologias

Como ponto de partida, deverá ser avaliada uma arquitetura baseada em:

- **Python**;
- **FastAPI** para API;
- **Pydantic** para validação de dados;
- **SQLAlchemy** para abstração de banco;
- **Alembic** para migrações;
- **PostgreSQL** como banco principal recomendado;
- **Cryptography** para operações criptográficas;
- **QRCode** ou biblioteca equivalente para geração de QR Codes;
- Biblioteca apropriada para leitura/validação e manipulação segura de PDFs;
- **JWT/OAuth2** ou mecanismo equivalente para autenticação;
- **HTTPS/TLS**;
- Sistema estruturado de logs e auditoria;
- Testes automatizados.

As escolhas tecnológicas deverão ser justificadas tecnicamente antes da implementação.

---

# Objetivo final

O objetivo é criar uma solução semelhante a um **cartório digital de documentos**, capaz de comprovar a autenticidade e integridade de documentos PDF, mantendo uma trilha de auditoria completa e confiável.

O sistema deverá tratar o documento como uma entidade única e permitir que ele receba **múltiplas autenticações ao longo do tempo**, preservando todo o histórico.

O **QR Code único** será a porta de entrada para a validação pública do documento.

Ao escanear o QR Code, qualquer pessoa autorizada a consultar as informações públicas deverá conseguir verificar:

**Qual é o documento → qual é seu status → quais dias foram autenticados → quem realizou cada autenticação → quando ocorreu → qual versão estava vigente → quais alterações ocorreram → qual é o hash correspondente → se o documento está íntegro → e se a autenticação final foi concluída.**

O sistema deverá ser projetado desde o início para que **nenhuma autenticação ou versão anterior seja simplesmente apagada ou sobrescrita**, garantindo rastreabilidade, integridade e auditoria completa.