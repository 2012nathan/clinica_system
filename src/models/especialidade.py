from src.extensions import db
from datetime import datetime

class Especialidade(db.Model):
    __tablename__ = 'especialidades'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    
    # Relacionamentos
    profissionais = db.relationship('Profissional', backref='especialidade', lazy=True)
    
    def __repr__(self):
        return f'<Especialidade {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao
        }
