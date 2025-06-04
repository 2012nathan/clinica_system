# src/services/notification_logger.py
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

class NotificationLogger:
    """
    Serviço para logging avançado de notificações
    Registra tentativas, sucessos, falhas e estatísticas
    """
    
    def __init__(self):
        self.logger = logging.getLogger('notification_logger')
        self.log_dir = Path('logs/notifications')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar handler específico para notificações
        self._setup_file_handler()
    
    def _setup_file_handler(self):
        """Configura handler de arquivo para logs de notificação"""
        log_file = self.log_dir / f'notifications_{datetime.now().strftime("%Y%m")}.log'
        
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_tentativa(self, tipo: str, canal: str, destinatario: str, 
                     paciente_nome: str, dados_exame: Dict[str, Any]) -> str:
        """
        Registra uma tentativa de envio de notificação
        
        Returns:
            str: ID único da tentativa para rastreamento
        """
        tentativa_id = f"{tipo}_{canal}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        log_entry = {
            'id': tentativa_id,
            'timestamp': datetime.now().isoformat(),
            'tipo': tipo,  # 'resultado' ou 'laudo'
            'canal': canal,  # 'email' ou 'whatsapp'
            'destinatario': destinatario,
            'paciente_nome': paciente_nome,
            'dados_exame': dados_exame,
            'status': 'tentativa',
            'evento': 'TENTATIVA_ENVIO'
        }
        
        self.logger.info(f"TENTATIVA | {json.dumps(log_entry, ensure_ascii=False)}")
        return tentativa_id
    
    def log_sucesso(self, tentativa_id: str, canal: str, destinatario: str, 
                   detalhes: Optional[Dict] = None):
        """Registra sucesso no envio"""
        log_entry = {
            'id': tentativa_id,
            'timestamp': datetime.now().isoformat(),
            'canal': canal,
            'destinatario': destinatario,
            'status': 'sucesso',
            'evento': 'ENVIO_SUCESSO',
            'detalhes': detalhes or {}
        }
        
        self.logger.info(f"SUCESSO | {json.dumps(log_entry, ensure_ascii=False)}")
    
    def log_falha(self, tentativa_id: str, canal: str, destinatario: str, 
                 erro: str, detalhes: Optional[Dict] = None):
        """Registra falha no envio"""
        log_entry = {
            'id': tentativa_id,
            'timestamp': datetime.now().isoformat(),
            'canal': canal,
            'destinatario': destinatario,
            'status': 'falha',
            'evento': 'ENVIO_FALHA',
            'erro': erro,
            'detalhes': detalhes or {}
        }
        
        self.logger.error(f"FALHA | {json.dumps(log_entry, ensure_ascii=False)}")
    
    def log_notificacao_completa(self, tipo: str, paciente_nome: str, 
                               paciente_cpf: str, tipo_exame: str,
                               resultados: Dict[str, Any]):
        """
        Registra resultado completo de uma notificação
        (sucesso/falha em todos os canais tentados)
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'tipo': tipo,
            'paciente_nome': paciente_nome,
            'paciente_cpf': paciente_cpf,
            'tipo_exame': tipo_exame,
            'resultados': resultados,
            'evento': 'NOTIFICACAO_COMPLETA'
        }
        
        status = 'SUCESSO_PARCIAL' if any(r.get('sucesso') for r in resultados.values()) else 'FALHA_TOTAL'
        if all(r.get('sucesso') for r in resultados.values()):
            status = 'SUCESSO_TOTAL'
        
        self.logger.info(f"{status} | {json.dumps(log_entry, ensure_ascii=False)}")
    
    def obter_estatisticas(self, dias: int = 7) -> Dict[str, Any]:
        """
        Obtém estatísticas de notificações dos últimos N dias
        """
        try:
            return self._calcular_estatisticas_dos_logs(dias)
        except Exception as e:
            self.logger.error(f"Erro ao calcular estatísticas: {str(e)}")
            return self._estatisticas_vazias()
    
    def _calcular_estatisticas_dos_logs(self, dias: int) -> Dict[str, Any]:
        """Calcula estatísticas analisando os arquivos de log"""
        data_limite = datetime.now() - timedelta(days=dias)
        
        stats = {
            'total_tentativas': 0,
            'sucessos': 0,
            'falhas': 0,
            'taxa_sucesso': 0,
            'por_canal': {
                'email': {'tentativas': 0, 'sucessos': 0, 'falhas': 0, 'taxa_sucesso': 0},
                'whatsapp': {'tentativas': 0, 'sucessos': 0, 'falhas': 0, 'taxa_sucesso': 0}
            },
            'por_tipo': {
                'resultado': {'tentativas': 0, 'sucessos': 0, 'falhas': 0, 'taxa_sucesso': 0},
                'laudo': {'tentativas': 0, 'sucessos': 0, 'falhas': 0, 'taxa_sucesso': 0}
            },
            'pacientes_unicos': set(),
            'ultimas_falhas': []
        }
        
        # Processar arquivos de log dos últimos meses
        for log_file in self._obter_arquivos_log_relevantes(dias):
            self._processar_arquivo_log(log_file, data_limite, stats)
        
        # Finalizar cálculos
        stats['pacientes_unicos'] = len(stats['pacientes_unicos'])
        
        # Calcular taxas de sucesso
        if stats['total_tentativas'] > 0:
            stats['taxa_sucesso'] = round((stats['sucessos'] / stats['total_tentativas']) * 100, 1)
        
        for canal in ['email', 'whatsapp']:
            canal_stats = stats['por_canal'][canal]
            if canal_stats['tentativas'] > 0:
                canal_stats['taxa_sucesso'] = round(
                    (canal_stats['sucessos'] / canal_stats['tentativas']) * 100, 1
                )
        
        for tipo in ['resultado', 'laudo']:
            tipo_stats = stats['por_tipo'][tipo]
            if tipo_stats['tentativas'] > 0:
                tipo_stats['taxa_sucesso'] = round(
                    (tipo_stats['sucessos'] / tipo_stats['tentativas']) * 100, 1
                )
        
        # Ordenar últimas falhas por data
        stats['ultimas_falhas'] = sorted(
            stats['ultimas_falhas'],
            key=lambda x: x['timestamp'],
            reverse=True
        )[:10]  # Últimas 10 falhas
        
        return stats
    
    def _obter_arquivos_log_relevantes(self, dias: int) -> List[Path]:
        """Obtém lista de arquivos de log relevantes para o período"""
        arquivos = []
        data_atual = datetime.now()
        
        # Verificar últimos 3 meses para cobrir o período solicitado
        for i in range(3):
            data_mes = data_atual - timedelta(days=i*30)
            nome_arquivo = f'notifications_{data_mes.strftime("%Y%m")}.log'
            arquivo_path = self.log_dir / nome_arquivo
            
            if arquivo_path.exists():
                arquivos.append(arquivo_path)
        
        return arquivos
    
    def _processar_arquivo_log(self, log_file: Path, data_limite: datetime, stats: Dict):
        """Processa um arquivo de log específico"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for linha in f:
                    try:
                        # Extrair timestamp e dados JSON da linha
                        if ' | ' not in linha:
                            continue
                        
                        partes = linha.strip().split(' | ', 2)
                        if len(partes) < 3:
                            continue
                        
                        timestamp_str = partes[0]
                        nivel = partes[1]
                        dados_json = partes[2]
                        
                        # Verificar se está no período desejado
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                            if timestamp < data_limite:
                                continue
                        except:
                            continue
                        
                        # Parse dos dados JSON
                        try:
                            if dados_json.startswith(('TENTATIVA |', 'SUCESSO |', 'FALHA |', 'SUCESSO_')):
                                tipo_evento, json_data = dados_json.split(' | ', 1)
                                dados = json.loads(json_data)
                            else:
                                continue
                        except (json.JSONDecodeError, ValueError):
                            continue
                        
                        # Processar evento
                        self._processar_evento_log(tipo_evento, dados, stats)
                        
                    except Exception as e:
                        continue  # Pular linhas problemáticas
                        
        except Exception as e:
            self.logger.error(f"Erro ao processar arquivo {log_file}: {str(e)}")
    
    def _processar_evento_log(self, tipo_evento: str, dados: Dict, stats: Dict):
        """Processa um evento específico do log"""
        if tipo_evento == 'TENTATIVA':
            stats['total_tentativas'] += 1
            
            canal = dados.get('canal', '')
            tipo = dados.get('tipo', '')
            
            if canal in stats['por_canal']:
                stats['por_canal'][canal]['tentativas'] += 1
            
            if tipo in stats['por_tipo']:
                stats['por_tipo'][tipo]['tentativas'] += 1
        
        elif tipo_evento == 'SUCESSO':
            stats['sucessos'] += 1
            
            canal = dados.get('canal', '')
            if canal in stats['por_canal']:
                stats['por_canal'][canal]['sucessos'] += 1
        
        elif tipo_evento == 'FALHA':
            stats['falhas'] += 1
            
            canal = dados.get('canal', '')
            if canal in stats['por_canal']:
                stats['por_canal'][canal]['falhas'] += 1
            
            # Adicionar às últimas falhas
            falha_info = {
                'timestamp': dados.get('timestamp', ''),
                'canal': canal,
                'erro': dados.get('erro', ''),
                'destinatario': dados.get('destinatario', ''),
                'tentativa_id': dados.get('id', '')
            }
            stats['ultimas_falhas'].append(falha_info)
        
        elif tipo_evento.startswith('SUCESSO_'):
            # Notificação completa
            paciente_cpf = dados.get('paciente_cpf', '')
            if paciente_cpf:
                stats['pacientes_unicos'].add(paciente_cpf)
            
            tipo = dados.get('tipo', '')
            resultados = dados.get('resultados', {})
            
            for canal, resultado in resultados.items():
                if canal in stats['por_canal'] and tipo in stats['por_tipo']:
                    if resultado.get('sucesso'):
                        stats['por_tipo'][tipo]['sucessos'] += 1
                    else:
                        stats['por_tipo'][tipo]['falhas'] += 1
    
    def _estatisticas_vazias(self) -> Dict[str, Any]:
        """Retorna estrutura de estatísticas vazia"""
        return {
            'total_tentativas': 0,
            'sucessos': 0,
            'falhas': 0,
            'taxa_sucesso': 0,
            'por_canal': {
                'email': {'tentativas': 0, 'sucessos': 0, 'falhas': 0, 'taxa_sucesso': 0},
                'whatsapp': {'tentativas': 0, 'sucessos': 0, 'falhas': 0, 'taxa_sucesso': 0}
            },
            'por_tipo': {
                'resultado': {'tentativas': 0, 'sucessos': 0, 'falhas': 0, 'taxa_sucesso': 0},
                'laudo': {'tentativas': 0, 'sucessos': 0, 'falhas': 0, 'taxa_sucesso': 0}
            },
            'pacientes_unicos': 0,
            'ultimas_falhas': []
        }
    
    def limpar_logs_antigos(self, dias_para_manter: int = 90):
        """
        Remove logs mais antigos que o período especificado
        """
        try:
            data_limite = datetime.now() - timedelta(days=dias_para_manter)
            removidos = 0
            
            for log_file in self.log_dir.glob('notifications_*.log'):
                try:
                    # Extrair data do nome do arquivo
                    nome = log_file.stem
                    if len(nome) >= 19:  # notifications_YYYYMM
                        ano_mes = nome[-6:]
                        ano = int(ano_mes[:4])
                        mes = int(ano_mes[4:])
                        
                        data_arquivo = datetime(ano, mes, 1)
                        
                        if data_arquivo < data_limite:
                            log_file.unlink()
                            removidos += 1
                            self.logger.info(f"Log removido: {log_file.name}")
                            
                except Exception as e:
                    self.logger.error(f"Erro ao processar arquivo {log_file}: {str(e)}")
            
            self.logger.info(f"Limpeza concluída: {removidos} arquivos removidos")
            return removidos
            
        except Exception as e:
            self.logger.error(f"Erro na limpeza de logs: {str(e)}")
            return 0
    
    def obter_logs_recentes(self, limite: int = 50) -> List[Dict]:
        """
        Obtém os logs mais recentes para exibição
        """
        try:
            logs = []
            arquivos_ordenados = sorted(
                self.log_dir.glob('notifications_*.log'),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            for log_file in arquivos_ordenados[:2]:  # Últimos 2 arquivos
                with open(log_file, 'r', encoding='utf-8') as f:
                    linhas = f.readlines()
                    
                    # Processar as últimas linhas
                    for linha in reversed(linhas[-limite:]):
                        try:
                            if ' | ' in linha:
                                partes = linha.strip().split(' | ', 2)
                                if len(partes) >= 3:
                                    timestamp_str = partes[0]
                                    nivel = partes[1]
                                    dados = partes[2]
                                    
                                    logs.append({
                                        'timestamp': timestamp_str,
                                        'nivel': nivel,
                                        'dados': dados
                                    })
                        except:
                            continue
                
                if len(logs) >= limite:
                    break
            
            return logs[:limite]
            
        except Exception as e:
            self.logger.error(f"Erro ao obter logs recentes: {str(e)}")
            return []

# Instância global
notification_logger = NotificationLogger()
