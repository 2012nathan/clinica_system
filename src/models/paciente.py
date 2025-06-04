from src.extensions import db
from datetime import datetime

class Paciente(db.Model):
    __tablename__ = 'pacientes'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    cartao_sus = db.Column(db.String(20))
    convenio = db.Column(db.String(100))
    numero_convenio = db.Column(db.String(50))
    observacoes = db.Column(db.Text)
    
    # Relacionamentos
    agendamentos = db.relationship('Agendamento', backref='paciente', lazy=True)
    documentos = db.relationship('Documento', backref='paciente', lazy=True)
    exames_imagem = db.relationship('ExameImagem', back_populates='paciente', lazy=True)
    cartao_gestante = db.relationship('CartaoGestante', backref='paciente', uselist=False, lazy=True)
    
    def __repr__(self):
        return f'<Paciente {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'cartao_sus': self.cartao_sus,
            'convenio': self.convenio,
            'numero_convenio': self.numero_convenio,
            'observacoes': self.observacoes
        }
