from src.extensions import db
from datetime import datetime

# Tabela de associação entre usuários e perfis (para sistema multi-perfil)
usuario_perfil = db.Table('usuario_perfil',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('perfil_id', db.Integer, db.ForeignKey('perfis.id'), primary_key=True)
)

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    senha = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso = db.Column(db.DateTime)
    
    # Campos para sistema de senhas provisórias
    senha_provisoria = db.Column(db.Boolean, default=False)
    data_expiracao_senha = db.Column(db.DateTime)
    
    # Relacionamento many-to-many com perfis (sistema novo)
    perfis = db.relationship('Perfil', secondary=usuario_perfil, backref='usuarios')
    
    # Relacionamentos existentes
    profissional = db.relationship('Profissional', backref='usuario', uselist=False, lazy=True)
    paciente = db.relationship('Paciente', backref='usuario', uselist=False, lazy=True)
    
    def __repr__(self):
        return f'<Usuario {self.nome_completo}>'
    
    def has_perfil(self, perfil_nome):
        """Verifica se o usuário tem um perfil específico"""
        return any(perfil.nome == perfil_nome for perfil in self.perfis)
    
    def tem_perfil(self, perfil_nome):
        """Alias para has_perfil - mantém compatibilidade com código existente"""
        return self.has_perfil(perfil_nome)
    
    def get_perfis(self):
        """Retorna lista de todos os perfis do usuário"""
        return [perfil.nome for perfil in self.perfis]
    
    def get_primeiro_perfil(self):
        """Retorna o primeiro perfil do usuário (usado para redirecionamento)"""
        perfis = self.get_perfis()
        return perfis[0] if perfis else 'paciente'  # padrão: paciente
    
    def is_admin(self):
        """Verifica se o usuário é administrador"""
        return self.has_perfil('admin')
    
    def is_medico(self):
        """Verifica se o usuário é médico"""
        return self.has_perfil('medico')
    
    def is_assistente(self):
        """Verifica se o usuário é assistente"""
        return self.has_perfil('assistente')
    
    def is_paciente(self):
        """Verifica se o usuário é paciente"""
        return self.has_perfil('paciente')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome_completo': self.nome_completo,
            'cpf': self.cpf,
            'data_nascimento': self.data_nascimento.strftime('%Y-%m-%d') if self.data_nascimento else None,
            'email': self.email,
            'telefone': self.telefone,
            'ativo': self.ativo,
            'data_criacao': self.data_criacao.strftime('%Y-%m-%d %H:%M:%S') if self.data_criacao else None,
            'ultimo_acesso': self.ultimo_acesso.strftime('%Y-%m-%d %H:%M:%S') if self.ultimo_acesso else None,
            'senha_provisoria': self.senha_provisoria,
            'perfis': self.get_perfis()
        }
