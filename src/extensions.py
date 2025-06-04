from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Inicializar extensões
db = SQLAlchemy()
migrate = Migrate()

# Função para inicializar extensões
def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
