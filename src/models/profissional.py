from src.extensions import db
from datetime import datetime

class Profissional(db.Model):
    __tablename__ = 'profissionais'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    especialidade_id = db.Column(db.Integer, db.ForeignKey('especialidades.id'), nullable=False)
    registro_profissional = db.Column(db.String(50), nullable=False)
    biografia = db.Column(db.Text)
    foto_perfil = db.Column(db.String(255))
    assinatura_digital = db.Column(db.String(255))
    
    # Relacionamentos
    disponibilidades = db.relationship('DisponibilidadeProfissional', backref='profissional', lazy=True)
    agendamentos = db.relationship('Agendamento', backref='profissional', lazy=True)
    documentos = db.relationship('Documento', backref='profissional', lazy=True)
    consultas_pre_natal = db.relationship('ConsultaPreNatal', backref='profissional', lazy=True)
    
    def __repr__(self):
        return f'<Profissional {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'especialidade_id': self.especialidade_id,
            'registro_profissional': self.registro_profissional,
            'biografia': self.biografia,
            'foto_perfil': self.foto_perfil,
            'assinatura_digital': self.assinatura_digital
        }
