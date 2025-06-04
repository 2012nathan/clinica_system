# src/models/exame_imagem.py - VERSÃO ATUALIZADA
from src.extensions import db
from datetime import datetime

class ExameImagem(db.Model):
    __tablename__ = 'exames_imagem'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    
    # Dados básicos do exame
    tipo_exame = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    data_realizacao = db.Column(db.DateTime, nullable=True)
    data_exame = db.Column(db.DateTime, nullable=True)  # Compatibilidade
    medico_solicitante = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pendente')  # pendente, coletado, laudado
    
    # Integração DICOM/Orthanc
    orthanc_study_uid = db.Column(db.String(100), nullable=True, unique=True)
    orthanc_id = db.Column(db.String(100), nullable=True)  # Compatibilidade
    
    # Integração SHOSP
    shosp_agendamento_id = db.Column(db.String(50), nullable=True)
    prestador_codigo = db.Column(db.String(10), nullable=True)
    prestador_nome = db.Column(db.String(100), nullable=True)
    
    # NOVOS CAMPOS PARA CASOS ESPECIAIS
    # Tipo especial do exame
    tipo_especial = db.Column(db.String(20), nullable=True)  # 'gravacao', 'complemento', 'normal'
    
    # Para gravações de US
    link_gravacao = db.Column(db.String(500), nullable=True)
    senha_gravacao = db.Column(db.String(50), nullable=True)
    observacoes_gravacao = db.Column(db.Text, nullable=True)
    
    # Para exames complementares
    exame_principal_id = db.Column(db.Integer, db.ForeignKey('exames_imagem.id'), nullable=True)
    observacoes_complemento = db.Column(db.Text, nullable=True)
    
    # Dados de criação e controle
    data_criacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    assistente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamentos
    paciente = db.relationship('Paciente', back_populates='exames_imagem')
    assistente = db.relationship('Usuario', backref=db.backref('exames_imagem_criados', lazy=True))
    
    # Auto-relacionamento para exames complementares
    exame_principal = db.relationship('ExameImagem', remote_side=[id], backref='exames_complementares')
    
    def __repr__(self):
        return f'<ExameImagem {self.id}: {self.tipo_exame}>'
    
    def is_gravacao(self):
        """Verifica se é uma gravação de US"""
        return self.tipo_especial == 'gravacao'
    
    def is_complemento(self):
        """Verifica se é um exame complementar"""
        return self.tipo_especial == 'complemento'
    
    def is_normal(self):
        """Verifica se é um exame normal"""
        return self.tipo_especial is None or self.tipo_especial == 'normal'
    
    def get_nome_exame_principal(self):
        """Retorna o nome do exame principal se for complemento"""
        if self.is_complemento() and self.exame_principal:
            return self.exame_principal.tipo_exame
        return None
    
    def has_dicom(self):
        """Verifica se tem DICOM vinculado"""
        return self.orthanc_study_uid is not None
    
    def has_gravacao(self):
        """Verifica se tem gravação"""
        return self.link_gravacao is not None
    
    def get_status_display(self):
        """Retorna o status formatado para exibição"""
        status_map = {
            'pendente': 'Pendente',
            'coletado': 'Coletado',
            'laudado': 'Laudado'
        }
        return status_map.get(self.status, self.status.capitalize())
    
    def get_tipo_especial_display(self):
        """Retorna o tipo especial formatado para exibição"""
        if self.is_gravacao():
            return 'Gravação de US'
        elif self.is_complemento():
            return f'Complemento de: {self.get_nome_exame_principal()}'
        else:
            return 'Exame Normal'
    
    def pode_anexar_laudo(self):
        """Verifica se pode anexar laudo"""
        # Gravações não precisam de laudo
        if self.is_gravacao():
            return False
        # Complementos só precisam de laudo se for independente
        if self.is_complemento():
            return False
        # Exames normais sempre podem ter laudo
        return True
    
    def finalizar_gravacao(self, link, senha=None, observacoes=None):
        """Finaliza uma gravação de US"""
        if not self.is_gravacao():
            return False
        
        self.link_gravacao = link
        self.senha_gravacao = senha
        self.observacoes_gravacao = observacoes
        self.status = 'laudado'  # Gravação finalizada = laudado
        
        return True
    
    def finalizar_complemento(self, observacoes=None):
        """Finaliza um exame complementar"""
        if not self.is_complemento():
            return False
        
        self.observacoes_complemento = observacoes
        self.status = 'laudado'  # Complemento finalizado = laudado
        
        return True
    
    @staticmethod
    def criar_gravacao(paciente_id, tipo_exame, link, senha=None, observacoes=None, 
                      assistente_id=None, shosp_agendamento_id=None):
        """Cria uma gravação de US"""
        exame = ExameImagem(
            paciente_id=paciente_id,
            tipo_exame=tipo_exame,
            tipo_especial='gravacao',
            link_gravacao=link,
            senha_gravacao=senha,
            observacoes_gravacao=observacoes,
            status='laudado',  # Gravação já está finalizada
            data_realizacao=datetime.utcnow(),
            assistente_id=assistente_id,
            shosp_agendamento_id=shosp_agendamento_id
        )
        
        db.session.add(exame)
        return exame
    
    @staticmethod
    def criar_complemento(paciente_id, tipo_exame, exame_principal_id, observacoes=None,
                         assistente_id=None, shosp_agendamento_id=None):
        """Cria um exame complementar"""
        exame = ExameImagem(
            paciente_id=paciente_id,
            tipo_exame=tipo_exame,
            tipo_especial='complemento',
            exame_principal_id=exame_principal_id,
            observacoes_complemento=observacoes,
            status='laudado',  # Complemento já está finalizado
            data_realizacao=datetime.utcnow(),
            assistente_id=assistente_id,
            shosp_agendamento_id=shosp_agendamento_id
        )
        
        db.session.add(exame)
        return exame
    
    def to_dict(self):
        return {
            'id': self.id,
            'paciente_id': self.paciente_id,
            'tipo_exame': self.tipo_exame,
            'descricao': self.descricao,
            'data_realizacao': self.data_realizacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_realizacao else None,
            'medico_solicitante': self.medico_solicitante,
            'status': self.status,
            'status_display': self.get_status_display(),
            'orthanc_study_uid': self.orthanc_study_uid,
            'shosp_agendamento_id': self.shosp_agendamento_id,
            'prestador_codigo': self.prestador_codigo,
            'prestador_nome': self.prestador_nome,
            'tipo_especial': self.tipo_especial,
            'tipo_especial_display': self.get_tipo_especial_display(),
            'link_gravacao': self.link_gravacao,
            'senha_gravacao': self.senha_gravacao,
            'observacoes_gravacao': self.observacoes_gravacao,
            'exame_principal_id': self.exame_principal_id,
            'nome_exame_principal': self.get_nome_exame_principal(),
            'observacoes_complemento': self.observacoes_complemento,
            'has_dicom': self.has_dicom(),
            'has_gravacao': self.has_gravacao(),
            'pode_anexar_laudo': self.pode_anexar_laudo(),
            'data_criacao': self.data_criacao.strftime('%Y-%m-%d %H:%M:%S'),
            'assistente_id': self.assistente_id
        }
