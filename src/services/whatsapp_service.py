# src/services/whatsapp_service.py
import os
import requests
import logging
from datetime import datetime

class WhatsAppService:
    """
    Serviço para envio de mensagens via WhatsApp
    Compatible com APIs como Twilio, Z-API, ChatAPI, etc.
    """
    
    def __init__(self):
        self.api_url = os.getenv('WHATSAPP_API_URL')
        self.api_token = os.getenv('WHATSAPP_API_TOKEN')
        self.api_type = os.getenv('WHATSAPP_API_TYPE', 'z-api')  # z-api, twilio, chatapi
        self.available = bool(self.api_url and self.api_token)
        
        if self.available:
            logging.info(f"✅ WhatsApp Service inicializado: {self.api_type}")
        else:
            logging.warning("⚠️ WhatsApp Service não configurado - WHATSAPP_API_URL e WHATSAPP_API_TOKEN necessários")
    
    def _format_phone_number(self, phone):
        """
        Formata número de telefone para WhatsApp
        Remove caracteres especiais e garante formato correto
        """
        if not phone:
            return None
        
        # Remove caracteres especiais
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Se começar com 0, remove
        if clean_phone.startswith('0'):
            clean_phone = clean_phone[1:]
        
        # Se não começar com 55 (Brasil), adiciona
        if not clean_phone.startswith('55'):
            clean_phone = '55' + clean_phone
        
        # Garante que tenha 13 dígitos (55 + DDD + 9dígitos) ou 12 (55 + DDD + 8dígitos)
        if len(clean_phone) == 12:  # Número fixo ou celular antigo
            return clean_phone
        elif len(clean_phone) == 13:  # Celular com 9
            return clean_phone
        elif len(clean_phone) == 11:  # DDD + número sem 55
            return '55' + clean_phone
        elif len(clean_phone) == 10:  # DDD + número fixo sem 55
            return '55' + clean_phone
        
        logging.warning(f"Número de telefone com formato inválido: {phone} -> {clean_phone}")
        return clean_phone if len(clean_phone) >= 10 else None
    
    def _prepare_z_api_message(self, phone, message):
        """Prepara mensagem para Z-API"""
        return {
            "phone": phone,
            "message": message
        }
    
    def _prepare_twilio_message(self, phone, message):
        """Prepara mensagem para Twilio"""
        return {
            "To": f"whatsapp:+{phone}",
            "From": f"whatsapp:{os.getenv('TWILIO_WHATSAPP_FROM')}",
            "Body": message
        }
    
    def _prepare_chatapi_message(self, phone, message):
        """Prepara mensagem para ChatAPI"""
        return {
            "chatId": f"{phone}@c.us",
            "body": message
        }
    
    def _get_headers(self):
        """Retorna headers baseado no tipo de API"""
        if self.api_type == 'z-api':
            return {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_token}'
            }
        elif self.api_type == 'twilio':
            import base64
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = self.api_token
            credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
            return {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {credentials}'
            }
        elif self.api_type == 'chatapi':
            return {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_token}'
            }
        else:
            return {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_token}'
            }
    
    def enviar_mensagem(self, telefone, mensagem):
        """
        Envia mensagem via WhatsApp
        
        Args:
            telefone (str): Número do WhatsApp
            mensagem (str): Mensagem a ser enviada
        
        Returns:
            dict: Resultado do envio
        """
        if not self.available:
            return {
                'sucesso': False,
                'erro': 'WhatsApp Service não configurado'
            }
        
        try:
            # Formatar número
            phone_formatted = self._format_phone_number(telefone)
            if not phone_formatted:
                return {
                    'sucesso': False,
                    'erro': f'Número de telefone inválido: {telefone}'
                }
            
            # Preparar dados baseado no tipo de API
            if self.api_type == 'z-api':
                data = self._prepare_z_api_message(phone_formatted, mensagem)
                url = f"{self.api_url}/send-text"
            elif self.api_type == 'twilio':
                data = self._prepare_twilio_message(phone_formatted, mensagem)
                url = f"{self.api_url}/Messages.json"
            elif self.api_type == 'chatapi':
                data = self._prepare_chatapi_message(phone_formatted, mensagem)
                url = f"{self.api_url}/sendMessage"
            else:
                # Default para Z-API
                data = self._prepare_z_api_message(phone_formatted, mensagem)
                url = f"{self.api_url}/send-text"
            
            # Enviar requisição
            headers = self._get_headers()
            
            if self.api_type == 'twilio':
                response = requests.post(url, data=data, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=data, headers=headers, timeout=10)
            
            # Processar resposta
            if response.status_code in [200, 201]:
                try:
                    response_data = response.json()
                    logging.info(f"✅ WhatsApp enviado para {phone_formatted}")
                    return {
                        'sucesso': True,
                        'telefone': phone_formatted,
                        'response_data': response_data
                    }
                except:
                    logging.info(f"✅ WhatsApp enviado para {phone_formatted} (sem JSON response)")
                    return {
                        'sucesso': True,
                        'telefone': phone_formatted,
                        'response_text': response.text
                    }
            else:
                logging.error(f"❌ Erro WhatsApp {response.status_code}: {response.text}")
                return {
                    'sucesso': False,
                    'erro': f'Erro HTTP {response.status_code}: {response.text}',
                    'telefone': phone_formatted
                }
        
        except requests.exceptions.Timeout:
            logging.error("❌ Timeout ao enviar WhatsApp")
            return {
                'sucesso': False,
                'erro': 'Timeout na requisição'
            }
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Erro de requisição WhatsApp: {str(e)}")
            return {
                'sucesso': False,
                'erro': f'Erro de conexão: {str(e)}'
            }
        except Exception as e:
            logging.error(f"❌ Erro inesperado WhatsApp: {str(e)}")
            return {
                'sucesso': False,
                'erro': f'Erro inesperado: {str(e)}'
            }
    
    def enviar_notificacao_resultado(self, paciente, tipo_exame, tipo_documento='resultado'):
        """
        Envia notificação específica para resultado de exame
        
        Args:
            paciente: Objeto paciente
            tipo_exame (str): Tipo do exame
            tipo_documento (str): 'resultado' ou 'laudo'
        
        Returns:
            dict: Resultado do envio
        """
        if not paciente or not paciente.usuario:
            return {
                'sucesso': False,
                'erro': 'Dados do paciente inválidos'
            }
        
        telefone = paciente.usuario.telefone
        if not telefone:
            return {
                'sucesso': False,
                'erro': 'Paciente não possui telefone cadastrado'
            }
        
        nome_paciente = paciente.usuario.nome_completo.split()[0]  # Primeiro nome
        
        if tipo_documento == 'laudo':
            mensagem = f"""🏥 *UltraClin* 

Olá, *{nome_paciente}*!

✅ Seu *laudo de {tipo_exame}* está pronto!

📋 Você pode visualizar o documento completo em nosso portal do paciente.

🔐 Acesse: https://ultraclin.com.br
📱 Ou baixe nosso app

❓ Dúvidas? Entre em contato:
📞 (96) 98114-4626

_Equipe UltraClin_ 💙"""
        else:
            mensagem = f"""🏥 *UltraClin* 

Olá, *{nome_paciente}*!

✅ Seu *resultado de {tipo_exame}* está disponível!

📊 Você pode acessar o resultado completo em nosso portal do paciente.

🔐 Acesse: https://ultraclin.com.br
📱 Ou baixe nosso app

❓ Dúvidas? Entre em contato:
📞 (96) 98114-4626

_Equipe UltraClin_ 💙"""
        
        return self.enviar_mensagem(telefone, mensagem)
    
    def testar_conexao(self):
        """
        Testa se a API WhatsApp está funcionando
        
        Returns:
            dict: Resultado do teste
        """
        if not self.available:
            return {
                'sucesso': False,
                'erro': 'WhatsApp Service não configurado'
            }
        
        try:
            # Endpoint de teste varia por API
            if self.api_type == 'z-api':
                test_url = f"{self.api_url}/status"
            elif self.api_type == 'twilio':
                test_url = f"{self.api_url.replace('/Messages.json', '')}"
            else:
                test_url = f"{self.api_url}/status"
            
            headers = self._get_headers()
            response = requests.get(test_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                return {
                    'sucesso': True,
                    'api_type': self.api_type,
                    'status': 'Conectado'
                }
            else:
                return {
                    'sucesso': False,
                    'erro': f'API retornou status {response.status_code}'
                }
        
        except Exception as e:
            return {
                'sucesso': False,
                'erro': f'Erro ao testar conexão: {str(e)}'
            }

# Instância global
try:
    whatsapp_service = WhatsAppService()
    WHATSAPP_AVAILABLE = whatsapp_service.available
except Exception as e:
    logging.error(f"❌ Erro ao inicializar WhatsApp Service: {str(e)}")
    whatsapp_service = None
    WHATSAPP_AVAILABLE = False
