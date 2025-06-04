from flask import Blueprint, jsonify, request, current_app
from src.models.usuario import Usuario
from src.models.paciente import Paciente
from src.models.agendamento import Agendamento
from src.models.documento import Documento
from src.models.exame_imagem import ExameImagem
from src.models.exame_laboratorial import ExameLaboratorial
from src.models.cartao_gestante import CartaoGestante
from src.extensions import db
import jwt
from datetime import datetime, timedelta
from functools import wraps

api_bp = Blueprint('api', __name__)

# Middleware para verificar token JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token não fornecido!'}), 401
        
        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = Usuario.query.get(data['user_id'])
            
            if not current_user:
                return jsonify({'message': 'Usuário não encontrado!'}), 401
            
            if not current_user.ativo:
                return jsonify({'message': 'Usuário inativo!'}), 401
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token inválido!'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# Rota pública para login e obtenção de token
@api_bp.route('/public/login', methods=['POST'])
def login():
    data = request.json
    
    if not data or not data.get('cpf') or not data.get('senha'):
        return jsonify({'message': 'Dados de login incompletos!'}), 400
    
    cpf = data.get('cpf')
    senha = data.get('senha')
    
    # Remover caracteres não numéricos do CPF
    cpf = ''.join(filter(str.isdigit, cpf))
    
    usuario = Usuario.query.filter_by(cpf=cpf).first()
    
    if not usuario:
        return jsonify({'message': 'CPF não encontrado!'}), 401
    
    # Verificar senha
    from werkzeug.security import check_password_hash
    if not check_password_hash(usuario.senha, senha):
        return jsonify({'message': 'Senha incorreta!'}), 401
    
    # Verificar se a conta está ativa
    if not usuario.ativo:
        return jsonify({'message': 'Conta desativada!'}), 401
    
    # Obter perfis do usuário
    perfis = [perfil.nome for perfil in usuario.perfis]
    
    # Gerar token JWT
    token_payload = {
        'user_id': usuario.id,
        'perfis': perfis,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    
    token = jwt.encode(token_payload, current_app.config['JWT_SECRET_KEY'], algorithm="HS256")
    
    # Atualizar último acesso
    usuario.ultimo_acesso = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'token': token,
        'user': {
            'id': usuario.id,
            'nome': usuario.nome_completo,
            'perfis': perfis
        }
    })

# Rota para renovar token
@api_bp.route('/refresh-token', methods=['POST'])
@token_required
def refresh_token(current_user):
    # Obter perfis do usuário
    perfis = [perfil.nome for perfil in current_user.perfis]
    
    # Gerar novo token JWT
    token_payload = {
        'user_id': current_user.id,
        'perfis': perfis,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    
    token = jwt.encode(token_payload, current_app.config['JWT_SECRET_KEY'], algorithm="HS256")
    
    return jsonify({'token': token})

# Rota para obter dados do usuário logado
@api_bp.route('/me', methods=['GET'])
@token_required
def get_me(current_user):
    return jsonify(current_user.to_dict())

# Rotas para pacientes
@api_bp.route('/pacientes/agendamentos', methods=['GET'])
@token_required
def get_agendamentos_paciente(current_user):
    if not current_user.tem_perfil('paciente'):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    paciente = current_user.paciente
    
    if not paciente:
        return jsonify({'message': 'Perfil de paciente não encontrado!'}), 404
    
    agendamentos = Agendamento.query.filter_by(paciente_id=paciente.id).all()
    
    return jsonify([{
        'id': a.id,
        'data': a.data_hora_inicio.strftime('%Y-%m-%d'),
        'hora_inicio': a.data_hora_inicio.strftime('%H:%M'),
        'hora_fim': a.data_hora_fim.strftime('%H:%M'),
        'status': a.status,
        'profissional': a.profissional.usuario.nome_completo,
        'especialidade': a.profissional.especialidade.nome
    } for a in agendamentos])

@api_bp.route('/pacientes/documentos', methods=['GET'])
@token_required
def get_documentos_paciente(current_user):
    if not current_user.tem_perfil('paciente'):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    paciente = current_user.paciente
    
    if not paciente:
        return jsonify({'message': 'Perfil de paciente não encontrado!'}), 404
    
    documentos = Documento.query.filter_by(paciente_id=paciente.id).all()
    
    return jsonify([{
        'id': d.id,
        'tipo': d.tipo,
        'titulo': d.titulo,
        'data_criacao': d.data_criacao.strftime('%Y-%m-%d %H:%M:%S'),
        'status': d.status,
        'arquivo_url': f"/api/pacientes/documentos/{d.id}/arquivo" if hasattr(d, 'arquivo_path') and d.arquivo_path else None
    } for d in documentos])

@api_bp.route('/pacientes/documentos/<int:documento_id>', methods=['GET'])
@token_required
def get_documento_paciente(current_user, documento_id):
    if not current_user.tem_perfil('paciente'):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    paciente = current_user.paciente
    
    if not paciente:
        return jsonify({'message': 'Perfil de paciente não encontrado!'}), 404
    
    documento = Documento.query.filter_by(id=documento_id, paciente_id=paciente.id).first()
    
    if not documento:
        return jsonify({'message': 'Documento não encontrado!'}), 404
    
    # Atualizar status para visualizado se ainda não foi
    if documento.status == 'disponivel':
        documento.status = 'visualizado'
        documento.data_visualizacao = datetime.utcnow()
        db.session.commit()
    
    return jsonify({
        'id': documento.id,
        'tipo': documento.tipo,
        'titulo': documento.titulo,
        'descricao': documento.descricao,
        'data_criacao': documento.data_criacao.strftime('%Y-%m-%d %H:%M:%S'),
        'status': documento.status,
        'data_visualizacao': documento.data_visualizacao.strftime('%Y-%m-%d %H:%M:%S') if documento.data_visualizacao else None,
        'arquivo_url': f"/api/pacientes/documentos/{documento.id}/arquivo" if hasattr(documento, 'arquivo_path') and documento.arquivo_path else None,
        'medico': documento.profissional.usuario.nome_completo if hasattr(documento, 'profissional') and documento.profissional else None
    })

@api_bp.route('/pacientes/exames-imagem', methods=['GET'])
@token_required
def get_exames_imagem_paciente(current_user):
    if not current_user.tem_perfil('paciente'):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    paciente = current_user.paciente
    
    if not paciente:
        return jsonify({'message': 'Perfil de paciente não encontrado!'}), 404
    
    exames = ExameImagem.query.filter_by(paciente_id=paciente.id).all()
    
    return jsonify([{
        'id': e.id,
        'tipo': e.tipo_exame,
        'data_solicitacao': e.data_exame.strftime('%Y-%m-%d') if e.data_exame else None,
        'status': e.status,
        'laudo_url': f"/api/pacientes/exames-imagem/{e.id}/laudo" if hasattr(e, 'laudo_path') and e.laudo_path else None,
        'imagem_url': f"/api/pacientes/exames-imagem/{e.id}/imagem" if e.orthanc_id else None
    } for e in exames])

@api_bp.route('/pacientes/exames-laboratoriais', methods=['GET'])
@token_required
def get_exames_laboratoriais_paciente(current_user):
    if not current_user.tem_perfil('paciente'):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    paciente = current_user.paciente
    
    if not paciente:
        return jsonify({'message': 'Perfil de paciente não encontrado!'}), 404
    
    # Verificar se o modelo ExameLaboratorial existe
    try:
        exames = ExameLaboratorial.query.filter_by(paciente_id=paciente.id).all()
        
        return jsonify([{
            'id': e.id,
            'tipo': e.tipo_exame,
            'data_solicitacao': e.data_solicitacao.strftime('%Y-%m-%d') if e.data_solicitacao else None,
            'status': e.status,
            'resultado_url': f"/api/pacientes/exames-laboratoriais/{e.id}/resultado" if hasattr(e, 'resultado_path') and e.resultado_path else None
        } for e in exames])
    except Exception as e:
        # Se o modelo não existir, retornar lista vazia
        return jsonify([])

@api_bp.route('/pacientes/cartao-gestante', methods=['GET'])
@token_required
def get_cartao_gestante(current_user):
    if not current_user.tem_perfil('paciente'):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    paciente = current_user.paciente
    
    if not paciente:
        return jsonify({'message': 'Perfil de paciente não encontrado!'}), 404
    
    cartao = CartaoGestante.query.filter_by(paciente_id=paciente.id).first()
    
    if not cartao:
        return jsonify({'message': 'Cartão gestante não encontrado!'}), 404
    
    # Obter consultas, exames e medicações
    consultas = cartao.consultas.all() if hasattr(cartao, 'consultas') else []
    exames = cartao.exames.all() if hasattr(cartao, 'exames') else []
    medicacoes = cartao.medicacoes.all() if hasattr(cartao, 'medicacoes') else []
    
    return jsonify({
        'id': cartao.id,
        'data_ultima_menstruacao': cartao.data_ultima_menstruacao.strftime('%Y-%m-%d') if cartao.data_ultima_menstruacao else None,
        'data_provavel_parto': cartao.data_provavel_parto.strftime('%Y-%m-%d') if cartao.data_provavel_parto else None,
        'idade_gestacional_inicial': cartao.idade_gestacional_inicial if hasattr(cartao, 'idade_gestacional_inicial') else None,
        'peso_inicial': cartao.peso_inicial if hasattr(cartao, 'peso_inicial') else None,
        'altura': cartao.altura if hasattr(cartao, 'altura') else None,
        'imc_inicial': cartao.imc_inicial if hasattr(cartao, 'imc_inicial') else None,
        'tipo_sanguineo': cartao.tipo_sanguineo if hasattr(cartao, 'tipo_sanguineo') else None,
        'fator_rh': cartao.fator_rh if hasattr(cartao, 'fator_rh') else None,
        'consultas': [{
            'id': c.id,
            'data': c.data_consulta.strftime('%Y-%m-%d') if hasattr(c, 'data_consulta') else None,
            'idade_gestacional': c.idade_gestacional if hasattr(c, 'idade_gestacional') else None,
            'peso': c.peso if hasattr(c, 'peso') else None,
            'pressao_arterial': c.pressao_arterial if hasattr(c, 'pressao_arterial') else None,
            'altura_uterina': c.altura_uterina if hasattr(c, 'altura_uterina') else None,
            'batimentos_cardiacos_fetais': c.batimentos_cardiacos_fetais if hasattr(c, 'batimentos_cardiacos_fetais') else None,
            'edema': c.edema if hasattr(c, 'edema') else None,
            'movimentos_fetais': c.movimentos_fetais if hasattr(c, 'movimentos_fetais') else None,
            'observacoes': c.observacoes if hasattr(c, 'observacoes') else None,
            'medico': c.profissional.usuario.nome_completo if hasattr(c, 'profissional') and c.profissional else None
        } for c in consultas],
        'exames': [{
            'id': e.id,
            'tipo': e.tipo_exame if hasattr(e, 'tipo_exame') else None,
            'data_solicitacao': e.data_solicitacao.strftime('%Y-%m-%d') if hasattr(e, 'data_solicitacao') else None,
            'data_realizacao': e.data_realizacao.strftime('%Y-%m-%d') if hasattr(e, 'data_realizacao') and e.data_realizacao else None,
            'resultado': e.resultado if hasattr(e, 'resultado') else None,
            'observacoes': e.observacoes if hasattr(e, 'observacoes') else None
        } for e in exames],
        'medicacoes': [{
            'id': m.id,
            'medicamento': m.medicamento if hasattr(m, 'medicamento') else None,
            'dosagem': m.dosagem if hasattr(m, 'dosagem') else None,
            'posologia': m.posologia if hasattr(m, 'posologia') else None,
            'data_inicio': m.data_inicio.strftime('%Y-%m-%d') if hasattr(m, 'data_inicio') else None,
            'data_fim': m.data_fim.strftime('%Y-%m-%d') if hasattr(m, 'data_fim') and m.data_fim else None,
            'observacoes': m.observacoes if hasattr(m, 'observacoes') else None
        } for m in medicacoes]
    })

# Rotas para médicos
@api_bp.route('/medicos/pacientes', methods=['GET'])
@token_required
def get_pacientes_medico(current_user):
    if not current_user.tem_perfil('medico'):
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    # Verificar se o usuário tem perfil de profissional
    if not hasattr(current_user, 'profissional') or not current_user.profissional:
        return jsonify({'message': 'Perfil de profissional não encontrado!'}), 404
    
    # Obter pacientes que já tiveram consulta com este médico
    from sqlalchemy import distinct
    
    pacientes_ids = db.session.query(distinct(Agendamento.paciente_id)).filter_by(
        profissional_id=current_user.profissional.id
    ).all()
    
    pacientes_ids = [p[0] for p in pacientes_ids]
    pacientes = Paciente.query.filter(Paciente.id.in_(pacientes_ids)).all()
    
    return jsonify([{
        'id': p.id,
        'nome': p.usuario.nome_completo,
        'cpf': p.usuario.cpf,
        'data_nascimento': p.usuario.data_nascimento.strftime('%Y-%m-%d'),
        'email': p.usuario.email,
        'telefone': p.usuario.telefone
    } for p in pacientes])

# Rota para verificar status do servidor
@api_bp.route('/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'online',
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    })
