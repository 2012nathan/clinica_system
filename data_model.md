# Modelo de Dados e Fluxos do Sistema Gerencial da Clínica

## 1. Entidades Principais

### 1.1 Usuário
- **Atributos**:
  - id (PK)
  - nome_completo
  - cpf (único)
  - data_nascimento
  - email
  - telefone
  - senha (hash)
  - tipo_perfil (enum: 'admin', 'medico', 'assistente', 'paciente')
  - ativo (boolean)
  - data_criacao
  - ultimo_acesso

### 1.2 Profissional
- **Atributos**:
  - id (PK)
  - usuario_id (FK -> Usuário)
  - especialidade_id (FK -> Especialidade)
  - registro_profissional (CRM, CRP, etc.)
  - biografia
  - foto_perfil
  - assinatura_digital (caminho para arquivo)

### 1.3 Especialidade
- **Atributos**:
  - id (PK)
  - nome
  - descricao

### 1.4 DisponibilidadeProfissional
- **Atributos**:
  - id (PK)
  - profissional_id (FK -> Profissional)
  - dia_semana (0-6, onde 0=domingo)
  - hora_inicio
  - hora_fim
  - intervalo_minutos (duração de cada consulta)
  - ativo (boolean)

### 1.5 Paciente
- **Atributos**:
  - id (PK)
  - usuario_id (FK -> Usuário)
  - cartao_sus
  - convenio
  - numero_convenio
  - observacoes

### 1.6 Agendamento
- **Atributos**:
  - id (PK)
  - paciente_id (FK -> Paciente)
  - profissional_id (FK -> Profissional)
  - data_hora_inicio
  - data_hora_fim
  - status (enum: 'agendado', 'confirmado', 'cancelado', 'realizado')
  - motivo_consulta
  - observacoes
  - data_criacao
  - data_atualizacao
  - notificacao_enviada (boolean)

### 1.7 Documento
- **Atributos**:
  - id (PK)
  - paciente_id (FK -> Paciente)
  - profissional_id (FK -> Profissional, null para laudos anexados por assistentes)
  - assistente_id (FK -> Usuário, null para documentos criados por médicos)
  - tipo (enum: 'receita', 'atestado', 'laudo', 'outro')
  - titulo
  - descricao
  - arquivo_caminho
  - data_criacao
  - data_atualizacao
  - status (enum: 'pendente', 'disponivel', 'visualizado')

### 1.8 ExameImagem
- **Atributos**:
  - id (PK)
  - paciente_id (FK -> Paciente)
  - tipo_exame
  - data_realizacao
  - orthanc_study_uid
  - descricao
  - laudo_id (FK -> Documento, null se não tiver laudo anexado)
  - status (enum: 'pendente_laudo', 'laudo_disponivel')

### 1.9 CartaoGestante
- **Atributos**:
  - id (PK)
  - paciente_id (FK -> Paciente)
  - data_ultima_menstruacao
  - data_provavel_parto
  - gestacoes_previas
  - partos_previos
  - abortos_previos
  - altura_cm
  - peso_inicial_kg
  - imc_inicial
  - grupo_sanguineo
  - fator_rh
  - data_criacao
  - data_atualizacao

### 1.10 ConsultaPreNatal
- **Atributos**:
  - id (PK)
  - cartao_gestante_id (FK -> CartaoGestante)
  - profissional_id (FK -> Profissional)
  - data_consulta
  - semanas_gestacao
  - peso_kg
  - pressao_arterial
  - altura_uterina_cm
  - bcf
  - movimentos_fetais (boolean)
  - edema (enum: 'ausente', '+', '++', '+++')
  - observacoes_medicas
  - observacoes_gestante

### 1.11 ExamePreNatal
- **Atributos**:
  - id (PK)
  - cartao_gestante_id (FK -> CartaoGestante)
  - tipo_exame
  - data_solicitacao
  - data_realizacao
  - resultado
  - documento_id (FK -> Documento, para laudos)
  - observacoes

### 1.12 MedicacaoGestante
- **Atributos**:
  - id (PK)
  - cartao_gestante_id (FK -> CartaoGestante)
  - nome_medicacao
  - dosagem
  - posologia
  - data_inicio
  - data_fim
  - motivo
  - lembrete_ativo (boolean)
  - horario_lembrete

## 2. Relacionamentos

- **Usuário -> Profissional**: Um usuário do tipo 'medico' pode ter um registro de profissional (1:1)
- **Usuário -> Paciente**: Um usuário do tipo 'paciente' tem um registro de paciente (1:1)
- **Profissional -> Especialidade**: Um profissional pertence a uma especialidade (N:1)
- **Profissional -> DisponibilidadeProfissional**: Um profissional pode ter múltiplas disponibilidades (1:N)
- **Paciente -> Agendamento**: Um paciente pode ter múltiplos agendamentos (1:N)
- **Profissional -> Agendamento**: Um profissional pode ter múltiplos agendamentos (1:N)
- **Paciente -> Documento**: Um paciente pode ter múltiplos documentos (1:N)
- **Profissional -> Documento**: Um profissional pode criar múltiplos documentos (1:N)
- **Paciente -> ExameImagem**: Um paciente pode ter múltiplos exames de imagem (1:N)
- **ExameImagem -> Documento**: Um exame pode ter um laudo associado (1:1)
- **Paciente -> CartaoGestante**: Uma paciente pode ter um cartão gestante (1:1)
- **CartaoGestante -> ConsultaPreNatal**: Um cartão gestante pode ter múltiplas consultas (1:N)
- **CartaoGestante -> ExamePreNatal**: Um cartão gestante pode ter múltiplos exames (1:N)
- **CartaoGestante -> MedicacaoGestante**: Um cartão gestante pode ter múltiplas medicações (1:N)

## 3. Fluxos de Acesso e Permissões

### 3.1 Perfil Administrador
- **Permissões**:
  - Cadastrar/editar/desativar todos os tipos de usuários
  - Cadastrar/editar/remover especialidades
  - Visualizar todos os agendamentos
  - Acesso a relatórios gerenciais
  - Configurar parâmetros do sistema

### 3.2 Perfil Médico/Profissional
- **Permissões**:
  - Visualizar/editar próprio perfil
  - Configurar disponibilidade de agenda
  - Visualizar agendamentos próprios
  - Buscar pacientes por CPF
  - Criar/visualizar receitas e atestados para seus pacientes
  - Preencher/atualizar cartão gestante de suas pacientes
  - Visualizar exames e laudos de seus pacientes

### 3.3 Perfil Assistente
- **Permissões**:
  - Visualizar/editar próprio perfil
  - Cadastrar/editar pacientes
  - Gerenciar agendamentos (criar, cancelar, remarcar)
  - Anexar laudos aos exames de imagem
  - Visualizar status de laudos (pendentes/enviados)
  - Remover/substituir laudos incorretos

### 3.4 Perfil Paciente
- **Permissões**:
  - Visualizar próprio perfil (sem poder alterar nome, CPF e data de nascimento)
  - Editar informações de contato
  - Solicitar agendamentos
  - Cancelar próprios agendamentos
  - Visualizar histórico de consultas
  - Acessar receitas, atestados e laudos próprios
  - Visualizar cartão gestante (se aplicável)

## 4. Fluxos Principais do Sistema

### 4.1 Fluxo de Cadastro de Profissional
1. Administrador acessa o módulo de cadastro de profissionais
2. Preenche dados pessoais, especialidade e registro profissional
3. Sistema cria conta de usuário com perfil 'medico'
4. Administrador configura disponibilidade do profissional
5. Sistema envia credenciais por email ao profissional

### 4.2 Fluxo de Agendamento
1. Paciente solicita agendamento via aplicativo
2. Sistema verifica disponibilidade do profissional
3. Paciente confirma data/hora
4. Sistema registra agendamento com status 'agendado'
5. Sistema envia email de confirmação para a clínica
6. Assistente confirma agendamento, alterando status para 'confirmado'
7. Sistema notifica paciente sobre confirmação

### 4.3 Fluxo de Atendimento Médico
1. Médico acessa dashboard e visualiza agenda do dia
2. Busca paciente por CPF
3. Acessa histórico e informações do paciente
4. Realiza atendimento
5. Registra informações no sistema (consulta pré-natal, se aplicável)
6. Gera receitas/atestados conforme necessário
7. Finaliza atendimento, alterando status para 'realizado'

### 4.4 Fluxo de Gestão de Laudos
1. Assistente acessa módulo de gestão de laudos
2. Visualiza lista de exames pendentes de laudo
3. Seleciona exame e visualiza imagens do Orthanc pelo StudyUID
4. Anexa arquivo PDF do laudo
5. Sistema associa laudo ao exame e altera status para 'laudo_disponivel'
6. Paciente recebe notificação sobre disponibilidade do laudo

### 4.5 Fluxo de Cartão Gestante
1. Médico identifica paciente gestante
2. Cria cartão gestante com informações iniciais
3. Registra consultas pré-natal sequenciais
4. Solicita exames específicos da gestação
5. Prescreve medicações com lembretes (ex: AAS 150mg)
6. Paciente acessa cartão gestante pelo aplicativo
7. Sistema envia lembretes de medicação conforme configurado

## 5. Integrações Externas

### 5.1 Integração com Email
- Envio de notificações de agendamento/cancelamento
- Envio de credenciais para novos usuários
- Alertas de novos documentos disponíveis

### 5.2 Integração com Orthanc
- Consulta de estudos DICOM por StudyUID
- Visualização de miniaturas de imagens
- Associação de laudos PDF aos estudos

## 6. Armazenamento de Arquivos
- Receitas e atestados: `/storage/documentos/[tipo]/[paciente_id]/[timestamp]_[nome_arquivo].pdf`
- Laudos: `/storage/laudos/[paciente_id]/[exame_id]_[timestamp].pdf`
- Fotos de perfil: `/storage/perfil/[usuario_id].[extensao]`
- Assinaturas digitais: `/storage/assinaturas/[profissional_id].[extensao]`

## 7. Considerações de Segurança
- Autenticação via JWT (JSON Web Token)
- Senhas armazenadas com hash bcrypt
- Controle de acesso baseado em perfis
- Logs de auditoria para ações críticas
- Timeout de sessão após inatividade
- HTTPS para todas as comunicações
- Validação de dados em frontend e backend
