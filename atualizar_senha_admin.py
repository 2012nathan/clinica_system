import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.extensions import db
from src.models.usuario import Usuario
from werkzeug.security import generate_password_hash
from src.main import app

def atualizar_senha_admin():
    with app.app_context():
        # Buscar o administrador
        admin = Usuario.query.filter_by(cpf='00000000000', tipo_perfil='admin').first()
        
        if admin:
            nova_senha = input("Digite a nova senha para o administrador: ")
            confirmar_senha = input("Confirme a nova senha: ")
            
            if nova_senha == confirmar_senha:
                admin.senha = generate_password_hash(nova_senha)
                db.session.commit()
                print("✅ Senha do administrador atualizada com sucesso!")
            else:
                print("❌ As senhas não coincidem!")
        else:
            print("❌ Administrador não encontrado!")

if __name__ == '__main__':
    atualizar_senha_admin()
