# Importações dos modelos para facilitar o acesso
from .usuario import Usuario
from .perfil import Perfil
from .profissional import Profissional
from .especialidade import Especialidade
from .disponibilidade import DisponibilidadeProfissional
from .paciente import Paciente
from .agendamento import Agendamento
from .documento import Documento
from .exame_imagem import ExameImagem
from .exame_laboratorial import ExameLaboratorial
from .cartao_gestante import CartaoGestante, ConsultaPreNatal, ExamePreNatal, MedicacaoGestante

# Lista de todos os modelos disponíveis
__all__ = [
    'Usuario',
    'Perfil',
    'Profissional', 
    'Especialidade',
    'DisponibilidadeProfissional',
    'Paciente',
    'Agendamento',
    'Documento',
    'ExameImagem',
    'ExameLaboratorial',
    'CartaoGestante',
    'ConsultaPreNatal',
    'ExamePreNatal',
    'MedicacaoGestante'
]
