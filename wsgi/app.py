import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app as application, criar_admin_padrao

# Inicializar banco de dados e criar usuário admin
criar_admin_padrao()

if __name__ == "__main__":
    application.run()
