from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from src.extensions import db
from src.models.usuario import Usuario
from src.models.perfil import Perfil
from src.models.paciente import Paciente
from datetime import datetime, timedelta
import random
import string
import re

# IMPORTAÇÃO ATUALIZADA - Usar serviço unificado de email
from src.services.unified_email_service import enviar_senha_provisoria

auth_bp = Blueprint('auth', __name__)


def login_required(view_func):
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página', 'danger')
            return redirect(url_for('auth.login'))
        return view_func(*args, **kwargs)
    wrapped_view.__name__ = view_func.__name__
    return wrapped_view


def limpar_cpf(cpf):
    """Remove caracteres não numéricos do CPF"""
    if cpf:
        return re.sub(r'[^0-9]', '', cpf)
    return ''


def formatar_cpf(cpf):
    """Formata CPF com pontos e traço"""
    if cpf and len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            # Aceitar apenas CPF e senha
            cpf = request.form.get('cpf')
            senha = request.form.get('senha')

            current_app.logger.info(f"Tentativa de login para CPF: {cpf}")

            if not cpf or not senha:
                flash('CPF e senha são obrigatórios', 'danger')
                return render_template('auth/login.html')

            # Limpar CPF
            cpf = limpar_cpf(cpf)
            current_app.logger.info(f"CPF limpo: {cpf}")
            
            if len(cpf) != 11:
                flash('CPF deve ter 11 dígitos', 'danger')
                return render_template('auth/login.html')
            
            usuario = Usuario.query.filter_by(cpf=cpf).first()

            current_app.logger.info(f"Usuário encontrado: {usuario.nome_completo if usuario else 'Não encontrado'}")

            if not usuario:
                flash('CPF não encontrado. Se você ainda não é paciente, faça seu cadastro.', 'danger')
                return render_template('auth/login.html')

            # Verificar senha
            if not check_password_hash(usuario.senha, senha):
                current_app.logger.info("Senha incorreta")
                flash('Senha incorreta', 'danger')
                return render_template('auth/login.html')

            if not usuario.ativo:
                flash('Conta desativada. Entre em contato com a clínica.', 'danger')
                return render_template('auth/login.html')

            current_app.logger.info(f"Login bem-sucedido para usuário: {usuario.nome_completo}")

            # Verificar se tem senha provisória
            if usuario.senha_provisoria:
                current_app.logger.info("Usuário tem senha provisória - redirecionando para troca")
                session['user_id'] = usuario.id
                session['user_name'] = usuario.nome_completo
                session['primeiro_acesso'] = True
                return redirect(url_for('auth.trocar_senha_provisoria'))

            # Login bem-sucedido
            session['user_id'] = usuario.id
            session['user_name'] = usuario.nome_completo
            session['primeiro_acesso'] = False

            # Atualizar último acesso
            try:
                usuario.ultimo_acesso = datetime.utcnow()
                db.session.commit()
            except Exception as e:
                current_app.logger.warning(f"Erro ao atualizar último acesso: {str(e)}")

            # Verificar perfis do usuário
            try:
                # Buscar perfis associados ao usuário
                perfis_usuario = list(usuario.perfis) if hasattr(usuario, 'perfis') else []
                    
                current_app.logger.info(f"Perfis encontrados: {[p.nome for p in perfis_usuario]}")
                
                if len(perfis_usuario) > 1:
                    # Se tem múltiplos perfis, ir para seleção
                    current_app.logger.info("Usuário tem múltiplos perfis - redirecionando para seleção")
                    session['perfis_disponiveis'] = [
                        {'id': p.id, 'nome': p.nome, 'descricao': p.descricao} 
                        for p in perfis_usuario
                    ]
                    return redirect(url_for('auth.selecionar_perfil'))
                elif len(perfis_usuario) == 1:
                    # Se tem apenas um perfil, usar ele diretamente
                    perfil_usado = perfis_usuario[0].nome
                    session['user_tipo'] = perfil_usado
                    session['perfil_atual'] = perfil_usado
                    current_app.logger.info(f"Perfil único encontrado: {perfil_usado}")
                else:
                    # Se não tem perfil associado, definir como paciente por padrão
                    perfil_usado = 'paciente'
                    session['user_tipo'] = perfil_usado
                    session['perfil_atual'] = perfil_usado
                    current_app.logger.info(f"Nenhum perfil encontrado, usando padrão: {perfil_usado}")
                        
            except Exception as e:
                current_app.logger.error(f"Erro ao obter perfis: {str(e)}")
                # Usar paciente como padrão
                perfil_usado = 'paciente'
                session['user_tipo'] = perfil_usado
                session['perfil_atual'] = perfil_usado
                current_app.logger.info(f"Erro ao buscar perfis, usando padrão: {perfil_usado}")

            # Redirecionar com base no perfil
            perfil_usado = session.get('user_tipo', 'paciente')
            current_app.logger.info(f"Redirecionando para dashboard: {perfil_usado}")
            
            try:
                # Usar o mesmo padrão do main.py para redirecionamento
                if perfil_usado == 'admin':
                    return redirect('/admin/')
                elif perfil_usado == 'medico':
                    return redirect('/medico/')
                elif perfil_usado == 'assistente':
                    return redirect('/assistente/')
                elif perfil_usado == 'paciente':
                    return redirect('/paciente/')
                else:
                    flash('Tipo de usuário não reconhecido', 'danger')
                    return redirect(url_for('auth.login'))
            except Exception as e:
                current_app.logger.error(f"Erro ao redirecionar para dashboard: {str(e)}")
                flash('Erro interno. Dashboard não encontrado. Contate o administrador.', 'danger')
                return redirect(url_for('auth.login'))
                
        except Exception as e:
            current_app.logger.error(f"Erro geral no login: {str(e)}")
            flash('Erro interno do sistema. Tente novamente.', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('auth/login.html')


@auth_bp.route('/selecionar_perfil', methods=['GET', 'POST'])
@login_required
def selecionar_perfil():
    """Tela para seleção de perfil quando usuário tem múltiplos perfis"""
    current_app.logger.info("Acessando página de seleção de perfil")
    
    if 'perfis_disponiveis' not in session:
        current_app.logger.info("Perfis não encontrados na sessão, redirecionando para login")
        return redirect(url_for('auth.login'))
    
    perfis_disponiveis = session['perfis_disponiveis']
    current_app.logger.info(f"Perfis disponíveis: {perfis_disponiveis}")
    
    if request.method == 'POST':
        perfil_id = request.form.get('perfil_id')
        current_app.logger.info(f"Perfil selecionado ID: {perfil_id}")
        
        # Encontrar o perfil selecionado
        perfil_selecionado = None
        for perfil in perfis_disponiveis:
            if str(perfil['id']) == str(perfil_id):
                perfil_selecionado = perfil['nome']
                break
        
        current_app.logger.info(f"Perfil selecionado nome: {perfil_selecionado}")
        
        if not perfil_selecionado:
            flash('Perfil inválido', 'danger')
            return render_template('auth/selecionar_perfil.html', perfis=perfis_disponiveis)
        
        # Definir o perfil selecionado na sessão
        session['user_tipo'] = perfil_selecionado
        session['perfil_atual'] = perfil_selecionado
        
        # Remover perfis da sessão
        session.pop('perfis_disponiveis', None)
        
        current_app.logger.info(f"Redirecionando para dashboard do perfil: {perfil_selecionado}")
        
        # Redirecionar para o dashboard correspondente
        try:
            if perfil_selecionado == 'admin':
                return redirect('/admin/')
            elif perfil_selecionado == 'medico':
                return redirect('/medico/')
            elif perfil_selecionado == 'assistente':
                return redirect('/assistente/')
            elif perfil_selecionado == 'paciente':
                return redirect('/paciente/')
            else:
                flash('Tipo de usuário não reconhecido', 'danger')
                return redirect(url_for('auth.login'))
        except Exception as e:
            current_app.logger.error(f"Erro ao redirecionar para dashboard: {str(e)}")
            flash('Erro interno. Dashboard não encontrado. Contate o administrador.', 'danger')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/selecionar_perfil.html', perfis=perfis_disponiveis)


@auth_bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        try:
            # Obter dados do formulário
            nome_completo = request.form.get('nome_completo')
            data_nascimento = request.form.get('data_nascimento')
            cpf = request.form.get('cpf')
            email = request.form.get('email')
            celular = request.form.get('celular')
            como_conheceu = request.form.get('como_conheceu')
            
            # Campos opcionais
            endereco = request.form.get('endereco', '')
            nome_mae = request.form.get('nome_mae', '')
            sexo = request.form.get('sexo', '')
            cartao_sus = request.form.get('cartao_sus', '')
            convenio = request.form.get('convenio', '')
            numero_convenio = request.form.get('numero_convenio', '')
            
            # Validar campos obrigatórios
            if not nome_completo or not data_nascimento or not cpf or not email or not celular or not como_conheceu:
                flash('Todos os campos obrigatórios devem ser preenchidos', 'danger')
                return render_template('auth/cadastro.html')
            
            # Limpar CPF
            cpf = limpar_cpf(cpf)
            
            if len(cpf) != 11:
                flash('CPF deve conter 11 dígitos', 'danger')
                return render_template('auth/cadastro.html')
            
            # Verificar se o CPF já está cadastrado no sistema
            usuario_existente = Usuario.query.filter_by(cpf=cpf).first()
            if usuario_existente:
                flash('CPF já cadastrado. Por favor, faça login.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Criar usuário no sistema local
            novo_usuario = Usuario(
                nome_completo=nome_completo,
                cpf=cpf,
                data_nascimento=datetime.strptime(data_nascimento, '%Y-%m-%d').date(),
                email=email,
                telefone=celular,
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
            
            # Criar paciente
            novo_paciente = Paciente(
                usuario_id=novo_usuario.id,
                cartao_sus=cartao_sus,
                convenio=convenio,
                numero_convenio=numero_convenio
            )
            
            # Verificar se o campo observacoes existe antes de definir
            if hasattr(novo_paciente, 'observacoes'):
                novo_paciente.observacoes = f"Como conheceu: {como_conheceu}. Cadastrado via sistema em {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}"
            
            db.session.add(novo_paciente)
            db.session.commit()
            
            # Enviar senha provisória por e-mail usando o serviço unificado
            try:
                enviar_senha_provisoria(novo_usuario, senha_provisoria)
                flash('Cadastro realizado com sucesso! Uma senha provisória foi enviada para seu e-mail.', 'success')
            except Exception as e:
                current_app.logger.error(f"Erro ao enviar senha provisória: {str(e)}")
                flash(f'Cadastro realizado! Sua senha provisória é: {senha_provisoria}', 'success')
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f"Erro no cadastro: {str(e)}")
            db.session.rollback()
            flash('Erro interno no cadastro. Tente novamente.', 'danger')
            return render_template('auth/cadastro.html')
    
    return render_template('auth/cadastro.html')


@auth_bp.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    """Rota para recuperação de senha - Envia senha provisória por email"""
    if request.method == 'POST':
        try:
            cpf = request.form.get('cpf')
            
            if not cpf:
                flash('CPF é obrigatório', 'danger')
                return render_template('auth/recuperar_senha.html')
            
            # Limpar CPF
            cpf = limpar_cpf(cpf)
            
            if len(cpf) != 11:
                flash('CPF deve ter 11 dígitos', 'danger')
                return render_template('auth/recuperar_senha.html')
            
            current_app.logger.info(f"Iniciando recuperação de senha para CPF: {cpf}")
            
            # Buscar usuário pelo CPF na base local
            usuario = Usuario.query.filter_by(cpf=cpf).first()
            
            if usuario:
                # USUÁRIO EXISTE LOCALMENTE - Gerar nova senha provisória
                current_app.logger.info(f"Usuário encontrado localmente para recuperação: {cpf}")
                
                # Gerar nova senha provisória
                senha_provisoria = gerar_senha_provisoria()
                usuario.senha = generate_password_hash(senha_provisoria)
                usuario.senha_provisoria = True
                usuario.data_expiracao_senha = datetime.utcnow() + timedelta(hours=24)
                
                db.session.commit()
                
                # Enviar senha provisória usando o serviço unificado de email
                try:
                    current_app.logger.info(f"Tentando enviar senha provisória para: {usuario.email}")
                    enviar_senha_provisoria(usuario, senha_provisoria)
                    current_app.logger.info("Email de senha provisória enviado com sucesso")
                    flash('Uma nova senha provisória foi enviada para seu e-mail.', 'success')
                except Exception as e:
                    current_app.logger.error(f"Erro ao enviar senha provisória por email: {str(e)}")
                    # Mostrar a senha na tela como fallback
                    flash(f'Erro no envio do e-mail. Sua nova senha provisória é: {senha_provisoria}. Anote esta senha pois ela expira em 24 horas.', 'warning')
                
                return redirect(url_for('auth.login'))
            
            else:
                # USUÁRIO NÃO EXISTE LOCALMENTE - Verificar no SHOSP
                current_app.logger.info(f"Usuário não encontrado localmente, verificando SHOSP: {cpf}")
                
                # Tentar importar o serviço SHOSP
                try:
                    # Verificar se o CPF existe no Shosp
                    from src.services.shosp_service import shosp_service
                    paciente_shosp = shosp_service.buscar_paciente_por_cpf(cpf)
                    
                    if paciente_shosp:
                        current_app.logger.info(f"Paciente encontrado no SHOSP, criando usuário local: {cpf}")
                        
                        # PACIENTE ENCONTRADO NO SHOSP - Criar usuário local
                        
                        # Buscar ou criar perfil paciente
                        perfil_paciente = Perfil.query.filter_by(nome='paciente').first()
                        if not perfil_paciente:
                            perfil_paciente = Perfil(nome='paciente', descricao='Paciente da clínica')
                            db.session.add(perfil_paciente)
                            db.session.flush()
                        
                        # Gerar senha provisória
                        senha_provisoria = gerar_senha_provisoria()
                        
                        # Criar usuário com dados do SHOSP
                        novo_usuario = Usuario(
                            nome_completo=paciente_shosp.get('nome', ''),
                            cpf=cpf,
                            data_nascimento=datetime.strptime(paciente_shosp.get('dataNascimento', '1990-01-01'), '%Y-%m-%d').date(),
                            email=paciente_shosp.get('email', ''),
                            telefone=paciente_shosp.get('telefone', paciente_shosp.get('celular', '')),
                            senha=generate_password_hash(senha_provisoria),
                            ativo=True,
                            senha_provisoria=True,
                            data_expiracao_senha=datetime.utcnow() + timedelta(hours=24)
                        )
                        
                        # Adicionar perfil ao usuário
                        novo_usuario.perfis.append(perfil_paciente)
                        
                        db.session.add(novo_usuario)
                        db.session.flush()  # Para obter o ID do usuário
                        
                        # Criar registro de paciente
                        novo_paciente = Paciente(
                            usuario_id=novo_usuario.id,
                            cartao_sus=paciente_shosp.get('cartaoSus', ''),
                            convenio=paciente_shosp.get('convenio', ''),
                            numero_convenio=paciente_shosp.get('numeroConvenio', '')
                        )
                        
                        # Adicionar observações
                        if hasattr(novo_paciente, 'observacoes'):
                            novo_paciente.observacoes = f"Importado do SHOSP em {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} via recuperação de senha"
                        
                        db.session.add(novo_paciente)
                        db.session.commit()
                        
                        current_app.logger.info(f"Usuário criado com sucesso a partir do SHOSP: {novo_usuario.id}")
                        
                        # Enviar senha provisória usando o serviço unificado de email
                        try:
                            current_app.logger.info(f"Tentando enviar senha provisória para novo usuário: {novo_usuario.email}")
                            enviar_senha_provisoria(novo_usuario, senha_provisoria)
                            current_app.logger.info("Email de senha provisória enviado com sucesso para novo usuário")
                            flash('Conta criada com dados do sistema da clínica! Uma senha provisória foi enviada para seu e-mail.', 'success')
                        except Exception as e:
                            current_app.logger.error(f"Erro ao enviar senha provisória para novo usuário: {str(e)}")
                            # Mostrar a senha na tela como fallback
                            flash(f'Conta criada com sucesso! Erro no envio do e-mail. Sua senha provisória é: {senha_provisoria}. Anote esta senha pois ela expira em 24 horas.', 'warning')
                        
                        return redirect(url_for('auth.login'))
                    
                    else:
                        # CPF não encontrado nem localmente nem no SHOSP
                        current_app.logger.info(f"CPF não encontrado no SHOSP: {cpf}")
                        flash('CPF não encontrado no sistema da clínica. Entre em contato para cadastro.', 'danger')
                        return render_template('auth/recuperar_senha.html')
                
                except ImportError:
                    # SHOSP não disponível
                    current_app.logger.warning("Serviço SHOSP não disponível")
                    flash('CPF não encontrado. Se você ainda não é paciente, faça seu cadastro.', 'danger')
                    return render_template('auth/recuperar_senha.html')
                
                except Exception as e:
                    # Erro na consulta SHOSP
                    current_app.logger.error(f"Erro ao consultar SHOSP: {str(e)}")
                    flash('CPF não encontrado. Se você ainda não é paciente, faça seu cadastro.', 'danger')
                    return render_template('auth/recuperar_senha.html')
            
        except Exception as e:
            current_app.logger.error(f"Erro ao solicitar senha provisória: {str(e)}")
            flash('Erro interno. Tente novamente.', 'danger')
            return render_template('auth/recuperar_senha.html')
    
    return render_template('auth/recuperar_senha.html')


@auth_bp.route('/trocar_senha_provisoria', methods=['GET', 'POST'])
@login_required
def trocar_senha_provisoria():
    try:
        usuario = Usuario.query.get(session['user_id'])
        
        if not usuario:
            flash('Usuário não encontrado', 'danger')
            session.clear()
            return redirect(url_for('auth.login'))
        
        if request.method == 'POST':
            senha_atual = request.form.get('senha_atual')
            nova_senha = request.form.get('nova_senha')
            confirmar_senha = request.form.get('confirmar_senha')
            
            if not senha_atual or not nova_senha or not confirmar_senha:
                flash('Todos os campos são obrigatórios', 'danger')
                return render_template('auth/trocar_senha_provisoria.html')
            
            # Verificar senha atual
            if not check_password_hash(usuario.senha, senha_atual):
                flash('Senha atual incorreta', 'danger')
                return render_template('auth/trocar_senha_provisoria.html')
            
            # Verificar se as senhas coincidem
            if nova_senha != confirmar_senha:
                flash('As senhas não coincidem', 'danger')
                return render_template('auth/trocar_senha_provisoria.html')
            
            # Verificar requisitos de segurança da senha
            if len(nova_senha) < 8:
                flash('A senha deve ter pelo menos 8 caracteres', 'danger')
                return render_template('auth/trocar_senha_provisoria.html')
            
            # Atualizar senha
            usuario.senha = generate_password_hash(nova_senha)
            usuario.senha_provisoria = False
            usuario.data_expiracao_senha = None
            
            db.session.commit()
            
            # Atualizar sessão
            session['primeiro_acesso'] = False
            
            flash('Senha alterada com sucesso!', 'success')
            
            # Verificar se tem múltiplos perfis
            try:
                perfis_usuario = list(usuario.perfis) if hasattr(usuario, 'perfis') else []
                
                if len(perfis_usuario) > 1:
                    # Se tem múltiplos perfis, ir para seleção
                    session['perfis_disponiveis'] = [
                        {'id': p.id, 'nome': p.nome, 'descricao': p.descricao} 
                        for p in perfis_usuario
                    ]
                    return redirect(url_for('auth.selecionar_perfil'))
                elif len(perfis_usuario) == 1:
                    # Se tem apenas um perfil, usar ele diretamente
                    perfil_usado = perfis_usuario[0].nome
                    session['user_tipo'] = perfil_usado
                    session['perfil_atual'] = perfil_usado
                else:
                    # Se não tem perfil associado, usar paciente como padrão
                    perfil_usado = 'paciente'
                    session['user_tipo'] = perfil_usado
                    session['perfil_atual'] = perfil_usado
            except Exception as e:
                current_app.logger.error(f"Erro ao obter perfis: {str(e)}")
                # Usar paciente como padrão
                perfil_usado = 'paciente'
                session['user_tipo'] = perfil_usado
                session['perfil_atual'] = perfil_usado
            
            # Redirecionar com base no perfil
            perfil_usado = session.get('user_tipo', 'paciente')
            
            try:
                if perfil_usado == 'admin':
                    return redirect('/admin/')
                elif perfil_usado == 'medico':
                    return redirect('/medico/')
                elif perfil_usado == 'assistente':
                    return redirect('/assistente/')
                elif perfil_usado == 'paciente':
                    return redirect('/paciente/')
                else:
                    return redirect(url_for('auth.login'))
            except Exception as e:
                current_app.logger.error(f"Erro ao redirecionar após troca de senha: {str(e)}")
                flash('Senha alterada, mas erro ao redirecionar. Faça login novamente.', 'warning')
                session.clear()
                return redirect(url_for('auth.login'))
        
        return render_template('auth/trocar_senha_provisoria.html')
        
    except Exception as e:
        current_app.logger.error(f"Erro na troca de senha provisória: {str(e)}")
        flash('Erro interno. Tente novamente.', 'danger')
        return redirect(url_for('auth.login'))


@auth_bp.route('/trocar_perfil')
@login_required
def trocar_perfil():
    """Permite ao usuário trocar entre seus perfis"""
    try:
        usuario = Usuario.query.get(session['user_id'])
        
        if not usuario:
            flash('Usuário não encontrado', 'danger')
            session.clear()
            return redirect(url_for('auth.login'))
        
        try:
            # Buscar perfis do usuário
            perfis_usuario = list(usuario.perfis) if hasattr(usuario, 'perfis') else []
            
            if len(perfis_usuario) <= 1:
                flash('Você não possui múltiplos perfis para trocar', 'info')
                
                # Redirecionar com base no perfil atual
                perfil_atual = session.get('user_tipo', 'paciente')
                
                if perfil_atual == 'admin':
                    return redirect('/admin/')
                elif perfil_atual == 'medico':
                    return redirect('/medico/')
                elif perfil_atual == 'assistente':
                    return redirect('/assistente/')
                elif perfil_atual == 'paciente':
                    return redirect('/paciente/')
                else:
                    return redirect(url_for('auth.login'))
            
            # Armazenar perfis na sessão
            session['perfis_disponiveis'] = [
                {'id': p.id, 'nome': p.nome, 'descricao': p.descricao} 
                for p in perfis_usuario
            ]
            
            # Remover perfil atual da sessão
            if 'user_tipo' in session:
                session.pop('user_tipo')
            if 'perfil_atual' in session:
                session.pop('perfil_atual')
            
            return redirect(url_for('auth.selecionar_perfil'))
            
        except Exception as e:
            current_app.logger.error(f"Erro ao trocar perfil: {str(e)}")
            flash('Erro ao trocar perfil. Tente novamente.', 'danger')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        current_app.logger.error(f"Erro geral ao trocar perfil: {str(e)}")
        flash('Erro interno. Tente novamente.', 'danger')
        return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso', 'success')
    return redirect(url_for('auth.login'))


# Funções auxiliares

def gerar_senha_provisoria(tamanho=8):
    """Gera uma senha provisória aleatória"""
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for i in range(tamanho))


# NOTA: A função enviar_senha_provisoria agora é importada do serviço unificado
# from src.services.unified_email_service import enviar_senha_provisoria
