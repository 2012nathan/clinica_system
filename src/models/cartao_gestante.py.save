from src.extensions import db
from datetime import datetime

class CartaoGestante(db.Model):
    __tablename__ = 'cartoes_gestante'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    data_ultima_menstruacao = db.Column(db.Date)
    data_provavel_parto = db.Column(db.Date)
    gestacoes_previas = db.Column(db.Integer, default=0)
    partos_previos = db.Column(db.Integer, default=0)
    abortos_previos = db.Column(db.Integer, default=0)
    altura_cm = db.Column(db.Integer)
    peso_inicial_kg = db.Column(db.Float)
    imc_inicial = db.Column(db.Float)
    grupo_sanguineo = db.Column(db.String(5))
    fator_rh = db.Column(db.String(10))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    consultas = db.relationship('ConsultaPreNatal', backref='cartao_gestante', lazy=True)
    exames = db.relationship('ExamePreNatal', backref='cartao_gestante', lazy=True)
    medicacoes = db.relationship('MedicacaoGestante', backref='cartao_gestante', lazy=True)
    
    def __repr__(self):
        return f'<CartaoGestante {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'paciente_id': self.paciente_id,
            'data_ultima_menstruacao': self.data_ultima_menstruacao.strftime('%Y-%m-%d') if self.data_ultima_menstruacao else None,
            'data_provavel_parto': self.data_provavel_parto.strftime('%Y-%m-%d') if self.data_provavel_parto else None,
            'gestacoes_previas': self.gestacoes_previas,
            'partos_previos': self.partos_previos,
            'abortos_previos': self.abortos_previos,
            'altura_cm': self.altura_cm,
            'peso_inicial_kg': self.peso_inicial_kg,
            'imc_inicial': self.imc_inicial,
            'grupo_sanguineo': self.grupo_sanguineo,
            'fator_rh': self.fator_rh,
            'data_criacao': self.data_criacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_atualizacao else None
        }

class ConsultaPreNatal(db.Model):
    __tablename__ = 'consultas_pre_natal'
    
    id = db.Column(db.Integer, primary_key=True)
    cartao_gestante_id = db.Column(db.Integer, db.ForeignKey('cartoes_gestante.id'), nullable=False)
    profissional_id = db.Column(db.Integer, db.ForeignKey('profissionais.id'), nullable=False)
    data_consulta = db.Column(db.DateTime, nullable=False)
    semanas_gestacao = db.Column(db.Integer)
    peso_kg = db.Column(db.Float)
    pressao_arterial = db.Column(db.String(10))
    altura_uterina_cm = db.Column(db.Float)
    bcf = db.Column(db.Integer)
    movimentos_fetais = db.Column(db.Boolean)
    edema = db.Column(db.Enum('ausente', '+', '++', '+++'), default='ausente')
    observacoes_medicas = db.Column(db.Text)
    observacoes_gestante = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ConsultaPreNatal {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'cartao_gestante_id': self.cartao_gestante_id,
            'profissional_id': self.profissional_id,
            'data_consulta': self.data_consulta.strftime('%Y-%m-%d %H:%M:%S') if self.data_consulta else None,
            'semanas_gestacao': self.semanas_gestacao,
            'peso_kg': self.peso_kg,
            'pressao_arterial': self.pressao_arterial,
            'altura_uterina_cm': self.altura_uterina_cm,
            'bcf': self.bcf,
            'movimentos_fetais': self.movimentos_fetais,
            'edema': self.edema,
            'observacoes_medicas': self.observacoes_medicas,
            'observacoes_gestante': self.observacoes_gestante
        }

class ExamePreNatal(db.Model):
    __tablename__ = 'exames_pre_natal'
    
    id = db.Column(db.Integer, primary_key=True)
    cartao_gestante_id = db.Column(db.Integer, db.ForeignKey('cartoes_gestante.id'), nullable=False)
    tipo_exame = db.Column(db.String(100), nullable=False)
    data_solicitacao = db.Column(db.Date, nullable=False)
    data_realizacao = db.Column(db.Date)
    resultado = db.Column(db.Text)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.id'))
    observacoes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ExamePreNatal {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'cartao_gestante_id': self.cartao_gestante_id,
            'tipo_exame': self.tipo_exame,
            'data_solicitacao': self.data_solicitacao.strftime('%Y-%m-%d') if self.data_solicitacao else None,
            'data_realizacao': self.data_realizacao.strftime('%Y-%m-%d') if self.data_realizacao else None,
            'resultado': self.resultado,
            'documento_id': self.documento_id,
            'observacoes': self.observacoes
        }

class MedicacaoGestante(db.Model):
    __tablename__ = 'medicacoes_gestante'
    
    id = db.Column(db.Integer, primary_key=True)
    cartao_gestante_id = db.Column(db.Integer, db.ForeignKey('cartoes_gestante.id'), nullable=False)
    nome_medicacao = db.Column(db.String(100), nullable=False)
    dosagem = db.Column(db.String(50), nullable=False)
    posologia = db.Column(db.String(255), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date)
    motivo = db.Column(db.Text)
    lembrete_ativo = db.Column(db.Boolean, default=True)
    horario_lembrete = db.Column(db.Time)
    
    def __repr__(self):
        return f'<MedicacaoGestante {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'cartao_gestante_id': self.cartao_gestante_id,
            'nome_medicacao': self.nome_medicacao,
            'dosagem': self.dosagem,
            'posologia': self.posologia,
            'data_inicio': self.data_inicio.strftime('%Y-%m-%d') if self.data_inicio else None,
            'data_fim': self.data_fim.strftime('%Y-%m-%d') if self.data_fim else None,
            'motivo': self.motivo,
            'lembrete_ativo': self.lembrete_ativo,
            'horario_lembrete': self.horario_lembrete.strftime('%H:%M') if self.horario_lembrete else None
        }
