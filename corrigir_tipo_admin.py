from src.main import app, db
from src.models.usuario import Usuario

with app.app_context():
    admin = Usuario.query.filter_by(email='admin@clinica.com').first()
    if admin:
        admin.tipo = 'admin'
        admin.tipo_perfil = 'admin'
        db.session.commit()
        print("Campos 'tipo' e 'tipo_perfil' atualizados com sucesso!")
    else:
        print("Admin não encontrado")
