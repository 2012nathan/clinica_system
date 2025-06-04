## Configuração do Sistema de Gerenciamento da Clínica

### Requisitos do Sistema

#### Requisitos de Hardware
- Servidor com pelo menos 4GB de RAM
- 20GB de espaço em disco disponível
- Processador dual-core ou superior

#### Requisitos de Software
- Sistema operacional: Linux (Ubuntu 20.04 LTS ou superior recomendado)
- Python 3.8 ou superior
- MySQL 8.0 ou superior
- Servidor web (Nginx ou Apache)
- Certificado SSL para conexões seguras

### Variáveis de Ambiente

O sistema utiliza as seguintes variáveis de ambiente que devem ser configuradas no servidor:

```
# Configurações do Banco de Dados
DB_USERNAME=seu_usuario_mysql
DB_PASSWORD=sua_senha_mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=clinica_db

# Configurações de Email
SMTP_SERVER=smtp.seudominio.com
SMTP_PORT=587
SMTP_USER=seu_email@seudominio.com
SMTP_PASSWORD=sua_senha_email
SENDER_EMAIL=noreply@seudominio.com

# Configurações do WhatsApp (opcional)
WHATSAPP_API_URL=https://api.whatsapp.com/send
WHATSAPP_API_TOKEN=seu_token_api

# Configurações do Orthanc
ORTHANC_URL=http://seu_servidor_orthanc:8042
ORTHANC_USER=seu_usuario_orthanc
ORTHANC_PASSWORD=sua_senha_orthanc
ORTHANC_VIEWER_URL=http://seu_servidor_orthanc:8042/app/explorer.html

# Configurações do Shosp
SHOSP_API_URL=https://api.shosp.com.br
SHOSP_API_TOKEN=seu_token_api_shosp

# Configurações de Segurança
SECRET_KEY=chave_secreta_para_sessoes
UPLOAD_FOLDER=/caminho/para/uploads
```

### Instruções de Instalação

1. Clone o repositório:
```bash
git clone https://github.com/sua-organizacao/clinica-system.git
cd clinica-system
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure o banco de dados:
```bash
mysql -u root -p
```

```sql
CREATE DATABASE clinica_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'clinica_user'@'localhost' IDENTIFIED BY 'senha_segura';
GRANT ALL PRIVILEGES ON clinica_db.* TO 'clinica_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

5. Configure as variáveis de ambiente (crie um arquivo `.env` na raiz do projeto)

6. Inicialize o banco de dados:
```bash
flask db init
flask db migrate -m "Inicialização do banco de dados"
flask db upgrade
```

7. Crie um usuário administrador:
```bash
flask create-admin
```

8. Execute o servidor de desenvolvimento:
```bash
flask run
```

### Implantação em Produção

Para implantação em ambiente de produção, recomendamos:

1. Configurar o Gunicorn como servidor WSGI:
```bash
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:8000 "src.main:create_app()"
```

2. Configurar o Nginx como proxy reverso:
```nginx
server {
    listen 80;
    server_name seudominio.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static {
        alias /caminho/para/clinica-system/src/static;
    }
    
    location /uploads {
        alias /caminho/para/uploads;
    }
}
```

3. Configurar o Supervisor para gerenciar o processo:
```ini
[program:clinica-system]
command=/caminho/para/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 "src.main:create_app()"
directory=/caminho/para/clinica-system
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/clinica-system/error.log
stdout_logfile=/var/log/clinica-system/access.log
```

4. Configurar backup automático do banco de dados:
```bash
# Adicione ao crontab
0 2 * * * /caminho/para/scripts/backup_database.sh
```

### Integração com Orthanc

Para integrar com o servidor Orthanc:

1. Certifique-se de que o Orthanc esteja configurado para permitir acesso via API REST
2. Configure o CORS no Orthanc para permitir requisições do domínio da aplicação
3. Verifique se o visualizador DICOM está disponível na URL configurada

### Integração com Shosp

Para integrar com a API do Shosp:

1. Obtenha as credenciais de acesso à API com o suporte do Shosp
2. Configure as variáveis de ambiente com a URL e token de acesso
3. Teste a conexão usando a rota de teste da aplicação: `/api/test-shosp-connection`

### Manutenção

- Realize backups diários do banco de dados
- Monitore o espaço em disco, especialmente na pasta de uploads
- Verifique regularmente os logs de erro em `/var/log/clinica-system/`
- Atualize as dependências periodicamente para garantir segurança
