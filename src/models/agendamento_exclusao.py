# src/models/agendamento_exclusao.py
from src.extensions import db
from datetime import datetime

class AgendamentoExclusao(db.Model):
    """
    Modelo para controlar agendamentos SHOSP que foram excluídos
    e não devem mais aparecer na listagem
    """
    __tablename__ = 'agendamentos_exclusoes'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do agendamento SHOSP excluído
    shosp_agendamento_id = db.Column(db.String(50), nullable=False, unique=True)
    paciente_cpf = db.Column(db.String(11), nullable=False)
    paciente_nome = db.Column(db.String(200), nullable=False)
    tipo_agendamento = db.Column(db.String(100), nullable=False)
    data_agendamento = db.Column(db.DateTime, nullable=False)
    prestador_codigo = db.Column(db.String(10), nullable=True)
    prestador_nome = db.Column(db.String(100), nullable=True)
    
    # Dados da exclusão
    motivo_exclusao = db.Column(db.String(20), nullable=False)  # 'nao_e_exame', 'duplicado', 'cancelado', 'outro'
    descricao_motivo = db.Column(db.Text, nullable=True)
    data_exclusao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    usuario_exclusao_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    # Relacionamentos
    usuario_exclusao = db.relationship('Usuario', backref=db.backref('agendamentos_excluidos', lazy=True))
    
    def __repr__(self):
        return f'<AgendamentoExclusao {self.shosp_agendamento_id}: {self.motivo_exclusao}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'shosp_agendamento_id': self.shosp_agendamento_id,
            'paciente_cpf': self.paciente_cpf,
            'paciente_nome': self.paciente_nome,
            'tipo_agendamento': self.tipo_agendamento,
            'data_agendamento': self.data_agendamento.strftime('%Y-%m-%d %H:%M:%S'),
            'prestador_codigo': self.prestador_codigo,
            'prestador_nome': self.prestador_nome,
            'motivo_exclusao': self.motivo_exclusao,
            'descricao_motivo': self.descricao_motivo,
            'data_exclusao': self.data_exclusao.strftime('%Y-%m-%d %H:%M:%S'),
            'usuario_exclusao_id': self.usuario_exclusao_id,
            'usuario_exclusao_nome': self.usuario_exclusao.nome_completo if self.usuario_exclusao else None
        }
    
    @staticmethod
    def is_excluido(shosp_agendamento_id):
        """
        Verifica se um agendamento SHOSP já foi excluído
        """
        return AgendamentoExclusao.query.filter_by(
            shosp_agendamento_id=shosp_agendamento_id
        ).first() is not None
    
    @staticmethod
    def excluir_agendamento(shosp_agendamento_id, agendamento_data, motivo, descricao, usuario_id):
        """
        Adiciona um agendamento à lista de exclusões
        """
        exclusao = AgendamentoExclusao(
            shosp_agendamento_id=shosp_agendamento_id,
            paciente_cpf=agendamento_data.get('paciente_cpf', ''),
            paciente_nome=agendamento_data.get('paciente_nome', ''),
            tipo_agendamento=agendamento_data.get('tipo_agendamento', ''),
            data_agendamento=agendamento_data.get('data_agendamento'),
            prestador_codigo=agendamento_data.get('prestador_codigo'),
            prestador_nome=agendamento_data.get('prestador_nome'),
            motivo_exclusao=motivo,
            descricao_motivo=descricao,
            usuario_exclusao_id=usuario_id
        )
        
        db.session.add(exclusao)
        db.session.commit()
        
        return exclusao
