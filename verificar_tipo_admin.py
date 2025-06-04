from src.main import app
from src.models.usuario import Usuario

with app.app_context():
    admin = Usuario.query.filter_by(email='admin@clinica.com').first()
    if admin:
        print(f"Admin encontrado: {admin.email}")
        print(f"Tipo: {admin.tipo if hasattr(admin, 'tipo') else 'Campo não encontrado'}")
        print(f"Tipo_perfil: {admin.tipo_perfil if hasattr(admin, 'tipo_perfil') else 'Campo não encontrado'}")
    else:
        print("Admin não encontrado")
