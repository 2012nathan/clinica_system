from src.extensions import db
from datetime import datetime

class Agendamento(db.Model):
    __tablename__ = 'agendamentos'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    profissional_id = db.Column(db.Integer, db.ForeignKey('profissionais.id'), nullable=False)
    data_hora_inicio = db.Column(db.DateTime, nullable=False)
    data_hora_fim = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum('agendado', 'confirmado', 'cancelado', 'realizado'), default='agendado')
    motivo_consulta = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notificacao_enviada = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Agendamento {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'paciente_id': self.paciente_id,
            'profissional_id': self.profissional_id,
            'data_hora_inicio': self.data_hora_inicio.strftime('%Y-%m-%d %H:%M:%S') if self.data_hora_inicio else None,
            'data_hora_fim': self.data_hora_fim.strftime('%Y-%m-%d %H:%M:%S') if self.data_hora_fim else None,
            'status': self.status,
            'motivo_consulta': self.motivo_consulta,
            'observacoes': self.observacoes,
            'data_criacao': self.data_criacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_atualizacao else None,
            'notificacao_enviada': self.notificacao_enviada
        }
