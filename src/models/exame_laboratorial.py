from src.extensions import db
from datetime import datetime

class ExameLaboratorial(db.Model):
    __tablename__ = 'exames_laboratoriais'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    tipo_exame = db.Column(db.String(100), nullable=False)
    data_solicitacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_coleta = db.Column(db.DateTime, nullable=True)
    data_resultado = db.Column(db.DateTime, nullable=True)
    medico_solicitante = db.Column(db.String(100), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pendente')  # pendente, coletado, resultado_disponivel
    arquivo_resultado = db.Column(db.String(255), nullable=True)  # Caminho para o arquivo PDF
    assistente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    data_cadastro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    paciente = db.relationship('Paciente', backref=db.backref('exames_laboratoriais', lazy=True))
    assistente = db.relationship('Usuario', backref=db.backref('exames_laboratoriais_cadastrados', lazy=True))
    
    def __repr__(self):
        return f'<ExameLaboratorial {self.id}: {self.tipo_exame}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'paciente_id': self.paciente_id,
            'tipo_exame': self.tipo_exame,
            'data_solicitacao': self.data_solicitacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_solicitacao else None,
            'data_coleta': self.data_coleta.strftime('%Y-%m-%d %H:%M:%S') if self.data_coleta else None,
            'data_resultado': self.data_resultado.strftime('%Y-%m-%d %H:%M:%S') if self.data_resultado else None,
            'medico_solicitante': self.medico_solicitante,
            'observacoes': self.observacoes,
            'status': self.status,
            'arquivo_resultado': self.arquivo_resultado,
            'assistente_id': self.assistente_id,
            'data_cadastro': self.data_cadastro.strftime('%Y-%m-%d %H:%M:%S'),
            'data_atualizacao': self.data_atualizacao.strftime('%Y-%m-%d %H:%M:%S')
        }
