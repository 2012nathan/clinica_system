# src/services/gmail_no_browser_service.py
import os
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class GmailNoBrowserService:
    def __init__(self):
        self.service = None
        self.setup_gmail()
    
    def setup_gmail(self):
        """Configura Gmail API sem navegador (para servidores)"""
        creds = None
        token_path = 'token.json'
        credentials_path = 'credentials.json'
        
        # Verificar se credentials.json existe
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"❌ Arquivo {credentials_path} não encontrado. "
                "Baixe-o do Google Cloud Console e coloque na raiz do projeto."
            )
        
        print(f"📁 Procurando credenciais em: {os.path.abspath(credentials_path)}")
        print(f"📁 Procurando token em: {os.path.abspath(token_path)}")
        
        # Carregar token existente
        if os.path.exists(token_path):
            print("📄 Token encontrado, carregando...")
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        # Se não há credenciais válidas, fazer autenticação manual
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refresh token encontrado, renovando...")
                try:
                    creds.refresh(Request())
                    print("✅ Token renovado com sucesso!")
                except Exception as e:
                    print(f"❌ Erro ao renovar token: {e}")
                    print("🔧 Será necessário fazer nova autenticação...")
                    creds = None
            
            if not creds:
                print("\n🔐 PRIMEIRA AUTENTICAÇÃO NECESSÁRIA")
                print("=" * 50)
                
                # Criar flow para autenticação manual
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                
                # Obter URL de autorização
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'  # Para aplicações instaladas
                auth_url, _ = flow.authorization_url(prompt='consent')
                
                print("🌐 PASSO 1: Abra este link em seu navegador LOCAL:")
                print("-" * 50)
                print(auth_url)
                print("-" * 50)
                print()
                print("🔑 PASSO 2: Após autorizar, você receberá um código.")
                print("📋 PASSO 3: Cole o código abaixo:")
                
                # Solicitar código manualmente
                authorization_code = input("\n👉 Cole o código de autorização aqui: ").strip()
                
                if not authorization_code:
                    raise ValueError("❌ Código de autorização não fornecido!")
                
                try:
                    # Trocar código por token
                    flow.fetch_token(code=authorization_code)
                    creds = flow.credentials
                    print("✅ Autenticação realizada com sucesso!")
                    
                except Exception as e:
                    raise ValueError(f"❌ Erro na autenticação: {e}")
            
            # Salvar token para próximas execuções
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            print(f"💾 Token salvo em: {os.path.abspath(token_path)}")
        
        # Construir serviço Gmail
        self.service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail API configurada com sucesso!")
        logging.info("Gmail API configurada com sucesso")
    
    def enviar_email(self, destinatario, assunto, corpo_html, corpo_texto=None):
        """Envia email via Gmail API"""
        try:
            # Verificar se serviço está configurado
            if not self.service:
                raise Exception("Serviço Gmail não está configurado")
            
            # Criar mensagem
            message = MIMEMultipart('alternative')
            message['to'] = destinatario
            message['from'] = os.getenv('GMAIL_SENDER_EMAIL')
            message['subject'] = assunto
            
            # Verificar se GMAIL_SENDER_EMAIL está configurado
            if not os.getenv('GMAIL_SENDER_EMAIL'):
                raise Exception("GMAIL_SENDER_EMAIL não configurado no .env")
            
            # Adicionar conteúdo
            if corpo_texto:
                part1 = MIMEText(corpo_texto, 'plain', 'utf-8')
                message.attach(part1)
            
            part2 = MIMEText(corpo_html, 'html', 'utf-8')
            message.attach(part2)
            
            # Codificar e enviar
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = self.service.users().messages().send(
                userId="me",
                body={'raw': raw_message}
            ).execute()
            
            print(f"✅ Email enviado para {destinatario}")
            logging.info(f"Email enviado para {destinatario}")
            return {
                'sucesso': True,
                'message_id': send_message['id'],
                'destinatario': destinatario
            }
            
        except Exception as e:
            print(f"❌ Erro ao enviar email: {e}")
            logging.error(f"Erro ao enviar email: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def enviar_senha_provisoria(self, usuario, senha_provisoria):
        """Envia senha provisória"""
        assunto = "UltraClin - Sua senha provisória"
        
        corpo_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #ff6600; color: white; padding: 20px; text-align: center;">
                <h1>🏥 UltraClin</h1>
                <p>Sistema de Gestão Clínica</p>
            </div>
            
            <div style="padding: 30px; background-color: #f9f9f9;">
                <h2>Olá, {usuario.nome_completo}!</h2>
                
                <p>Sua conta foi criada no sistema UltraClin.</p>
                
                <div style="background-color: white; border: 2px solid #ff6600; padding: 20px; text-align: center; margin: 20px 0;">
                    <h3>Sua Senha Provisória:</h3>
                    <h2 style="color: #ff6600; font-family: monospace; letter-spacing: 2px;">{senha_provisoria}</h2>
                </div>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 15px 0;">
                    <h4>⚠️ Importante:</h4>
                    <ul>
                        <li>Esta senha é <strong>temporária</strong> (válida por 24h)</li>
                        <li>Você <strong>deve alterar</strong> no primeiro acesso</li>
                        <li>Não compartilhe com ninguém</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{os.getenv('APP_URL', 'http://localhost:5000')}/auth/login" 
                       style="background-color: #ff6600; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        🔐 Acessar Sistema
                    </a>
                </div>
            </div>
            
            <div style="background-color: #333; color: white; padding: 15px; text-align: center;">
                <p>© 2025 UltraClin - Sistema de Gestão Clínica</p>
                <p>Este email é automático, não responda.</p>
            </div>
        </div>
        """
        
        return self.enviar_email(usuario.email, assunto, corpo_html)
    
    def enviar_recuperacao_senha(self, usuario, token_recuperacao):
        """Envia email de recuperação de senha"""
        assunto = "UltraClin - Recuperação de Senha"
        
        link_recuperacao = f"{os.getenv('APP_URL', 'http://localhost:5000')}/auth/redefinir-senha?token={token_recuperacao}"
        
        corpo_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #ff6600; color: white; padding: 20px; text-align: center;">
                <h1>🏥 UltraClin</h1>
                <p>Sistema de Gestão Clínica</p>
            </div>
            
            <div style="padding: 30px; background-color: #f9f9f9;">
                <h2>Recuperação de Senha</h2>
                
                <p>Olá, {usuario.nome_completo}!</p>
                
                <p>Recebemos uma solicitação de recuperação de senha para sua conta.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{link_recuperacao}" 
                       style="background-color: #ff6600; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        🔐 Redefinir Senha
                    </a>
                </div>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 15px 0;">
                    <h4>⚠️ Importante:</h4>
                    <ul>
                        <li>Este link é válido por <strong>1 hora</strong></li>
                        <li>Se você não solicitou, ignore este email</li>
                    </ul>
                </div>
                
                <p>Link direto: {link_recuperacao}</p>
            </div>
            
            <div style="background-color: #333; color: white; padding: 15px; text-align: center;">
                <p>© 2025 UltraClin - Sistema de Gestão Clínica</p>
            </div>
        </div>
        """
        
        return self.enviar_email(usuario.email, assunto, corpo_html)

# Para teste
if __name__ == "__main__":
    print("🏥 UltraClin - Teste Gmail API")
    print("=" * 40)
    
    try:
        service = GmailNoBrowserService()
        print("✅ Serviço configurado com sucesso!")
        
        # Teste básico
        resultado = service.enviar_email(
            "teste@exemplo.com",
            "Teste UltraClin Gmail API", 
            "<h1>Teste funcionando!</h1>",
            "Teste funcionando!"
        )
        
        print(f"📧 Resultado do teste: {resultado}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("\n💡 Dicas:")
        print("1. Verifique se credentials.json existe")
        print("2. Configure GMAIL_SENDER_EMAIL no .env")
        print("3. Execute a autenticação inicial")
