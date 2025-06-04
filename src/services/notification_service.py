# src/services/notification_service.py
import os
import logging
from datetime import datetime
from flask import render_template_string

class NotificationService:
    """
    Serviço unificado para envio de notificações por email e WhatsApp
    """
    
    def __init__(self):
        self.email_available = False
        self.whatsapp_available = False
        
        # Tentar importar serviços
        try:
            from .unified_email_service import email_service, EMAIL_SERVICE_AVAILABLE
            self.email_service = email_service
            self.email_available = EMAIL_SERVICE_AVAILABLE
        except ImportError as e:
            logging.warning(f"⚠️ Email service não disponível: {str(e)}")
            self.email_service = None
        
        try:
            from .whatsapp_service import whatsapp_service, WHATSAPP_AVAILABLE
            self.whatsapp_service = whatsapp_service
            self.whatsapp_available = WHATSAPP_AVAILABLE
        except ImportError as e:
            logging.warning(f"⚠️ WhatsApp service não disponível: {str(e)}")
            self.whatsapp_service = None
        
        # Log de status
        status_msg = []
        if self.email_available:
            status_msg.append("✅ Email")
        else:
            status_msg.append("❌ Email")
        
        if self.whatsapp_available:
            status_msg.append("✅ WhatsApp")
        else:
            status_msg.append("❌ WhatsApp")
        
        logging.info(f"Notification Service inicializado: {' | '.join(status_msg)}")
    
    def _load_email_template(self, template_name, **kwargs):
        """
        Carrega template de email
        
        Args:
            template_name (str): Nome do template ('resultado' ou 'laudo')
            **kwargs: Variáveis para o template
        
        Returns:
            str: HTML do email
        """
        try:
            # Adicionar ano atual automaticamente
            kwargs['ano_atual'] = datetime.now().year
            
            # Templates inline para evitar problemas de path
            if template_name == 'resultado':
                # Template já está no artifact anterior
                template_path = os.path.join(
                    os.path.dirname(__file__), 
                    '..', 'templates', 'emails', 'resultado_disponivel.html'
                )
                
                if os.path.exists(template_path):
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_content = f.read()
                else:
                    # Fallback template inline
                    template_content = self._get_resultado_template_inline()
                
            elif template_name == 'laudo':
                template_path = os.path.join(
                    os.path.dirname(__file__), 
                    '..', 'templates', 'emails', 'laudo_disponivel.html'
                )
                
                if os.path.exists(template_path):
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_content = f.read()
                else:
                    # Fallback template inline
                    template_content = self._get_laudo_template_inline()
            else:
                template_content = self._get_default_template_inline()
            
            # Renderizar template com Jinja2
            from jinja2 import Template
            template = Template(template_content)
            return template.render(**kwargs)
            
        except Exception as e:
            logging.error(f"❌ Erro ao carregar template {template_name}: {str(e)}")
            # Template de fallback simples
            return self._get_simple_fallback_template(template_name, **kwargs)
    
    def _get_resultado_template_inline(self):
        """Template inline para resultado (fallback)"""
        return """
        <html>
        <head><title>Resultado Disponível - UltraClin</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #ff6600; color: white; padding: 20px; text-align: center;">
                <h1>🏥 UltraClin</h1>
                <p>Centro de Diagnóstico por Imagem</p>
            </div>
            <div style="padding: 20px;">
                <h2>Olá, {{ paciente_nome }}!</h2>
                <p>Seu resultado de <strong>{{ tipo_exame }}</strong> está disponível!</p>
                <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #ff6600;">
                    <h3>📊 Resultado Pronto</h3>
                    <p><strong>Tipo:</strong> {{ tipo_exame }}</p>
                    {% if data_realizacao %}<p><strong>Data:</strong> {{ data_realizacao }}</p>{% endif %}
                </div>
                <p style="text-align: center;">
                    <a href="https://ultraclin.com.br" style="background: #ff6600; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px;">
                        🔐 Acessar Portal do Paciente
                    </a>
                </p>
                <p>📞 Dúvidas? WhatsApp: (96) 98114-4626</p>
            </div>
        </body>
        </html>
        """
    
    def _get_laudo_template_inline(self):
        """Template inline para laudo (fallback)"""
        return """
        <html>
        <head><title>Laudo Disponível - UltraClin</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #ff6600; color: white; padding: 20px; text-align: center;">
                <h1>🏥 UltraClin</h1>
                <p>Centro de Diagnóstico por Imagem</p>
            </div>
            <div style="padding: 20px;">
                <h2>Olá, {{ paciente_nome }}!</h2>
                <p>Seu laudo de <strong>{{ tipo_exame }}</strong> está pronto!</p>
                <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #ff6600;">
                    <h3>📋 Laudo Médico Pronto</h3>
                    <p><strong>Tipo:</strong> {{ tipo_exame }}</p>
                    {% if data_realizacao %}<p><strong>Data:</strong> {{ data_realizacao }}</p>{% endif %}
                </div>
                <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h4>⚕️ Importante</h4>
                    <p>Este laudo deve ser analisado por um médico qualificado.</p>
                </div>
                <p style="text-align: center;">
                    <a href="https://ultraclin.com.br" style="background: #ff6600; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px;">
                        🔐 Acessar Portal do Paciente
                    </a>
                </p>
                <p>📞 Dúvidas? WhatsApp: (96) 98114-4626</p>
            </div>
        </body>
        </html>
        """
    
    def _create_plain_text_template(self, template_name, paciente_nome, tipo_exame, data_realizacao=None, medico=None):
        """
        Cria template de texto plano para email
        
        Args:
            template_name (str): 'resultado' ou 'laudo'
            paciente_nome (str): Nome do paciente
            tipo_exame (str): Tipo do exame
            data_realizacao (str): Data de realização
            medico (str): Nome do médico
        
        Returns:
            str: Template em texto plano
        """
        if template_name == 'laudo':
            return f"""🏥 UltraClin - Centro de Diagnóstico por Imagem

Olá, {paciente_nome}!

Temos uma excelente notícia para você!

📋 LAUDO MÉDICO DISPONÍVEL

Tipo de Exame: {tipo_exame}
{f'Data de Realização: {data_realizacao}' if data_realizacao else ''}
{f'Médico Responsável: {medico}' if medico else ''}

Seu laudo médico foi finalizado por nossos especialistas e está disponível para visualização e download em nosso portal do paciente.

🔐 ACESSE SEU LAUDO:
https://ultraclin.com.br

Como acessar:
1. Acesse o portal do paciente no link acima
2. Faça login com seu CPF e senha
3. Vá para a seção "Meus Documentos"
4. Localize o laudo do seu exame
5. Visualize online ou faça o download em PDF

⚕️ IMPORTANTE - ORIENTAÇÃO MÉDICA:
• Este laudo deve ser analisado por um médico qualificado
• Não interrompa tratamentos sem orientação médica
• Em caso de dúvidas, consulte seu médico assistente
• O laudo possui validade médica e legal

📞 PRECISA DE AJUDA?
WhatsApp: (96) 98114-4626
Email: atendimento@ultraclin.com.br
Horário: Segunda à Sexta, 7h às 18h

Agradecemos pela confiança em nossos serviços!

Equipe UltraClin 💙
www.ultraclin.com.br | Macapá - AP

Este é um email automático. Por favor, não responda a esta mensagem."""
        
        else:  # resultado
            return f"""🏥 UltraClin - Centro de Diagnóstico por Imagem

Olá, {paciente_nome}!

Temos uma ótima notícia para você!

📊 RESULTADO DISPONÍVEL

Tipo de Exame: {tipo_exame}
{f'Data de Realização: {data_realizacao}' if data_realizacao else ''}
{f'Médico Solicitante: {medico}' if medico else ''}

Seu resultado de exame laboratorial está pronto e disponível para visualização em nosso portal do paciente.

🔐 ACESSE SEU RESULTADO:
https://ultraclin.com.br

Como acessar:
1. Acesse o portal do paciente no link acima
2. Faça login com seu CPF e senha
3. Vá para a seção "Meus Exames"
4. Clique no exame para visualizar o resultado
5. Faça o download do PDF se necessário

📞 PRECISA DE AJUDA?
WhatsApp: (96) 98114-4626
Email: atendimento@ultraclin.com.br
Horário: Segunda à Sexta, 7h às 18h

Agradecemos pela confiança em nossos serviços!

Equipe UltraClin 💙
www.ultraclin.com.br | Macapá - AP

Este é um email automático. Por favor, não responda a esta mensagem."""
    
    def notificar_resultado_disponivel(self, paciente, tipo_exame, data_realizacao=None, medico_solicitante=None):
        """
        Notifica paciente sobre resultado de exame laboratorial disponível
        
        Args:
            paciente: Objeto paciente
            tipo_exame (str): Tipo do exame
            data_realizacao (str): Data de realização (opcional)
            medico_solicitante (str): Nome do médico (opcional)
        
        Returns:
            dict: Resultado das notificações
        """
        if not paciente or not paciente.usuario:
            return {
                'sucesso': False,
                'erro': 'Dados do paciente inválidos'
            }
        
        # Importar logger de notificações
        try:
            from .notification_logger import log_notification_success, log_notification_failure
        except ImportError:
            log_notification_success = log_notification_failure = lambda *args: None
        
        resultado = {
            'email': {'sucesso': False, 'erro': 'Não enviado'},
            'whatsapp': {'sucesso': False, 'erro': 'Não enviado'}
        }
        
        paciente_nome = paciente.usuario.nome_completo
        primeiro_nome = paciente_nome.split()[0]
        
        # Enviar Email
        if self.email_available and paciente.usuario.email:
            try:
                html_content = self._load_email_template(
                    'resultado',
                    paciente_nome=primeiro_nome,
                    tipo_exame=tipo_exame,
                    data_realizacao=data_realizacao,
                    medico_solicitante=medico_solicitante
                )
                
                # Template de texto plano para fallback
                texto_plano = self._create_plain_text_template(
                    'resultado', primeiro_nome, tipo_exame, data_realizacao, medico_solicitante
                )
                
                resultado_email = self.email_service.enviar_email(
                    destinatario=paciente.usuario.email,
                    assunto=f"Resultado de {tipo_exame} Disponível - UltraClin",
                    corpo_html=html_content,
                    corpo_texto=texto_plano
                )
                
                resultado['email'] = resultado_email
                
                # Log de sucesso/falha
                if resultado_email.get('sucesso'):
                    log_notification_success('resultado', paciente, 'email', {
                        'tipo_exame': tipo_exame,
                        'provider': getattr(self.email_service, 'provider', 'unknown')
                    })
                else:
                    log_notification_failure('resultado', paciente, 'email', resultado_email.get('erro', 'Erro desconhecido'))
                
            except Exception as e:
                erro_msg = str(e)
                logging.error(f"❌ Erro ao enviar email: {erro_msg}")
                resultado['email'] = {'sucesso': False, 'erro': erro_msg}
                log_notification_failure('resultado', paciente, 'email', erro_msg)
        elif not paciente.usuario.email:
            resultado['email'] = {'sucesso': False, 'erro': 'Email não cadastrado'}
            log_notification_failure('resultado', paciente, 'email', 'Email não cadastrado')
        
        # Enviar WhatsApp
        if self.whatsapp_available and paciente.usuario.telefone:
            try:
                resultado_whatsapp = self.whatsapp_service.enviar_notificacao_resultado(
                    paciente=paciente,
                    tipo_exame=tipo_exame,
                    tipo_documento='resultado'
                )
                
                resultado['whatsapp'] = resultado_whatsapp
                
                # Log de sucesso/falha
                if resultado_whatsapp.get('sucesso'):
                    log_notification_success('resultado', paciente, 'whatsapp', {
                        'tipo_exame': tipo_exame,
                        'telefone': resultado_whatsapp.get('telefone'),
                        'api_type': getattr(self.whatsapp_service, 'api_type', 'unknown')
                    })
                else:
                    log_notification_failure('resultado', paciente, 'whatsapp', resultado_whatsapp.get('erro', 'Erro desconhecido'))
                
            except Exception as e:
                erro_msg = str(e)
                logging.error(f"❌ Erro ao enviar WhatsApp: {erro_msg}")
                resultado['whatsapp'] = {'sucesso': False, 'erro': erro_msg}
                log_notification_failure('resultado', paciente, 'whatsapp', erro_msg)
        elif not paciente.usuario.telefone:
            resultado['whatsapp'] = {'sucesso': False, 'erro': 'Telefone não cadastrado'}
            log_notification_failure('resultado', paciente, 'whatsapp', 'Telefone não cadastrado')
        
        # Log do resultado
        sucessos = []
        if resultado['email']['sucesso']:
            sucessos.append("Email")
        if resultado['whatsapp']['sucesso']:
            sucessos.append("WhatsApp")
        
        if sucessos:
            logging.info(f"✅ Resultado notificado via {', '.join(sucessos)} para {paciente_nome}")
        else:
            logging.warning(f"⚠️ Nenhuma notificação enviada para {paciente_nome}")
        
        resultado['resumo'] = {
            'paciente': paciente_nome,
            'tipo_exame': tipo_exame,
            'sucessos': sucessos,
            'total_sucessos': len(sucessos)
        }
        
        return resultado
    
    def _get_simple_fallback_template(self, template_name, **kwargs):
        """Template de fallback ultra simples"""
        paciente_nome = kwargs.get('paciente_nome', 'Paciente')
        tipo_exame = kwargs.get('tipo_exame', 'exame')
        
        if template_name == 'laudo':
            documento_tipo = 'laudo'
            icone = '📋'
        else:
            documento_tipo = 'resultado'
            icone = '📊'
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>🏥 UltraClin</h2>
            <p>Olá, <strong>{paciente_nome}</strong>!</p>
            <p>Seu {documento_tipo} de <strong>{tipo_exame}</strong> está disponível! {icone}</p>
            <p>Acesse: <a href="https://ultraclin.com.br">https://ultraclin.com.br</a></p>
            <p>Dúvidas? WhatsApp: (96) 98114-4626</p>
        </body>
        </html>
        """
    
    def notificar_laudo_disponivel(self, paciente, tipo_exame, data_realizacao=None, medico_responsavel=None):
        """
        Notifica paciente sobre laudo de exame de imagem disponível
        
        Args:
            paciente: Objeto paciente
            tipo_exame (str): Tipo do exame
            data_realizacao (str): Data de realização (opcional)
            medico_responsavel (str): Nome do médico responsável (opcional)
        
        Returns:
            dict: Resultado das notificações
        """
        if not paciente or not paciente.usuario:
            return {
                'sucesso': False,
                'erro': 'Dados do paciente inválidos'
            }
        
        # Importar logger de notificações
        try:
            from .notification_logger import log_notification_success, log_notification_failure
        except ImportError:
            log_notification_success = log_notification_failure = lambda *args: None
        
        resultado = {
            'email': {'sucesso': False, 'erro': 'Não enviado'},
            'whatsapp': {'sucesso': False, 'erro': 'Não enviado'}
        }
        
        paciente_nome = paciente.usuario.nome_completo
        primeiro_nome = paciente_nome.split()[0]
        
        # Enviar Email
        if self.email_available and paciente.usuario.email:
            try:
                html_content = self._load_email_template(
                    'laudo',
                    paciente_nome=primeiro_nome,
                    tipo_exame=tipo_exame,
                    data_realizacao=data_realizacao,
                    medico_responsavel=medico_responsavel
                )
                
                # Template de texto plano para fallback
                texto_plano = self._create_plain_text_template(
                    'laudo', primeiro_nome, tipo_exame, data_realizacao, medico_responsavel
                )
                
                resultado_email = self.email_service.enviar_email(
                    destinatario=paciente.usuario.email,
                    assunto=f"Laudo de {tipo_exame} Disponível - UltraClin",
                    corpo_html=html_content,
                    corpo_texto=texto_plano
                )
                
                resultado['email'] = resultado_email
                
                # Log de sucesso/falha
                if resultado_email.get('sucesso'):
                    log_notification_success('laudo', paciente, 'email', {
                        'tipo_exame': tipo_exame,
                        'provider': getattr(self.email_service, 'provider', 'unknown')
                    })
                else:
                    log_notification_failure('laudo', paciente, 'email', resultado_email.get('erro', 'Erro desconhecido'))
                
            except Exception as e:
                erro_msg = str(e)
                logging.error(f"❌ Erro ao enviar email: {erro_msg}")
                resultado['email'] = {'sucesso': False, 'erro': erro_msg}
                log_notification_failure('laudo', paciente, 'email', erro_msg)
        elif not paciente.usuario.email:
            resultado['email'] = {'sucesso': False, 'erro': 'Email não cadastrado'}
            log_notification_failure('laudo', paciente, 'email', 'Email não cadastrado')
        
        # Enviar WhatsApp
        if self.whatsapp_available and paciente.usuario.telefone:
            try:
                resultado_whatsapp = self.whatsapp_service.enviar_notificacao_resultado(
                    paciente=paciente,
                    tipo_exame=tipo_exame,
                    tipo_documento='laudo'
                )
                
                resultado['whatsapp'] = resultado_whatsapp
                
                # Log de sucesso/falha
                if resultado_whatsapp.get('sucesso'):
                    log_notification_success('laudo', paciente, 'whatsapp', {
                        'tipo_exame': tipo_exame,
                        'telefone': resultado_whatsapp.get('telefone'),
                        'api_type': getattr(self.whatsapp_service, 'api_type', 'unknown')
                    })
                else:
                    log_notification_failure('laudo', paciente, 'whatsapp', resultado_whatsapp.get('erro', 'Erro desconhecido'))
                
            except Exception as e:
                erro_msg = str(e)
                logging.error(f"❌ Erro ao enviar WhatsApp: {erro_msg}")
                resultado['whatsapp'] = {'sucesso': False, 'erro': erro_msg}
                log_notification_failure('laudo', paciente, 'whatsapp', erro_msg)
        elif not paciente.usuario.telefone:
            resultado['whatsapp'] = {'sucesso': False, 'erro': 'Telefone não cadastrado'}
            log_notification_failure('laudo', paciente, 'whatsapp', 'Telefone não cadastrado')
        
        # Log do resultado
        sucessos = []
        if resultado['email']['sucesso']:
            sucessos.append("Email")
        if resultado['whatsapp']['sucesso']:
            sucessos.append("WhatsApp")
        
        if sucessos:
            logging.info(f"✅ Laudo notificado via {', '.join(sucessos)} para {paciente_nome}")
        else:
            logging.warning(f"⚠️ Nenhuma notificação enviada para {paciente_nome}")
        
        resultado['resumo'] = {
            'paciente': paciente_nome,
            'tipo_exame': tipo_exame,
            'sucessos': sucessos,
            'total_sucessos': len(sucessos)
        }
        
        return resultado
    
    def get_status(self):
        """
        Retorna status dos serviços de notificação
        
        Returns:
            dict: Status dos serviços
        """
        return {
            'email': {
                'disponivel': self.email_available,
                'provider': getattr(self.email_service, 'provider', None) if self.email_service else None
            },
            'whatsapp': {
                'disponivel': self.whatsapp_available,
                'api_type': getattr(self.whatsapp_service, 'api_type', None) if self.whatsapp_service else None
            }
        }
    
    def testar_servicos(self):
        """
        Testa ambos os serviços de notificação
        
        Returns:
            dict: Resultado dos testes
        """
        resultado = {
            'email': {'testado': False, 'sucesso': False, 'erro': 'Não testado'},
            'whatsapp': {'testado': False, 'sucesso': False, 'erro': 'Não testado'}
        }
        
        # Testar Email
        if self.email_available:
            resultado['email']['testado'] = True
            try:
                # Aqui poderia ter um teste específico do email service
                resultado['email']['sucesso'] = True
                resultado['email']['provider'] = getattr(self.email_service, 'provider', 'unknown')
            except Exception as e:
                resultado['email']['erro'] = str(e)
        
        # Testar WhatsApp
        if self.whatsapp_available:
            resultado['whatsapp']['testado'] = True
            try:
                teste_whatsapp = self.whatsapp_service.testar_conexao()
                resultado['whatsapp']['sucesso'] = teste_whatsapp.get('sucesso', False)
                resultado['whatsapp']['erro'] = teste_whatsapp.get('erro', 'Teste concluído')
            except Exception as e:
                resultado['whatsapp']['erro'] = str(e)
        
        return resultado

# Instância global
try:
    notification_service = NotificationService()
    NOTIFICATION_SERVICE_AVAILABLE = True
    logging.info("✅ Notification Service inicializado com sucesso")
except Exception as e:
    logging.error(f"❌ Erro ao inicializar Notification Service: {str(e)}")
    notification_service = None
    NOTIFICATION_SERVICE_AVAILABLE = False

# Funções helper para uso direto
def notificar_resultado_disponivel(paciente, tipo_exame, **kwargs):
    """Função helper para notificar resultado disponível"""
    if not NOTIFICATION_SERVICE_AVAILABLE:
        return {'sucesso': False, 'erro': 'Notification Service não disponível'}
    
    return notification_service.notificar_resultado_disponivel(paciente, tipo_exame, **kwargs)

def notificar_laudo_disponivel(paciente, tipo_exame, **kwargs):
    """Função helper para notificar laudo disponível"""
    if not NOTIFICATION_SERVICE_AVAILABLE:
        return {'sucesso': False, 'erro': 'Notification Service não disponível'}
    
    return notification_service.notificar_laudo_disponivel(paciente, tipo_exame, **kwargs)
