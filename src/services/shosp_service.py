# src/services/shosp_service.py - VERSÃO ATUALIZADA COM AGENDAMENTOS

import os
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path

class ShospService:
    def __init__(self):
        self.carregar_config()
        
    def carregar_config(self):
        """Carrega configurações das variáveis de ambiente"""
        self.headers = {
            "id": os.getenv('SHOSP_API_ID'),
            "x-api-key": os.getenv('SHOSP_API_KEY'),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # URLs da API
        base_url = os.getenv('SHOSP_API_URL')
        
        # URL para pacientes
        if '/cadastro/paciente' in base_url:
            self.url_paciente = base_url
        else:
            self.url_paciente = f"{base_url}/cadastro/paciente"
        
        # URL para agendamentos
        self.url_agendamentos = f"{base_url}/agenda/get/porpaciente"
            
        logging.info(f"SHOSP Service configurado - URL Paciente: {self.url_paciente}")
        logging.info(f"SHOSP Service configurado - URL Agendamentos: {self.url_agendamentos}")
    
    def buscar_paciente_por_cpf(self, cpf):
        """
        Busca paciente por CPF usando GET /cadastro/paciente
        """
        try:
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            
            if len(cpf_limpo) != 11:
                logging.error(f"CPF inválido: {cpf}")
                return None
            
            response = requests.get(
                self.url_paciente,
                headers=self.headers,
                params={"cpf": cpf_limpo},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ret') == '1' and data.get('dados'):
                    logging.info(f"Paciente encontrado para CPF: {cpf_limpo}")
                    return data['dados'][0] if isinstance(data['dados'], list) else data['dados']
                else:
                    logging.info(f"Paciente não encontrado para CPF: {cpf_limpo}")
                    return None
            else:
                logging.error(f"Erro SHOSP - Status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Erro ao buscar paciente no SHOSP: {str(e)}")
            return None
    
    def buscar_agendamentos_por_cpf(self, cpf, filtrar_excluidos=True):
        """
        Busca agendamentos por CPF usando GET /agenda/get/porpaciente
        
        Args:
            cpf (str): CPF do paciente
            filtrar_excluidos (bool): Se deve filtrar agendamentos já excluídos
            
        Returns:
            list: Lista de agendamentos encontrados
        """
        try:
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            
            if len(cpf_limpo) != 11:
                logging.error(f"CPF inválido para agendamentos: {cpf}")
                return []
            
            response = requests.get(
                self.url_agendamentos,
                headers=self.headers,
                params={"cpf": cpf_limpo},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ret') == '1' and data.get('dados'):
                    agendamentos = data['dados'] if isinstance(data['dados'], list) else [data['dados']]
                    
                    # Processar agendamentos
                    agendamentos_processados = []
                    for agendamento in agendamentos:
                        agendamento_processado = self._processar_agendamento(agendamento)
                        if agendamento_processado:
                            agendamentos_processados.append(agendamento_processado)
                    
                    # Filtrar excluídos se solicitado
                    if filtrar_excluidos:
                        agendamentos_processados = self._filtrar_agendamentos_excluidos(agendamentos_processados)
                    
                    logging.info(f"Encontrados {len(agendamentos_processados)} agendamentos para CPF: {cpf_limpo}")
                    return agendamentos_processados
                else:
                    logging.info(f"Nenhum agendamento encontrado para CPF: {cpf_limpo}")
                    return []
            else:
                logging.error(f"Erro ao buscar agendamentos SHOSP - Status {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            logging.error(f"Erro ao buscar agendamentos no SHOSP: {str(e)}")
            return []
    
    def _processar_agendamento(self, agendamento_raw):
        """
        Processa um agendamento bruto do SHOSP
        """
        try:
            # Extrair dados básicos
            agendamento_id = agendamento_raw.get('id') or agendamento_raw.get('agendamentoId')
            if not agendamento_id:
                return None
            
            # Dados do paciente
            paciente_nome = agendamento_raw.get('pacienteNome') or agendamento_raw.get('nomeCompleto', '')
            paciente_cpf = agendamento_raw.get('pacienteCpf') or agendamento_raw.get('cpf', '')
            
            # Dados do agendamento
            data_agendamento_str = agendamento_raw.get('dataAgendamento') or agendamento_raw.get('dataHora')
            if data_agendamento_str:
                try:
                    # Tentar diferentes formatos de data
                    for formato in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y']:
                        try:
                            data_agendamento = datetime.strptime(data_agendamento_str, formato)
                            break
                        except ValueError:
                            continue
                    else:
                        data_agendamento = datetime.now()  # Fallback
                except:
                    data_agendamento = datetime.now()
            else:
                data_agendamento = datetime.now()
            
            # Dados do prestador
            prestador_codigo = str(agendamento_raw.get('prestadorCodigo', ''))
            prestador_nome = agendamento_raw.get('prestadorNome', '')
            
            # Tipo de exame/agendamento
            tipo_agendamento = agendamento_raw.get('tipoExame') or agendamento_raw.get('procedimento') or agendamento_raw.get('especialidade', '')
            
            # Status do agendamento
            status = agendamento_raw.get('status', '').lower()
            
            # Determinar se é exame de imagem ou laboratório
            tipo_categoria = self._categorizar_tipo_exame(tipo_agendamento, prestador_codigo)
            
            # Verificar se é gravação
            is_gravacao = self._is_gravacao_us(tipo_agendamento)
            
            agendamento_processado = {
                'id': str(agendamento_id),
                'paciente_nome': paciente_nome,
                'paciente_cpf': ''.join(filter(str.isdigit, paciente_cpf)),
                'data_agendamento': data_agendamento,
                'data_agendamento_str': data_agendamento.strftime('%d/%m/%Y %H:%M'),
                'prestador_codigo': prestador_codigo,
                'prestador_nome': prestador_nome,
                'tipo_agendamento': tipo_agendamento,
                'status': status,
                'tipo_categoria': tipo_categoria,  # 'imagem', 'laboratorio', 'outro'
                'is_gravacao': is_gravacao,
                'pode_criar_exame': status == 'confirmado' and tipo_categoria in ['imagem', 'laboratorio'],
                'dados_raw': agendamento_raw  # Manter dados originais para debug
            }
            
            return agendamento_processado
            
        except Exception as e:
            logging.error(f"Erro ao processar agendamento: {str(e)}")
            return None
    
    def _categorizar_tipo_exame(self, tipo_exame, prestador_codigo):
        """
        Categoriza o tipo de exame baseado no nome e prestador
        """
        tipo_lower = tipo_exame.lower()
        
        # Código 3 = Laboratório
        if prestador_codigo == '3':
            return 'laboratorio'
        
        # Palavras-chave para exames de imagem
        palavras_imagem = [
            'ultrassom', 'ultrasom', 'us ', 'ecografia', 'eco',
            'tomografia', 'tc', 'ressonancia', 'rm', 'ressonância',
            'raio', 'rx', 'radiografia', 'mamografia', 'densitometria',
            'doppler', 'ecocardiograma', 'morfologico', 'morfológico',
            'translucencia', 'translucência', 'nucal', 'obstétrico',
            'obstetrico', 'pelvica', 'pélvica', 'abdome', 'abdominal',
            'tireoide', 'tireóide', 'prostata', 'próstata', 'renal',
            'vesicula', 'vesícula', 'biliar', 'mama', 'mamas',
            'gestacional', 'fetal', 'gravacao', 'gravação'
        ]
        
        # Verificar se contém palavras de imagem
        for palavra in palavras_imagem:
            if palavra in tipo_lower:
                return 'imagem'
        
        # Palavras-chave para laboratório
        palavras_lab = [
            'hemograma', 'glicemia', 'colesterol', 'triglicerideos',
            'urina', 'fezes', 'sangue', 'beta', 'hcg', 'tsh',
            'creatinina', 'ureia', 'acido', 'ácido', 'urico',
            'parasitologico', 'parasitológico', 'cultura',
            'antibiograma', 'eas', 'leucograma', 'plaquetas'
        ]
        
        for palavra in palavras_lab:
            if palavra in tipo_lower:
                return 'laboratorio'
        
        # Se não identificou, retorna 'outro'
        return 'outro'
    
    def _is_gravacao_us(self, tipo_exame):
        """
        Verifica se é uma gravação de ultrassom
        """
        tipo_lower = tipo_exame.lower()
        palavras_gravacao = ['gravacao', 'gravação', 'video', 'vídeo', 'record']
        
        return any(palavra in tipo_lower for palavra in palavras_gravacao)
    
    def _filtrar_agendamentos_excluidos(self, agendamentos):
        """
        Filtra agendamentos que já foram excluídos
        """
        try:
            # Importar aqui para evitar circular import
            from src.models.agendamento_exclusao import AgendamentoExclusao
            
            agendamentos_filtrados = []
            for agendamento in agendamentos:
                if not AgendamentoExclusao.is_excluido(agendamento['id']):
                    agendamentos_filtrados.append(agendamento)
                else:
                    logging.debug(f"Agendamento {agendamento['id']} foi filtrado (excluído)")
            
            return agendamentos_filtrados
            
        except Exception as e:
            logging.error(f"Erro ao filtrar agendamentos excluídos: {str(e)}")
            # Se houver erro, retorna todos os agendamentos
            return agendamentos
    
    def buscar_agendamentos_imagem_por_cpf(self, cpf):
        """
        Busca apenas agendamentos de exames de imagem confirmados
        """
        agendamentos = self.buscar_agendamentos_por_cpf(cpf)
        
        # Filtrar apenas exames de imagem confirmados
        agendamentos_imagem = [
            ag for ag in agendamentos 
            if ag['tipo_categoria'] == 'imagem' and ag['status'] == 'confirmado'
        ]
        
        return agendamentos_imagem
    
    def buscar_agendamentos_laboratorio_por_cpf(self, cpf):
        """
        Busca apenas agendamentos de exames de laboratório confirmados
        """
        agendamentos = self.buscar_agendamentos_por_cpf(cpf)
        
        # Filtrar apenas exames de laboratório confirmados
        agendamentos_lab = [
            ag for ag in agendamentos 
            if ag['tipo_categoria'] == 'laboratorio' and ag['status'] == 'confirmado'
        ]
        
        return agendamentos_lab
    
    def cadastrar_paciente(self, dados_paciente):
        """
        Cadastra novo paciente usando POST /cadastro/paciente
        """
        try:
            # Validações básicas - INCLUINDO SEXO
            required_fields = ['cpf', 'nome', 'email', 'dataNascimento', 'sexo']
            for field in required_fields:
                if not dados_paciente.get(field):
                    logging.error(f"Campo obrigatório ausente: {field}")
                    return None
            
            # Validar sexo
            if dados_paciente['sexo'].upper() not in ['M', 'F']:
                logging.error(f"Sexo deve ser 'M' ou 'F', recebido: {dados_paciente['sexo']}")
                return None
            
            # Limpar e formatar dados
            dados_limpos = {
                'cpf': ''.join(filter(str.isdigit, dados_paciente['cpf'])),
                'nome': dados_paciente['nome'].strip().upper(),
                'email': dados_paciente['email'].strip().lower(),
                'dataNascimento': dados_paciente['dataNascimento'],
                'sexo': dados_paciente['sexo'].upper()
            }
            
            # Campos opcionais
            campos_opcionais = ['telefone', 'celular', 'nomeMae', 'logradouro', 'numero', 'bairro', 'cep']
            for campo in campos_opcionais:
                if dados_paciente.get(campo):
                    dados_limpos[campo] = dados_paciente[campo]
            
            response = requests.post(
                self.url_paciente,
                headers=self.headers,
                json=dados_limpos,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('ret') == '1':
                    logging.info(f"Paciente cadastrado no SHOSP: {dados_limpos['cpf']}")
                    return data.get('dados')
                else:
                    erro_msg = data.get('msg', 'Erro desconhecido')
                    logging.error(f"SHOSP rejeitou cadastro: {erro_msg}")
                    return None
            else:
                logging.error(f"Erro ao cadastrar no SHOSP - Status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Erro ao cadastrar paciente no SHOSP: {str(e)}")
            return None
    
    def verificar_cpf_existe(self, cpf):
        """Verifica se CPF existe no SHOSP"""
        return self.buscar_paciente_por_cpf(cpf) is not None
    
    def buscar_ou_cadastrar_paciente(self, cpf, dados_cadastro=None):
        """
        Busca paciente, se não encontrar tenta cadastrar
        """
        # Primeiro busca
        paciente = self.buscar_paciente_por_cpf(cpf)
        
        if paciente:
            return paciente
        
        # Se não encontrou e tem dados para cadastro
        if dados_cadastro:
            dados_cadastro['cpf'] = cpf
            return self.cadastrar_paciente(dados_cadastro)
        
        return None

# Instância global
shosp_service = ShospService()

# Função de conveniência para verificar CPF (compatibilidade com código existente)
def verificar_cpf_shosp(cpf):
    """Função de compatibilidade - verifica se CPF existe no SHOSP"""
    return shosp_service.verificar_cpf_existe(cpf)
