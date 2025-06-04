from src.extensions import db
from datetime import datetime

class DisponibilidadeProfissional(db.Model):
    __tablename__ = 'disponibilidades_profissionais'
    
    id = db.Column(db.Integer, primary_key=True)
    profissional_id = db.Column(db.Integer, db.ForeignKey('profissionais.id'), nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)  # 0=Domingo, 1=Segunda, ..., 6=Sábado
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)
    intervalo_minutos = db.Column(db.Integer, default=30)  # Duração padrão de cada consulta
    ativo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<DisponibilidadeProfissional {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'profissional_id': self.profissional_id,
            'dia_semana': self.dia_semana,
            'hora_inicio': self.hora_inicio.strftime('%H:%M') if self.hora_inicio else None,
            'hora_fim': self.hora_fim.strftime('%H:%M') if self.hora_fim else None,
            'intervalo_minutos': self.intervalo_minutos,
            'ativo': self.ativo
        }
