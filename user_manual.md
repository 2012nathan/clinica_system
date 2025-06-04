# Manual do Usuário - Sistema de Gerenciamento da Clínica

## Introdução

Bem-vindo ao Sistema de Gerenciamento da Clínica, uma solução completa para gerenciamento de pacientes, agendamentos, documentos médicos e cartão gestante digital. Este manual fornece instruções detalhadas para todos os tipos de usuários do sistema.

## Acesso ao Sistema

O sistema está disponível através do seguinte endereço:
```
https://clinica.seudominio.com
```

Existem quatro tipos de perfis de usuário:
1. Administrador
2. Médico/Profissional de Saúde
3. Assistente
4. Paciente

## Perfil de Administrador

### Acesso
- **Usuário**: admin@clinica.com
- **Senha**: Fornecida separadamente por questões de segurança

### Funcionalidades

#### Gerenciamento de Profissionais
- Acesse "Profissionais" no menu lateral
- Clique em "Novo Profissional" para cadastrar médicos, psicólogos ou nutricionistas
- Preencha todos os dados obrigatórios, incluindo especialidade e registro profissional
- Para editar, clique no ícone de lápis ao lado do profissional
- Para desativar/ativar, use o botão correspondente na lista

#### Gerenciamento de Especialidades
- Acesse "Especialidades" no menu lateral
- Clique em "Nova Especialidade" para adicionar
- Preencha nome e descrição
- Especialidades com profissionais vinculados não podem ser excluídas

#### Configuração de Disponibilidade
- Na lista de profissionais, clique no ícone de calendário
- Adicione os dias e horários disponíveis para cada profissional
- Configure a duração padrão das consultas

#### Gerenciamento de Assistentes
- Acesse "Assistentes" no menu lateral
- Clique em "Novo Assistente" para cadastrar
- Preencha todos os dados obrigatórios
- Para editar, clique no ícone de lápis ao lado do assistente

## Perfil de Médico/Profissional

### Primeiro Acesso
- Use o CPF e a senha fornecidos pelo administrador
- Ao primeiro login, você será solicitado a trocar a senha

### Funcionalidades

#### Dashboard
- Visualize resumo de consultas agendadas, documentos emitidos e pacientes atendidos
- Acesse ações rápidas como busca de pacientes e visualização de agenda

#### Busca de Pacientes
- Clique em "Buscar Paciente" no menu lateral
- Digite o CPF do paciente (apenas números)
- O sistema exibirá os dados do paciente se encontrado

#### Emissão de Documentos
- Na página de detalhes do paciente, clique em "Nova Receita/Atestado"
- Selecione o tipo de documento (receita, atestado ou laudo)
- Preencha o título e descrição
- Faça upload do arquivo PDF assinado digitalmente
- Clique em "Salvar Documento"

#### Cartão Gestante
- Na página de detalhes da paciente, clique em "Criar Cartão Gestante" (ou "Cartão Gestante" se já existir)
- Preencha os dados iniciais da gestação
- Registre consultas pré-natal clicando em "Nova Consulta"
- Solicite exames clicando em "Novo Exame"
- Registre medicações clicando em "Nova Medicação"
- Configure lembretes para medicações ativando a opção correspondente

## Perfil de Assistente

### Primeiro Acesso
- Use o CPF e a senha fornecidos pelo administrador
- Ao primeiro login, você será solicitado a trocar a senha

### Funcionalidades

#### Dashboard
- Visualize resumo de exames pendentes e laudados
- Acesse ações rápidas como busca de exames e pacientes

#### Gestão de Laudos
- Acesse "Exames" no menu lateral para ver todos os exames
- Filtre por status (pendente/laudado)
- Clique em um exame para ver detalhes

#### Busca de Exames no Orthanc
- Clique em "Buscar Exames Orthanc" no menu lateral
- O sistema exibirá os estudos disponíveis no servidor Orthanc
- Clique em "Cadastrar" para um estudo não cadastrado
- Selecione o paciente correspondente e preencha os dados do exame

#### Anexar Laudos
- Na página de detalhes do exame, clique em "Anexar Laudo"
- Preencha o título e descrição
- Faça upload do arquivo PDF do laudo
- Clique em "Salvar Laudo"
- O status do exame será atualizado para "Laudado"

#### Remover Laudos
- Na página de detalhes do exame, clique em "Remover Laudo"
- Confirme a remoção
- O status do exame voltará para "Pendente"

#### Visualizar Imagens
- Na página de detalhes do exame, clique em "Visualizar Imagens"
- O sistema abrirá o visualizador DICOM do Orthanc

## Perfil de Paciente

### Primeiro Acesso
- Acesse a página de login e clique em "Primeiro Acesso"
- Digite seu CPF (apenas números)
- O sistema verificará se seu CPF está cadastrado no Shosp
- Se encontrado, uma senha provisória será enviada para seu e-mail e/ou WhatsApp
- Faça login com seu CPF e a senha provisória
- Você será solicitado a criar uma nova senha permanente

### Funcionalidades

#### Dashboard
- Visualize resumo de consultas agendadas e documentos disponíveis
- Acesse ações rápidas como visualização de documentos e cartão gestante

#### Meus Dados
- Visualize seus dados pessoais
- Note que nome, CPF e data de nascimento não podem ser alterados

#### Alterar Senha
- Acesse "Alterar Senha" no menu lateral
- Digite sua senha atual e a nova senha
- Confirme a nova senha
- Clique em "Alterar Senha"

#### Meus Documentos
- Acesse "Meus Documentos" no menu lateral
- Visualize receitas, atestados e laudos disponíveis
- Clique em "Visualizar" para abrir o documento

#### Cartão Gestante
- Acesse "Meu Cartão Gestante" no menu lateral (disponível apenas para pacientes do sexo feminino)
- Visualize dados da gestação, histórico de consultas, exames solicitados e medicações prescritas
- Configure lembretes para medicações

#### Meus Agendamentos
- Acesse "Meus Agendamentos" no menu lateral
- Visualize histórico de consultas e próximos agendamentos

## Suporte Técnico

Em caso de dúvidas ou problemas técnicos, entre em contato com o suporte:
- **E-mail**: suporte@clinica.com
- **Telefone**: (XX) XXXX-XXXX
- **Horário de atendimento**: Segunda a sexta, das 8h às 18h
