from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from src.extensions import db
from src.models.usuario import Usuario
from src.models.perfil import Perfil
from src.models.paciente import Paciente
from src.models.documento import Documento
from src.models.cartao_gestante import CartaoGestante, ConsultaPreNatal, ExamePreNatal, MedicacaoGestante
from src.models.agendamento import Agendamento
from src.models.exame_imagem import ExameImagem
import os
import random
import string
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

# Importar o serviço SHOSP se disponível
try:
    from src.services.shosp_service import verificar_cpf_shosp
except ImportError:
    # Fallback para função local se o serviço não estiver disponível
    def verificar_cpf_shosp(cpf):
        """Verifica se o CPF existe no Shosp e retorna os dados do paciente"""
        # Configurações da API Shosp
        shosp_api_url = current_app.config.get('SHOSP_API_URL')
        shosp_api_id = current_app.config.get('SHOSP_API_ID')
        shosp_api_key = current_app.config.get('SHOSP_API_KEY')
        
        if not all([shosp_api_url, shosp_api_id, shosp_api_key]):
            current_app.logger.error("Configurações da API SHOSP incompletas")
            return None
        
        # Consultar API
        headers = {
            'X-SHOSP-ID': shosp_api_id,
            'X-SHOSP-KEY': shosp_api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(f"{shosp_api_url}/pacientes/{cpf}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                current_app.logger.info(f"CPF {cpf} não encontrado no SHOSP")
                return None
            else:
                current_app.logger.error(f"Erro na API SHOSP: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Erro ao conectar com API SHOSP: {str(e)}")
            return None

paciente_bp = Blueprint('paciente', __name__)

# Middleware para verificar se o usuário é paciente
@paciente_bp.before_request
def check_paciente():
    # Exceção para rotas de login e primeiro acesso
    if request.endpoint in ['paciente.login', 'paciente.primeiro_acesso', 'paciente.solicitar_senha_provisoria', 'paciente.trocar_senha_provisoria']:
        return
    
    # Verificar se está logado
    if 'user_id' not in session:
        flash('Acesso restrito. Faça login primeiro.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Verificar se tem perfil de paciente (compatível com múltiplos perfis)
    if session.get('user_tipo') != 'paciente' and session.get('perfil_atual') != 'paciente':
        flash('Acesso restrito a pacientes', 'danger')
        return redirect(url_for('auth.login'))

@paciente_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        senha = request.form.get('senha')
        
        if not cpf or not senha:
            flash('CPF e senha são obrigatórios', 'danger')
            return render_template('paciente/login.html')
        
        # Remover caracteres não numéricos do CPF
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # Buscar usuário pelo CPF
        usuario = Usuario.query.filter_by(cpf=cpf).first()
        
        if not usuario:
            flash('CPF não encontrado', 'danger')
            return render_template('paciente/login.html')
        
        # Verificar se o usuário tem perfil de paciente
        if not usuario.has_perfil('paciente'):
            flash('Usuário não é paciente', 'danger')
            return render_template('paciente/login.html')
        
        # Verificar senha
        if not check_password_hash(usuario.senha, senha):
            flash('Senha incorreta', 'danger')
            return render_template('paciente/login.html')
        
        # Verificar se a conta está ativa
        if not usuario.ativo:
            flash('Conta desativada. Entre em contato com a clínica.', 'danger')
            return render_template('paciente/login.html')
        
        # Verificar se é primeiro acesso (senha provisória)
        if usuario.senha_provisoria:
            # Redirecionar para página de troca de senha
            session['user_id'] = usuario.id
            session['perfil_atual'] = 'paciente'
            session['primeiro_acesso'] = True
            return redirect(url_for('paciente.trocar_senha_provisoria'))
        
        # Login bem-sucedido
        session['user_id'] = usuario.id
        session['perfil_atual'] = 'paciente'
        session['primeiro_acesso'] = False
        
        return redirect(url_for('paciente.dashboard'))
    
    return render_template('paciente/login.html')

@paciente_bp.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso', 'success')
    return redirect(url_for('paciente.login'))

@paciente_bp.route('/dashboard')
def dashboard():
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    if not paciente:
        flash('Dados de paciente não encontrados', 'danger')
        return redirect(url_for('paciente.logout'))
    
    # Contagem de consultas agendadas
    try:
        total_agendamentos = Agendamento.query.filter_by(
            paciente_id=paciente.id, 
            status='agendado'
        ).count()
    except Exception as e:
        current_app.logger.error(f"Erro ao contar agendamentos: {str(e)}")
        total_agendamentos = 0
    
    # Contagem de documentos disponíveis
    try:
        total_documentos = Documento.query.filter_by(
            paciente_id=paciente.id,
            status='disponivel'
        ).count()
    except Exception as e:
        current_app.logger.error(f"Erro ao contar documentos: {str(e)}")
        total_documentos = 0
    
    # Verificar se paciente tem cartão gestante
    try:
        cartao_gestante = CartaoGestante.query.filter_by(
            paciente_id=paciente.id
        ).first()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar cartão gestante: {str(e)}")
        cartao_gestante = None
    
    # Próximos agendamentos (consultas agendadas)
    try:
        consultas_agendadas = Agendamento.query.filter_by(
            paciente_id=paciente.id, 
            status='agendado'
        ).order_by(Agendamento.data_hora_inicio).limit(3).all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar consultas agendadas: {str(e)}")
        consultas_agendadas = []
    
    # Exames pendentes
    try:
        exames_pendentes = ExameImagem.query.filter_by(
            paciente_id=paciente.id,
            status='pendente'
        ).order_by(ExameImagem.data_realizacao.desc()).limit(5).all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar exames pendentes: {str(e)}")
        exames_pendentes = []
    
    # Resultados disponíveis (documentos recentes)
    try:
        resultados_disponiveis = Documento.query.filter_by(
            paciente_id=paciente.id,
            status='disponivel'
        ).order_by(Documento.data_criacao.desc()).limit(3).all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar resultados disponíveis: {str(e)}")
        resultados_disponiveis = []
    
    return render_template('paciente/dashboard.html', 
                          paciente=paciente,
                          total_agendamentos=total_agendamentos,
                          total_documentos=total_documentos,
                          cartao_gestante=cartao_gestante,
                          consultas_agendadas=consultas_agendadas,
                          exames_pendentes=exames_pendentes,
                          resultados_disponiveis=resultados_disponiveis)

@paciente_bp.route('/minhas_consultas')
def minhas_consultas():
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    if not paciente:
        flash('Dados de paciente não encontrados', 'danger')
        return redirect(url_for('paciente.logout'))
    
    # Filtros
    status = request.args.get('status', 'todos')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Consulta base
    query = Agendamento.query.filter_by(paciente_id=paciente.id)
    
    # Aplicar filtros
    if status != 'todos':
        query = query.filter_by(status=status)
    
    if data_inicio:
        query = query.filter(Agendamento.data_hora_inicio >= datetime.strptime(data_inicio, '%Y-%m-%d'))
    
    if data_fim:
        query = query.filter(Agendamento.data_hora_inicio <= datetime.strptime(data_fim + ' 23:59:59', '%Y-%m-%d %H:%M:%S'))
    
    # Ordenar por data (mais recentes primeiro)
    consultas = query.order_by(Agendamento.data_hora_inicio.desc()).all()
    
    # Separar por status para as abas
    consultas_agendadas = [c for c in consultas if c.status == 'agendado']
    consultas_realizadas = [c for c in consultas if c.status == 'realizado']
    consultas_canceladas = [c for c in consultas if c.status == 'cancelado']
    
    return render_template('paciente/minhas_consultas.html', 
                          paciente=paciente,
                          consultas=consultas,
                          consultas_agendadas=consultas_agendadas,
                          consultas_realizadas=consultas_realizadas,
                          consultas_canceladas=consultas_canceladas)

@paciente_bp.route('/agendar_consulta', methods=['GET', 'POST'])
def agendar_consulta():
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    if not paciente:
        flash('Dados de paciente não encontrados', 'danger')
        return redirect(url_for('paciente.logout'))
    
    if request.method == 'POST':
        especialidade_id = request.form.get('especialidade')
        profissional_id = request.form.get('profissional')
        data = request.form.get('data')
        horario = request.form.get('horario')
        motivo = request.form.get('motivo', '')
        convenio = request.form.get('convenio')
        numero_convenio = request.form.get('numero_convenio', '')
        
        # Validação
        if not all([especialidade_id, profissional_id, data, horario]):
            flash('Todos os campos obrigatórios devem ser preenchidos', 'danger')
            return redirect(url_for('paciente.agendar_consulta'))
        
        try:
            # Combinar data e horário
            data_hora = datetime.strptime(f"{data} {horario}", "%Y-%m-%d %H:%M")
            
            # Verificar se a data/hora não é no passado
            if data_hora <= datetime.now():
                flash('Não é possível agendar para data/hora no passado', 'danger')
                return redirect(url_for('paciente.agendar_consulta'))
            
            # Verificar se o horário está disponível
            conflito = Agendamento.query.filter(
                Agendamento.profissional_id == profissional_id,
                Agendamento.data_hora_inicio == data_hora,
                Agendamento.status.in_(['agendado', 'confirmado'])
            ).first()
            
            if conflito:
                flash('Este horário não está mais disponível. Por favor, escolha outro horário.', 'warning')
                return redirect(url_for('paciente.agendar_consulta'))
            
            # Buscar profissional para o email
            from src.models.profissional import Profissional
            profissional = Profissional.query.get(profissional_id)
            
            # Criar agendamento
            novo_agendamento = Agendamento(
                paciente_id=paciente.id,
                profissional_id=profissional_id,
                data_hora_inicio=data_hora,
                data_hora_fim=data_hora + timedelta(minutes=30),  # Assumindo 30 min por consulta
                motivo_consulta=motivo,
                status='agendado',
                convenio=convenio,
                numero_convenio=numero_convenio
            )
            
            db.session.add(novo_agendamento)
            db.session.commit()
            
            # Enviar email para a clínica
            try:
                enviar_email_agendamento_clinica(novo_agendamento, paciente, profissional, 'agendamento')
            except Exception as e:
                current_app.logger.error(f"Erro ao enviar email de agendamento: {str(e)}")
            
            flash('Consulta agendada com sucesso! A clínica foi notificada.', 'success')
            return redirect(url_for('paciente.minhas_consultas'))
            
        except Exception as e:
            current_app.logger.error(f"Erro ao agendar consulta: {str(e)}")
            flash('Erro ao agendar consulta. Tente novamente.', 'danger')
            return redirect(url_for('paciente.agendar_consulta'))
    
    # Buscar especialidades para o form
    try:
        from src.models.especialidade import Especialidade
        especialidades = Especialidade.query.filter(
            Especialidade.id.in_(
                db.session.query(Profissional.especialidade_id).distinct()
            )
        ).all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar especialidades: {str(e)}")
        especialidades = []
    
    return render_template('paciente/agendar_consulta.html', 
                          paciente=paciente,
                          especialidades=especialidades)

@paciente_bp.route('/consulta/<int:id>')
def consulta_detalhes(id):
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    # Obter consulta (verificar se pertence ao paciente)
    consulta = Agendamento.query.filter_by(id=id, paciente_id=paciente.id).first_or_404()
    
    return render_template('paciente/consulta_detalhes.html', 
                          paciente=paciente,
                          consulta=consulta)

@paciente_bp.route('/cancelar_consulta', methods=['POST'])
def cancelar_consulta():
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    consulta_id = request.form.get('consulta_id')
    motivo_cancelamento = request.form.get('motivo_cancelamento')
    outro_motivo = request.form.get('outro_motivo', '')
    
    if not consulta_id or not motivo_cancelamento:
        flash('Dados inválidos para cancelamento', 'danger')
        return redirect(url_for('paciente.minhas_consultas'))
    
    # Obter consulta
    consulta = Agendamento.query.filter_by(id=consulta_id, paciente_id=paciente.id).first()
    
    if not consulta:
        flash('Consulta não encontrada', 'danger')
        return redirect(url_for('paciente.minhas_consultas'))
    
    if consulta.status != 'agendado':
        flash('Apenas consultas agendadas podem ser canceladas', 'danger')
        return redirect(url_for('paciente.minhas_consultas'))
    
    try:
        # Buscar profissional para o email
        from src.models.profissional import Profissional
        profissional = Profissional.query.get(consulta.profissional_id)
        
        # Atualizar status
        consulta.status = 'cancelado'
        consulta.motivo_cancelamento = outro_motivo if motivo_cancelamento == 'Outro' else motivo_cancelamento
        consulta.data_cancelamento = datetime.utcnow()
        
        db.session.commit()
        
        # Enviar email para a clínica
        try:
            enviar_email_agendamento_clinica(consulta, paciente, profissional, 'cancelamento')
        except Exception as e:
            current_app.logger.error(f"Erro ao enviar email de cancelamento: {str(e)}")
        
        flash('Consulta cancelada com sucesso. A clínica foi notificada.', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Erro ao cancelar consulta: {str(e)}")
        flash('Erro ao cancelar consulta. Tente novamente.', 'danger')
    
    return redirect(url_for('paciente.minhas_consultas'))

@paciente_bp.route('/reagendar_consulta/<int:id>')
def reagendar_consulta(id):
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    # Obter consulta cancelada
    consulta = Agendamento.query.filter_by(id=id, paciente_id=paciente.id).first_or_404()
    
    if consulta.status != 'cancelado':
        flash('Apenas consultas canceladas podem ser reagendadas', 'danger')
        return redirect(url_for('paciente.minhas_consultas'))
    
    # Redirecionar para agendamento com dados pré-preenchidos
    flash('Reagende sua consulta selecionando nova data e horário', 'info')
    return redirect(url_for('paciente.agendar_consulta'))

@paciente_bp.route('/meus_exames')
def meus_exames():
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    if not paciente:
        flash('Dados de paciente não encontrados', 'danger')
        return redirect(url_for('paciente.logout'))
    
    # Filtros
    status = request.args.get('status', 'todos')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Consulta base
    query = ExameImagem.query.filter_by(paciente_id=paciente.id)
    
    # Aplicar filtros
    if status != 'todos':
        query = query.filter_by(status=status)
    
    if data_inicio:
        query = query.filter(ExameImagem.data_realizacao >= datetime.strptime(data_inicio, '%Y-%m-%d'))
    
    if data_fim:
        query = query.filter(ExameImagem.data_realizacao <= datetime.strptime(data_fim + ' 23:59:59', '%Y-%m-%d %H:%M:%S'))
    
    # Ordenar por data (mais recentes primeiro)
    exames = query.order_by(ExameImagem.data_realizacao.desc()).all()
    
    # Separar por status para as abas
    exames_pendentes = [e for e in exames if e.status == 'pendente']
    exames_coletados = [e for e in exames if e.status == 'coletado']
    exames_resultados = [e for e in exames if e.status == 'resultado_disponivel']
    
    return render_template('paciente/meus_exames.html', 
                          paciente=paciente,
                          exames=exames,
                          exames_pendentes=exames_pendentes,
                          exames_coletados=exames_coletados,
                          exames_resultados=exames_resultados)

@paciente_bp.route('/exame/<int:id>')
def exame_detalhes(id):
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    # Obter exame (verificar se pertence ao paciente)
    exame = ExameImagem.query.filter_by(id=id, paciente_id=paciente.id).first_or_404()
    
    return render_template('paciente/exame_detalhes.html', 
                          paciente=paciente,
                          exame=exame)

@paciente_bp.route('/visualizar_resultado/<int:id>')
def visualizar_resultado(id):
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    # Obter exame (verificar se pertence ao paciente)
    exame = ExameImagem.query.filter_by(id=id, paciente_id=paciente.id).first_or_404()
    
    if exame.status != 'resultado_disponivel':
        flash('Resultado ainda não está disponível', 'warning')
        return redirect(url_for('paciente.meus_exames'))
    
    # Buscar documento de resultado
    documento = Documento.query.filter_by(
        exame_imagem_id=exame.id,
        tipo='resultado'
    ).first()
    
    if not documento:
        flash('Documento de resultado não encontrado', 'danger')
        return redirect(url_for('paciente.meus_exames'))
    
    return render_template('paciente/visualizar_resultado.html', 
                          paciente=paciente,
                          exame=exame,
                          documento=documento)

@paciente_bp.route('/primeiro_acesso', methods=['GET', 'POST'])
def primeiro_acesso():
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        
        if not cpf:
            flash('CPF é obrigatório', 'danger')
            return render_template('paciente/primeiro_acesso.html')
        
        # Remover caracteres não numéricos do CPF
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # Verificar se o CPF já está cadastrado
        usuario = Usuario.query.filter_by(cpf=cpf).first()
        
        if usuario:
            # Se já existe usuário, verificar se tem perfil de paciente
            if usuario.has_perfil('paciente'):
                # Verificar se já tem senha definida
                if usuario.senha_provisoria:
                    flash('Você já possui uma senha provisória. Verifique seu e-mail ou WhatsApp.', 'info')
                else:
                    flash('Você já possui cadastro. Faça login com sua senha.', 'info')
                
                return redirect(url_for('paciente.login'))
            else:
                flash('CPF encontrado, mas não está associado a um paciente.', 'danger')
                return render_template('paciente/primeiro_acesso.html')
        
        # Verificar se o CPF existe no Shosp
        paciente_shosp = verificar_cpf_shosp(cpf)
        
        if not paciente_shosp:
            flash('CPF não encontrado no sistema da clínica. Entre em contato para cadastro.', 'danger')
            return render_template('paciente/primeiro_acesso.html')
        
        # Criar usuário e paciente com dados do Shosp
        novo_usuario = Usuario(
            nome_completo=paciente_shosp['nome'],
            cpf=cpf,
            data_nascimento=datetime.strptime(paciente_shosp['data_nascimento'], '%Y-%m-%d').date(),
            email=paciente_shosp['email'],
            telefone=paciente_shosp['telefone'],
            ativo=True
        )
        
        # Buscar ou criar perfil paciente
        perfil_paciente = Perfil.query.filter_by(nome='paciente').first()
        if not perfil_paciente:
            perfil_paciente = Perfil(nome='paciente', descricao='Paciente da clínica')
            db.session.add(perfil_paciente)
            db.session.flush()
        
        # Adicionar perfil ao usuário
        novo_usuario.perfis.append(perfil_paciente)
        
        # Gerar senha provisória
        senha_provisoria = gerar_senha_provisoria()
        novo_usuario.senha = generate_password_hash(senha_provisoria)
        novo_usuario.senha_provisoria = True
        novo_usuario.data_expiracao_senha = datetime.utcnow() + timedelta(hours=24)
        
        db.session.add(novo_usuario)
        db.session.flush()  # Para obter o ID do usuário
        
        novo_paciente = Paciente(
            usuario_id=novo_usuario.id,
            cartao_sus=paciente_shosp.get('cartao_sus'),
            convenio=paciente_shosp.get('convenio'),
            numero_convenio=paciente_shosp.get('numero_convenio')
        )
        
        db.session.add(novo_paciente)
        db.session.commit()
        
        # Enviar senha provisória por e-mail e/ou WhatsApp
        enviar_senha_provisoria(novo_usuario, senha_provisoria)
        
        flash('Cadastro realizado com sucesso! Uma senha provisória foi enviada para seu e-mail e/ou WhatsApp.', 'success')
        return redirect(url_for('paciente.login'))
    
    return render_template('paciente/primeiro_acesso.html')

@paciente_bp.route('/solicitar_senha_provisoria', methods=['GET', 'POST'])
def solicitar_senha_provisoria():
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        
        if not cpf:
            flash('CPF é obrigatório', 'danger')
            return render_template('paciente/solicitar_senha_provisoria.html')
        
        # Remover caracteres não numéricos do CPF
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # Buscar usuário pelo CPF
        usuario = Usuario.query.filter_by(cpf=cpf).first()
        
        if not usuario:
            flash('CPF não encontrado', 'danger')
            return render_template('paciente/solicitar_senha_provisoria.html')
        
        # Verificar se o usuário tem perfil de paciente
        if not usuario.has_perfil('paciente'):
            flash('Usuário não é paciente', 'danger')
            return render_template('paciente/solicitar_senha_provisoria.html')
        
        # Gerar nova senha provisória
        senha_provisoria = gerar_senha_provisoria()
        usuario.senha = generate_password_hash(senha_provisoria)
        usuario.senha_provisoria = True
        usuario.data_expiracao_senha = datetime.utcnow() + timedelta(hours=24)
        
        db.session.commit()
        
        # Enviar senha provisória por e-mail e/ou WhatsApp
        enviar_senha_provisoria(usuario, senha_provisoria)
        
        flash('Uma nova senha provisória foi enviada para seu e-mail e/ou WhatsApp.', 'success')
        return redirect(url_for('paciente.login'))
    
    return render_template('paciente/solicitar_senha_provisoria.html')

@paciente_bp.route('/trocar_senha_provisoria', methods=['GET', 'POST'])
def trocar_senha_provisoria():
    if 'user_id' not in session:
        flash('Você precisa estar logado para trocar a senha', 'danger')
        return redirect(url_for('paciente.login'))
    
    usuario = Usuario.query.get(session['user_id'])
    
    if not usuario:
        flash('Usuário não encontrado', 'danger')
        session.clear()
        return redirect(url_for('paciente.login'))
    
    if not usuario.senha_provisoria:
        flash('Você não possui senha provisória para trocar', 'warning')
        return redirect(url_for('paciente.dashboard'))
    
    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        if not senha_atual or not nova_senha or not confirmar_senha:
            flash('Todos os campos são obrigatórios', 'danger')
            return render_template('paciente/trocar_senha_provisoria.html')
        
        # Verificar senha atual
        if not check_password_hash(usuario.senha, senha_atual):
            flash('Senha atual incorreta', 'danger')
            return render_template('paciente/trocar_senha_provisoria.html')
        
        # Verificar se as senhas coincidem
        if nova_senha != confirmar_senha:
            flash('As senhas não coincidem', 'danger')
            return render_template('paciente/trocar_senha_provisoria.html')
        
        # Verificar requisitos de segurança da senha
        if len(nova_senha) < 8:
            flash('A senha deve ter pelo menos 8 caracteres', 'danger')
            return render_template('paciente/trocar_senha_provisoria.html')
        
        # Atualizar senha
        usuario.senha = generate_password_hash(nova_senha)
        usuario.senha_provisoria = False
        usuario.data_expiracao_senha = None
        
        db.session.commit()
        
        # Atualizar sessão
        session['primeiro_acesso'] = False
        
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('paciente.dashboard'))
    
    return render_template('paciente/trocar_senha_provisoria.html')

@paciente_bp.route('/meus_dados')
def meus_dados():
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    if not paciente:
        flash('Dados de paciente não encontrados', 'danger')
        return redirect(url_for('paciente.logout'))
    
    return render_template('paciente/meus_dados.html', paciente=paciente)

@paciente_bp.route('/alterar_senha', methods=['GET', 'POST'])
def alterar_senha():
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    if not paciente:
        flash('Dados de paciente não encontrados', 'danger')
        return redirect(url_for('paciente.logout'))
    
    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        if not senha_atual or not nova_senha or not confirmar_senha:
            flash('Todos os campos são obrigatórios', 'danger')
            return render_template('paciente/alterar_senha.html', paciente=paciente)
        
        # Verificar senha atual
        if not check_password_hash(usuario.senha, senha_atual):
            flash('Senha atual incorreta', 'danger')
            return render_template('paciente/alterar_senha.html', paciente=paciente)
        
        # Verificar se as senhas coincidem
        if nova_senha != confirmar_senha:
            flash('As senhas não coincidem', 'danger')
            return render_template('paciente/alterar_senha.html', paciente=paciente)
        
        # Verificar requisitos de segurança da senha
        if len(nova_senha) < 8:
            flash('A senha deve ter pelo menos 8 caracteres', 'danger')
            return render_template('paciente/alterar_senha.html', paciente=paciente)
        
        # Atualizar senha
        usuario.senha = generate_password_hash(nova_senha)
        db.session.commit()
        
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('paciente.meus_dados'))
    
    return render_template('paciente/alterar_senha.html', paciente=paciente)

@paciente_bp.route('/meus_documentos')
def meus_documentos():
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    if not paciente:
        flash('Dados de paciente não encontrados', 'danger')
        return redirect(url_for('paciente.logout'))
    
    # Filtros
    tipo = request.args.get('tipo', 'todos')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    # Consulta base
    query = Documento.query.filter_by(paciente_id=paciente.id)
    
    # Aplicar filtros
    if tipo != 'todos':
        query = query.filter_by(tipo=tipo)
    
    if data_inicio:
        query = query.filter(Documento.data_criacao >= datetime.strptime(data_inicio, '%Y-%m-%d'))
    
    if data_fim:
        query = query.filter(Documento.data_criacao <= datetime.strptime(data_fim + ' 23:59:59', '%Y-%m-%d %H:%M:%S'))
    
    # Ordenar por data (mais recentes primeiro)
    documentos = query.order_by(Documento.data_criacao.desc()).all()
    
    return render_template('paciente/meus_documentos.html', 
                          paciente=paciente,
                          documentos=documentos)

@paciente_bp.route('/visualizar_documento/<int:id>')
def visualizar_documento(id):
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    if not paciente:
        flash('Dados de paciente não encontrados', 'danger')
        return redirect(url_for('paciente.logout'))
    
    # Obter documento
    documento = Documento.query.filter_by(
        id=id,
        paciente_id=paciente.id
    ).first_or_404()
    
    # Atualizar status para visualizado se ainda não foi
    if documento.status == 'disponivel':
        documento.status = 'visualizado'
        documento.data_visualizacao = datetime.utcnow()
        db.session.commit()
    
    # Verificar se o arquivo existe
    if not os.path.exists(documento.arquivo_caminho):
        flash('Arquivo não encontrado', 'danger')
        return redirect(url_for('paciente.meus_documentos'))
    
    return render_template('paciente/visualizar_documento.html', 
                          paciente=paciente,
                          documento=documento)

@paciente_bp.route('/download_documento/<int:id>')
def download_documento(id):
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    if not paciente:
        flash('Dados de paciente não encontrados', 'danger')
        return redirect(url_for('paciente.logout'))
    
    # Obter documento
    documento = Documento.query.filter_by(
        id=id,
        paciente_id=paciente.id
    ).first_or_404()
    
    # Verificar se o arquivo existe
    if not os.path.exists(documento.arquivo_caminho):
        flash('Arquivo não encontrado', 'danger')
        return redirect(url_for('paciente.meus_documentos'))
    
    # Atualizar status para visualizado se ainda não foi
    if documento.status == 'disponivel':
        documento.status = 'visualizado'
        documento.data_visualizacao = datetime.utcnow()
        db.session.commit()
    
    # Enviar arquivo
    return send_file(
        documento.arquivo_caminho,
        as_attachment=True,
        download_name=f"{documento.titulo}.pdf"
    )

@paciente_bp.route('/meu_cartao_gestante')
def meu_cartao_gestante():
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    if not paciente:
        flash('Dados de paciente não encontrados', 'danger')
        return redirect(url_for('paciente.logout'))
    
    # Verificar se já existe cartão gestante
    cartao = CartaoGestante.query.filter_by(paciente_id=paciente.id).first()
    
    if not cartao:
        flash('Você ainda não possui um cartão gestante. Solicite ao seu médico na próxima consulta.', 'info')
        return redirect(url_for('paciente.dashboard'))
    
    # Obter consultas pré-natal
    consultas = ConsultaPreNatal.query.filter_by(
        cartao_gestante_id=cartao.id
    ).order_by(ConsultaPreNatal.data_consulta.desc()).all()
    
    # Obter exames
    exames = ExamePreNatal.query.filter_by(
        cartao_gestante_id=cartao.id
    ).order_by(ExamePreNatal.data_solicitacao.desc()).all()
    
    # Obter medicações
    medicacoes = MedicacaoGestante.query.filter_by(
        cartao_gestante_id=cartao.id
    ).all()
    
    return render_template('paciente/meu_cartao_gestante.html', 
                          paciente=paciente,
                          cartao=cartao,
                          consultas=consultas,
                          exames=exames,
                          medicacoes=medicacoes)

@paciente_bp.route('/api/profissionais/<int:especialidade_id>')
def api_profissionais_por_especialidade(especialidade_id):
    """API para buscar profissionais por especialidade"""
    try:
        from src.models.profissional import Profissional
        
        profissionais = Profissional.query.filter_by(
            especialidade_id=especialidade_id
        ).join(Usuario).filter(Usuario.ativo == True).all()
        
        resultado = []
        for prof in profissionais:
            resultado.append({
                'id': prof.id,
                'nome': prof.usuario.nome_completo,
                'registro': prof.registro_profissional
            })
        
        return jsonify(resultado)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar profissionais: {str(e)}")
        return jsonify([]), 500

@paciente_bp.route('/api/horarios-disponiveis')
def api_horarios_disponiveis():
    """API para buscar horários disponíveis de um profissional em uma data"""
    try:
        profissional_id = request.args.get('profissional_id')
        data = request.args.get('data')
        
        if not profissional_id or not data:
            return jsonify([]), 400
        
        # Converter data string para objeto date
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        dia_semana = data_obj.weekday()  # 0=segunda, 6=domingo
        
        # Buscar disponibilidade do profissional para o dia da semana
        from src.models.disponibilidade import DisponibilidadeProfissional
        
        disponibilidades = DisponibilidadeProfissional.query.filter_by(
            profissional_id=profissional_id,
            dia_semana=dia_semana,
            ativo=True
        ).all()
        
        horarios_disponiveis = []
        
        for disp in disponibilidades:
            # Gerar horários com base no intervalo
            hora_atual = datetime.combine(data_obj, disp.hora_inicio)
            hora_fim = datetime.combine(data_obj, disp.hora_fim)
            
            while hora_atual < hora_fim:
                # Verificar se o horário já está ocupado
                agendamento_existente = Agendamento.query.filter(
                    Agendamento.profissional_id == profissional_id,
                    Agendamento.data_hora_inicio == hora_atual,
                    Agendamento.status.in_(['agendado', 'confirmado'])
                ).first()
                
                if not agendamento_existente:
                    horarios_disponiveis.append({
                        'horario': hora_atual.strftime('%H:%M'),
                        'disponivel': True
                    })
                
                # Avançar para o próximo horário
                hora_atual += timedelta(minutes=disp.intervalo_minutos)
        
        # Ordenar horários
        horarios_disponiveis.sort(key=lambda x: x['horario'])
        
        return jsonify(horarios_disponiveis)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar horários disponíveis: {str(e)}")
        return jsonify([]), 500
    # Obter o paciente logado
    user_id = session.get('user_id')
    usuario = Usuario.query.get(user_id)
    
    if not usuario or not usuario.has_perfil('paciente'):
        flash('Perfil de paciente não encontrado', 'danger')
        return redirect(url_for('paciente.logout'))
    
    paciente = usuario.paciente
    
    if not paciente:
        flash('Dados de paciente não encontrados', 'danger')
        return redirect(url_for('paciente.logout'))
    
    # Obter agendamentos
    agendamentos = Agendamento.query.filter_by(
        paciente_id=paciente.id
    ).order_by(Agendamento.data_hora_inicio.desc()).all()
    
    return render_template('paciente/meus_agendamentos.html', 
                          paciente=paciente,
                          agendamentos=agendamentos)

# Funções auxiliares

def gerar_senha_provisoria(tamanho=8):
    """Gera uma senha provisória aleatória"""
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for i in range(tamanho))

def enviar_senha_provisoria(usuario, senha_provisoria):
    """Envia a senha provisória por e-mail e/ou WhatsApp"""
    # Enviar por e-mail
    if usuario.email:
        try:
            enviar_email_senha_provisoria(usuario, senha_provisoria)
        except Exception as e:
            current_app.logger.error(f"Erro ao enviar e-mail: {str(e)}")
    
    # Enviar por WhatsApp
    if usuario.telefone:
        try:
            enviar_whatsapp_senha_provisoria(usuario, senha_provisoria)
        except Exception as e:
            current_app.logger.error(f"Erro ao enviar WhatsApp: {str(e)}")

def enviar_email_senha_provisoria(usuario, senha_provisoria):
    """Envia a senha provisória por e-mail"""
    # Configurações de e-mail
    smtp_server = current_app.config.get('SMTP_SERVER')
    smtp_port = current_app.config.get('SMTP_PORT')
    smtp_user = current_app.config.get('SMTP_USER')
    smtp_password = current_app.config.get('SMTP_PASSWORD')
    sender_email = current_app.config.get('SENDER_EMAIL')
    
    # Criar mensagem
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = usuario.email
    msg['Subject'] = 'Sua senha provisória para acesso ao sistema da clínica'
    
    # Corpo do e-mail
    body = f"""
    <html>
    <body>
        <h2>Olá, {usuario.nome_completo}!</h2>
        <p>Sua senha provisória para acesso ao sistema da clínica é: <strong>{senha_provisoria}</strong></p>
        <p>Esta senha é válida por 24 horas. Ao fazer login, você será solicitado a criar uma nova senha.</p>
        <p>Atenciosamente,<br>Equipe da Clínica</p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(body, 'html'))
    
    # Enviar e-mail
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

def enviar_whatsapp_senha_provisoria(usuario, senha_provisoria):
    """Envia a senha provisória por WhatsApp"""
    # Configurações de WhatsApp
    whatsapp_api_url = current_app.config.get('WHATSAPP_API_URL')
    whatsapp_api_token = current_app.config.get('WHATSAPP_API_TOKEN')
    
    # Formatar número de telefone (remover caracteres não numéricos)
    telefone = ''.join(filter(str.isdigit, usuario.telefone))
    
    # Mensagem
    mensagem = f"Olá, {usuario.nome_completo}! Sua senha provisória para acesso ao sistema da clínica é: {senha_provisoria}. Esta senha é válida por 24 horas. Ao fazer login, você será solicitado a criar uma nova senha."
    
    # Enviar mensagem
    headers = {
        'Authorization': f'Bearer {whatsapp_api_token}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'phone': telefone,
        'message': mensagem
    }
    
    response = requests.post(whatsapp_api_url, json=data, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Erro ao enviar WhatsApp: {response.text}")
