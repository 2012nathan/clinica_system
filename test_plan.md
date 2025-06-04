# Plano de Testes do Sistema de Gerenciamento da Clínica

## 1. Testes do Painel Administrativo

### 1.1 Cadastro e Gerenciamento de Profissionais
- [ ] Cadastrar novo profissional com todos os dados obrigatórios
- [ ] Editar dados de um profissional existente
- [ ] Ativar/desativar profissional
- [ ] Validar restrições de campos obrigatórios
- [ ] Verificar upload de foto de perfil e assinatura digital

### 1.2 Gerenciamento de Especialidades
- [ ] Cadastrar nova especialidade
- [ ] Editar especialidade existente
- [ ] Excluir especialidade (apenas quando não há profissionais vinculados)
- [ ] Validar restrições de exclusão

### 1.3 Configuração de Disponibilidade
- [ ] Adicionar disponibilidade para um profissional
- [ ] Editar disponibilidade existente
- [ ] Excluir disponibilidade
- [ ] Validar conflitos de horários

### 1.4 Gerenciamento de Assistentes
- [ ] Cadastrar novo assistente
- [ ] Editar dados de um assistente existente
- [ ] Ativar/desativar assistente
- [ ] Validar restrições de campos obrigatórios

## 2. Testes do Dashboard para Médicos

### 2.1 Busca de Pacientes
- [ ] Buscar paciente por CPF válido
- [ ] Validar mensagem de erro para CPF inexistente
- [ ] Verificar exibição correta dos dados do paciente

### 2.2 Upload de Documentos
- [ ] Fazer upload de receita médica em PDF
- [ ] Fazer upload de atestado médico em PDF
- [ ] Validar restrições de formato e tamanho de arquivo
- [ ] Verificar se o documento fica disponível para o paciente

### 2.3 Cartão Gestante
- [ ] Criar novo cartão gestante
- [ ] Editar dados do cartão gestante
- [ ] Registrar consulta pré-natal
- [ ] Solicitar exame pré-natal
- [ ] Registrar medicação com lembrete
- [ ] Validar cálculo automático da data provável do parto

## 3. Testes do Painel para Pacientes

### 3.1 Primeiro Acesso e Autenticação
- [ ] Solicitar primeiro acesso com CPF válido
- [ ] Verificar envio de senha provisória por e-mail
- [ ] Verificar envio de senha provisória por WhatsApp
- [ ] Fazer login com senha provisória
- [ ] Validar redirecionamento para troca de senha obrigatória
- [ ] Trocar senha provisória por senha permanente
- [ ] Validar requisitos de segurança da nova senha

### 3.2 Visualização de Dados e Documentos
- [ ] Verificar exibição correta dos dados pessoais
- [ ] Confirmar que campos sensíveis não podem ser editados
- [ ] Visualizar receitas médicas
- [ ] Visualizar atestados médicos
- [ ] Visualizar laudos de exames
- [ ] Verificar atualização de status ao visualizar documentos

### 3.3 Cartão Gestante
- [ ] Visualizar dados do cartão gestante
- [ ] Verificar histórico de consultas pré-natal
- [ ] Visualizar exames solicitados
- [ ] Verificar medicações prescritas e lembretes

## 4. Testes do Sistema de Gestão de Laudos

### 4.1 Integração com Orthanc
- [ ] Buscar estudos disponíveis no Orthanc
- [ ] Visualizar detalhes de um estudo
- [ ] Abrir visualizador DICOM para um estudo
- [ ] Cadastrar estudo do Orthanc no sistema

### 4.2 Gerenciamento de Laudos
- [ ] Anexar laudo em PDF a um exame
- [ ] Verificar atualização de status do exame para "laudado"
- [ ] Remover laudo anexado incorretamente
- [ ] Verificar retorno do status para "pendente" após remoção

### 4.3 Busca e Filtros
- [ ] Buscar exames por status (pendente/laudado)
- [ ] Buscar exames por paciente (CPF)
- [ ] Verificar exibição correta dos resultados filtrados

## 5. Testes de Segurança e Permissões

### 5.1 Controle de Acesso
- [ ] Verificar restrição de acesso a rotas administrativas
- [ ] Verificar restrição de acesso a rotas de médicos
- [ ] Verificar restrição de acesso a rotas de assistentes
- [ ] Verificar restrição de acesso a rotas de pacientes
- [ ] Testar redirecionamento após tentativa de acesso não autorizado

### 5.2 Segurança de Dados
- [ ] Validar armazenamento seguro de senhas (hash)
- [ ] Verificar expiração de senhas provisórias
- [ ] Testar proteção contra acesso a documentos de outros pacientes
- [ ] Validar proteção contra manipulação de IDs nas URLs

## 6. Testes de Interface e Usabilidade

### 6.1 Responsividade
- [ ] Testar visualização em desktop
- [ ] Testar visualização em tablet
- [ ] Testar visualização em smartphone
- [ ] Verificar adaptação de elementos de interface

### 6.2 Feedback ao Usuário
- [ ] Verificar exibição de mensagens de sucesso
- [ ] Verificar exibição de mensagens de erro
- [ ] Testar indicadores de carregamento
- [ ] Validar clareza das mensagens de orientação

## 7. Testes de Integração

### 7.1 Integração com Shosp
- [ ] Verificar busca de pacientes no Shosp por CPF
- [ ] Testar criação de usuário com dados do Shosp
- [ ] Validar tratamento de erros na comunicação com a API

### 7.2 Integração com Orthanc
- [ ] Testar conexão com servidor Orthanc
- [ ] Verificar listagem de estudos DICOM
- [ ] Testar abertura do visualizador DICOM
- [ ] Validar tratamento de erros na comunicação com a API

### 7.3 Envio de Notificações
- [ ] Testar envio de e-mail com senha provisória
- [ ] Testar envio de WhatsApp com senha provisória
- [ ] Verificar tratamento de erros no envio de notificações
