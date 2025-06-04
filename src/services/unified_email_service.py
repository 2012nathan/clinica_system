from dotenv import load_dotenv
load_dotenv()
# src/services/unified_email_service.py
import os
import logging
from enum import Enum

class EmailProvider(Enum):
    SENDGRID = "sendgrid"
    GMAIL = "gmail"
    MAILGUN = "mailgun"
    RESEND = "resend"

class UnifiedEmailService:
    """
    Serviço unificado de email que pode usar diferentes provedores
    baseado nas configurações do ambiente
    """
    
    def __init__(self):
        self.provider = self._detect_provider()
        self.service = self._initialize_service()
        logging.info(f"✅ Serviço de email inicializado com {self.provider.value}")
    
    def _detect_provider(self):
        """Detecta qual provedor usar baseado nas variáveis de ambiente"""
        # Gmail API tem prioridade se tiver token válido
        if (os.getenv('GMAIL_SENDER_EMAIL') and 
            os.path.exists('credentials.json') and 
            os.path.exists('token.json')):
            return EmailProvider.GMAIL
        elif os.getenv('SENDGRID_API_KEY'):
            return EmailProvider.SENDGRID
        elif os.getenv('MAILGUN_API_KEY'):
            return EmailProvider.MAILGUN
        elif os.getenv('RESEND_API_KEY'):
            return EmailProvider.RESEND
        else:
            raise ValueError(
                "Nenhum provedor de email configurado. Configure uma das opções:\n"
                "- Gmail: GMAIL_SENDER_EMAIL + credentials.json + token.json\n"
                "- SendGrid: SENDGRID_API_KEY + SENDGRID_FROM_EMAIL\n"
                "- Mailgun: MAILGUN_API_KEY + MAILGUN_DOMAIN\n"
                "- Resend: RESEND_API_KEY + RESEND_FROM_EMAIL"
            )
    
    def _initialize_service(self):
        """Inicializa o serviço específico do provedor"""
        try:
            if self.provider == EmailProvider.GMAIL:
                from .gmail_no_browser_service import GmailNoBrowserService
                return GmailNoBrowserService()
            
            elif self.provider == EmailProvider.SENDGRID:
                from .sendgrid_service import SendGridEmailService
                return SendGridEmailService()
            
            elif self.provider == EmailProvider.MAILGUN:
                from .mailgun_service import MailgunEmailService
                return MailgunEmailService()
            
            elif self.provider == EmailProvider.RESEND:
                from .resend_service import ResendEmailService
                return ResendEmailService()
            
        except ImportError as e:
            logging.error(f"❌ Erro ao importar serviço {self.provider.value}: {e}")
            raise
        except Exception as e:
            logging.error(f"❌ Erro ao inicializar serviço {self.provider.value}: {e}")
            raise
    
    def enviar_email(self, destinatario, assunto, corpo_html, corpo_texto=None):
        """
        Envia email usando o provedor configurado
        
        Args:
            destinatario (str): Email do destinatário
            assunto (str): Assunto do email
            corpo_html (str): Corpo do email em HTML
            corpo_texto (str): Corpo do email em texto plano (opcional)
        
        Returns:
            dict: Resultado do envio
        """
        try:
            resultado = self.service.enviar_email(destinatario, assunto, corpo_html, corpo_texto)
            if resultado.get('sucesso'):
                logging.info(f"✅ Email enviado com sucesso via {self.provider.value} para {destinatario}")
            else:
                logging.error(f"❌ Falha ao enviar email via {self.provider.value}: {resultado.get('erro')}")
            return resultado
        
        except Exception as e:
            logging.error(f"❌ Erro no envio de email via {self.provider.value}: {str(e)}")
            return {
                'sucesso': False,
                'erro': f"Erro no envio via {self.provider.value}: {str(e)}"
            }
    
    def enviar_senha_provisoria(self, usuario, senha_provisoria):
        """
        Envia email com senha provisória
        
        Args:
            usuario: Objeto usuário
            senha_provisoria (str): Senha provisória gerada
        
        Returns:
            dict: Resultado do envio
        """
        try:
            return self.service.enviar_senha_provisoria(usuario, senha_provisoria)
        except Exception as e:
            logging.error(f"❌ Erro ao enviar senha provisória: {str(e)}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def enviar_recuperacao_senha(self, usuario, token_recuperacao):
        """
        Envia email de recuperação de senha
        
        Args:
            usuario: Objeto usuário
            token_recuperacao (str): Token para recuperação
        
        Returns:
            dict: Resultado do envio
        """
        try:
            return self.service.enviar_recuperacao_senha(usuario, token_recuperacao)
        except Exception as e:
            logging.error(f"❌ Erro ao enviar recuperação de senha: {str(e)}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def get_provider_info(self):
        """Retorna informações sobre o provedor atual"""
        return {
            'provider': self.provider.value,
            'configured': True,
            'service_class': self.service.__class__.__name__,
            'details': {
                'gmail_email': os.getenv('GMAIL_SENDER_EMAIL') if self.provider == EmailProvider.GMAIL else None,
                'credentials_exists': os.path.exists('credentials.json') if self.provider == EmailProvider.GMAIL else None,
                'token_exists': os.path.exists('token.json') if self.provider == EmailProvider.GMAIL else None
            }
        }

# ============================================
# INSTÂNCIA GLOBAL
# ============================================

# Tentar inicializar o serviço unificado
try:
    email_service = UnifiedEmailService()
    EMAIL_SERVICE_AVAILABLE = True
    EMAIL_PROVIDER = email_service.provider.value
    
    print(f"🎉 Serviço de email inicializado: {EMAIL_PROVIDER}")
    
except Exception as e:
    logging.warning(f"⚠️ Serviço de email não disponível: {str(e)}")
    email_service = None
    EMAIL_SERVICE_AVAILABLE = False
    EMAIL_PROVIDER = None
    
    print(f"❌ Serviço de email não disponível: {str(e)}")

# ============================================
# FUNÇÕES HELPER PARA USO NO MAIN.PY
# ============================================

def enviar_senha_provisoria(usuario, senha_provisoria):
    """
    Função helper para enviar senha provisória
    Para usar no main.py na linha onde você tem:
    from src.routes.auth import enviar_senha_provisoria
    """
    if not EMAIL_SERVICE_AVAILABLE:
        logging.error("❌ Serviço de email não está disponível")
        return {
            'sucesso': False,
            'erro': 'Serviço de email não configurado'
        }
    
    return email_service.enviar_senha_provisoria(usuario, senha_provisoria)

def enviar_recuperacao_senha(usuario, token_recuperacao):
    """
    Função helper para enviar email de recuperação de senha
    """
    if not EMAIL_SERVICE_AVAILABLE:
        logging.error("❌ Serviço de email não está disponível")
        return {
            'sucesso': False,
            'erro': 'Serviço de email não configurado'
        }
    
    return email_service.enviar_recuperacao_senha(usuario, token_recuperacao)

def get_email_service_info():
    """
    Retorna informações sobre o serviço de email configurado
    """
    if not EMAIL_SERVICE_AVAILABLE:
        return {
            'disponivel': False,
            'provider': None,
            'erro': 'Nenhum provedor configurado'
        }
    
    return {
        'disponivel': True,
        'provider': EMAIL_PROVIDER,
        'info': email_service.get_provider_info()
    }
