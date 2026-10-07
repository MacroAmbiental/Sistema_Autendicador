# Requisitos do Sistema Autenticador Macroambiental


### **Requisitos Funcionais**

RF-001 – Consulta de documentos autenticados O sistema deverá permitir que usuários do SERTRAS consultem documentos autenticados por meio de um link direto ou QR Code.

RF-002 – Exibição de documentos autenticados Ao acessar o link ou QR Code, o sistema deverá apresentar o documento autenticado, incluindo seu status de validação e o respectivo arquivo PDF associado ao processo de assinatura.

RF-003 – Armazenamento e disponibilidade dos registros O sistema deverá manter disponíveis para consulta os registros de autenticação e os documentos assinados durante o período definido pela regra de retenção da plataforma.

RF-004 – Auditoria de consultas O sistema deverá registrar auditoria das consultas realizadas pelos usuários do SERTRAS, contendo no mínimo:

Data e hora da consulta (formato dd/MM/aaaa HH:mm:ss);
Tipo de dispositivo utilizado (Desktop ou Mobile);
Identificação do documento consultado;
Resultado da validação/autenticação.

RF-005 – Gestão administrativa O sistema deverá disponibilizar um perfil administrativo para gerenciamento do autenticador, permitindo:

Consultar registros de auditoria;
Visualizar histórico de consultas;
Gerenciar a geração e manutenção dos hashes de autenticação;
Monitorar a utilização do sistema.


### **Requisitos a Definir**

RD-001 – Tempo de retenção dos documentos Definir por quanto tempo os documentos e registros de autenticação permanecerão disponíveis para consulta pelo SERTRAS.

RD-002 – Forma de acesso Definir o modelo de acesso ao autenticador pelo SERTRAS:

Página pública;
Página privada com autenticação;
Acesso exclusivo via link;
Acesso via QR Code;
Outras formas de validação de identidade, se necessárias.

    RD-003 – Controle de acesso Definir se será necessária autenticação adicional para consulta dos documentos (login, senha, token, certificado digital, etc.).