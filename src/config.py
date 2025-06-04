"""
Configurações centralizadas do sistema UltraClin
"""

import os
from datetime import timedelta
import secrets

class Config:
    """Configurações base"""
    
    # Configurações do Flask
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(16))
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Configurações do Banco de Dados
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:"
        f"{os.getenv('DB_PASSWORD', 'password')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '3306')}/"
        f"{os.getenv('DB_NAME', 'ultraclin_db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações de Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
    
    # Configurações de E-mail
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', os.getenv('SMTP_USER'))
    
    # Configurações de E-mail (compatibilidade Flask-Mail)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', os.getenv('SMTP_USER'))
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', os.getenv('SMTP_PASSWORD'))
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('SENDER_EMAIL'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
    
    # Configurações do Orthanc (DICOM)
    ORTHANC_URL = os.getenv('ORTHANC_URL', 'http://localhost:8042')
    ORTHANC_USER = os.getenv('ORTHANC_USER')
    ORTHANC_PASSWORD = os.getenv('ORTHANC_PASSWORD')
    ORTHANC_VIEWER_URL = os.getenv('ORTHANC_VIEWER_URL', 'http://localhost:3000')
    
    # Configurações da API SHOSP
    SHOSP_API_ID = os.getenv('SHOSP_API_ID')
    SHOSP_API_KEY = os.getenv('SHOSP_API_KEY')
    SHOSP_API_URL = os.getenv('SHOSP_API_URL', 'https://api.shosp.com.br/v1')
    
    # Configurações do WhatsApp
    WHATSAPP_API_URL = os.getenv('WHATSAPP_API_URL')
    WHATSAPP_API_TOKEN = os.getenv('WHATSAPP_API_TOKEN')
    
    @staticmethod
    def validate_shosp_config():
        """Valida se as configurações do SHOSP estão completas"""
        required_configs = ['SHOSP_API_ID', 'SHOSP_API_KEY', 'SHOSP_API_URL']
        missing_configs = []
        
        for config in required_configs:
            if not os.getenv(config):
                missing_configs.append(config)
        
        if missing_configs:
            raise ValueError(f"Configurações SHOSP faltando: {', '.join(missing_configs)}")
        
        return True
    
    @staticmethod
    def validate_email_config():
        """Valida se as configurações de e-mail estão completas"""
        required_configs = ['SMTP_USER', 'SMTP_PASSWORD']
        missing_configs = []
        
        for config in required_configs:
            if not os.getenv(config):
                missing_configs.append(config)
        
        if missing_configs:
            raise ValueError(f"Configurações de e-mail faltando: {', '.join(missing_configs)}")
        
        return True

class DevelopmentConfig(Config):
    """Configurações para desenvolvimento"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Configurações para produção"""
    DEBUG = False
    TESTING = False
    
    # Configurações de segurança para produção
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestingConfig(Config):
    """Configurações para testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Dicionário de configurações
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
