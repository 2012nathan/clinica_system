from src.main import app, db
from src.models.usuario import Usuario
from werkzeug.security import generate_password_hash
from datetime import datetime

with app.app_context():
    admin = Usuario.query.filter_by(email='admin@clinica.com').first()

    if admin:
        print(f"Admin já existe: {admin.email}")
        admin.tipo_perfil = 'admin'
        admin.senha_hash = generate_password_hash('admin123')
        db.session.commit()
        print("Admin atualizado com sucesso!")
    else:
        admin = Usuario(
            nome_completo='Administrador',
            cpf='00000000000',
            email='admin@clinica.com',
            senha_hash=generate_password_hash('admin123'),
            data_nascimento=datetime.now().date(),
            tipo_perfil='admin',
            ativo=True,
            senha_provisoria=False
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin criado com sucesso!")
