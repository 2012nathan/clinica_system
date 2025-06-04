from src.extensions import db
from datetime import datetime

class Documento(db.Model):
    __tablename__ = 'documentos'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    profissional_id = db.Column(db.Integer, db.ForeignKey('profissionais.id'), nullable=True)
    assistente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    tipo = db.Column(db.Enum('receita', 'atestado', 'laudo', 'outro'), nullable=False)
    titulo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text)
    arquivo_caminho = db.Column(db.String(255), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.Enum('pendente', 'disponivel', 'visualizado'), default='disponivel')
    exame_imagem_id = db.Column(db.Integer, db.ForeignKey('exames_imagem.id'), nullable=True)
    
    # Relacionamentos
    exame_imagem = db.relationship('ExameImagem', backref='laudo', uselist=False, lazy=True)
    
    def __repr__(self):
        return f'<Documento {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'paciente_id': self.paciente_id,
            'profissional_id': self.profissional_id,
            'assistente_id': self.assistente_id,
            'tipo': self.tipo,
            'titulo': self.titulo,
            'descricao': self.descricao,
            'arquivo_caminho': self.arquivo_caminho,
            'data_criacao': self.data_criacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_atualizacao else None,
            'status': self.status
        }
