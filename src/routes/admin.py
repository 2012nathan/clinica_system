from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from src.extensions import db
from src.models.usuario import Usuario
from src.models.perfil import Perfil
from src.models.profissional import Profissional
from src.models.especialidade import Especialidade
from src.models.disponibilidade import DisponibilidadeProfissional
from src.models.agendamento import Agendamento
from src.models.documento import Documento
from sqlalchemy import func, desc, and_
import os
from datetime import datetime, time, timedelta

admin_bp = Blueprint('admin', __name__)

# Middleware para verificar se o usuário é admin
@admin_bp.before_request
def check_admin():
    # Verificar se está logado
    if 'user_id' not in session:
        flash('Acesso restrito. Faça login primeiro.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Verificar se tem perfil de admin (compatível com múltiplos perfis)
    if session.get('user_tipo') != 'admin' and session.get('perfil_atual') != 'admin':
        flash('Acesso restrito a administradores', 'danger')
        return redirect(url_for('auth.login'))


@admin_bp.route("/", methods=["GET"])
def index():
    return redirect(url_for("admin.dashboard"))

@admin_bp.route('/dashboard')
def dashboard():
    # Obter o administrador logado
    user_id = session.get('user_id')
    admin = Usuario.query.filter_by(id=user_id).first()
    
    if not admin:
        flash('Perfil de administrador não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter perfis
    perfil_medico = Perfil.query.filter_by(nome='medico').first()
    perfil_assistente = Perfil.query.filter_by(nome='assistente').first()
    perfil_paciente = Perfil.query.filter_by(nome='paciente').first()
    
    # Contagem de usuários por perfil
    total_medicos = 0
    total_assistentes = 0
    total_pacientes = 0
    
    try:
        if perfil_medico:
            total_medicos = len(perfil_medico.usuarios)
        if perfil_assistente:
            total_assistentes = len(perfil_assistente.usuarios)
        if perfil_paciente:
            total_pacientes = len(perfil_paciente.usuarios)
        
        # Contagem de especialidades
        total_especialidades = Especialidade.query.count()
        
        # Agendamentos recentes (se existir a tabela)
        agendamentos_recentes = []
        try:
            agendamentos_recentes = Agendamento.query.order_by(
                Agendamento.data_hora_inicio.desc()
            ).limit(5).all()
        except:
            pass
        
        # Documentos recentes (se existir a tabela)
        documentos_recentes = []
        try:
            documentos_recentes = Documento.query.order_by(
                Documento.data_criacao.desc()
            ).limit(5).all()
        except:
            pass
            
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar estatísticas do dashboard: {str(e)}")
        total_medicos = 0
        total_assistentes = 0
        total_pacientes = 0
        total_especialidades = 0
        agendamentos_recentes = []
        documentos_recentes = []
    
    return render_template('admin/dashboard.html',
                          admin=admin,
                          total_medicos=total_medicos,
                          total_assistentes=total_assistentes,
                          total_pacientes=total_pacientes,
                          total_especialidades=total_especialidades,
                          agendamentos_recentes=agendamentos_recentes,
                          documentos_recentes=documentos_recentes)

# Gerenciamento de Especialidades
@admin_bp.route('/especialidades')
def especialidades():
    especialidades = Especialidade.query.all()
    return render_template('admin/especialidades.html', especialidades=especialidades)

@admin_bp.route('/especialidades/nova', methods=['GET', 'POST'])
def nova_especialidade():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        
        if not nome:
            flash('Nome da especialidade é obrigatório', 'danger')
            return render_template('admin/form_especialidade.html')
        
        # Verificar se já existe
        especialidade_existente = Especialidade.query.filter_by(nome=nome).first()
        if especialidade_existente:
            flash('Especialidade já cadastrada', 'danger')
            return render_template('admin/form_especialidade.html')
        
        # Criar nova especialidade
        nova_especialidade = Especialidade(
            nome=nome,
            descricao=descricao
        )
        
        db.session.add(nova_especialidade)
        db.session.commit()
        
        flash('Especialidade cadastrada com sucesso', 'success')
        return redirect(url_for('admin.especialidades'))
    
    return render_template('admin/form_especialidade.html')

@admin_bp.route('/especialidades/editar/<int:id>', methods=['GET', 'POST'])
def editar_especialidade(id):
    especialidade = Especialidade.query.get_or_404(id)
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        
        if not nome:
            flash('Nome da especialidade é obrigatório', 'danger')
            return render_template('admin/form_especialidade.html', especialidade=especialidade)
        
        # Verificar se já existe outro com mesmo nome
        especialidade_existente = Especialidade.query.filter_by(nome=nome).first()
        if especialidade_existente and especialidade_existente.id != id:
            flash('Já existe outra especialidade com este nome', 'danger')
            return render_template('admin/form_especialidade.html', especialidade=especialidade)
        
        # Atualizar especialidade
        especialidade.nome = nome
        especialidade.descricao = descricao
        
        db.session.commit()
        
        flash('Especialidade atualizada com sucesso', 'success')
        return redirect(url_for('admin.especialidades'))
    
    return render_template('admin/form_especialidade.html', especialidade=especialidade)

@admin_bp.route('/especialidades/excluir/<int:id>', methods=['POST'])
def excluir_especialidade(id):
    especialidade = Especialidade.query.get_or_404(id)
    
    # Verificar se há profissionais vinculados
    if especialidade.profissionais:
        flash('Não é possível excluir especialidade com profissionais vinculados', 'danger')
        return redirect(url_for('admin.especialidades'))
    
    db.session.delete(especialidade)
    db.session.commit()
    
    flash('Especialidade excluída com sucesso', 'success')
    return redirect(url_for('admin.especialidades'))

# Gerenciamento de Profissionais
@admin_bp.route('/profissionais')
def profissionais():
    try:
        profissionais = Profissional.query.join(Usuario).join(Especialidade).all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar profissionais: {str(e)}")
        profissionais = []
    return render_template('admin/profissionais.html', profissionais=profissionais)

@admin_bp.route('/profissionais/novo', methods=['GET', 'POST'])
def novo_profissional():
    especialidades = Especialidade.query.all()
    
    if request.method == 'POST':
        # Dados do usuário
        nome_completo = request.form.get('nome_completo')
        cpf = request.form.get('cpf')
        data_nascimento = request.form.get('data_nascimento')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        senha = request.form.get('senha')
        
        # Dados do profissional
        especialidade_id = request.form.get('especialidade_id')
        registro_profissional = request.form.get('registro_profissional')
        biografia = request.form.get('biografia')
        
        # Validação básica
        if not nome_completo or not cpf or not data_nascimento or not email or not senha or not especialidade_id or not registro_profissional:
            flash('Todos os campos obrigatórios devem ser preenchidos', 'danger')
            return render_template('admin/form_profissional.html', especialidades=especialidades)
        
        # Limpar CPF
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # CORREÇÃO PRINCIPAL: Verificar se o CPF já está cadastrado
        usuario_existente = Usuario.query.filter_by(cpf=cpf).first()
        
        # Buscar ou criar perfil médico
        perfil_medico = Perfil.query.filter_by(nome='medico').first()
        if not perfil_medico:
            perfil_medico = Perfil(nome='medico', descricao='Médico/Profissional de Saúde')
            db.session.add(perfil_medico)
            db.session.flush()
        
        if usuario_existente:
            # USUÁRIO JÁ EXISTE - Verificar se já tem perfil de médico
            if usuario_existente.has_perfil('medico'):
                flash('Este usuário já possui perfil de médico', 'warning')
                return render_template('admin/form_profissional.html', especialidades=especialidades)
            
            # Verificar se o email já está sendo usado por outro usuário
            email_existente = Usuario.query.filter_by(email=email).first()
            if email_existente and email_existente.id != usuario_existente.id:
                flash('Email já cadastrado por outro usuário', 'danger')
                return render_template('admin/form_profissional.html', especialidades=especialidades)
            
            # Adicionar perfil de médico ao usuário existente
            usuario_existente.perfis.append(perfil_medico)
            
            # Atualizar dados se necessário
            usuario_existente.email = email
            usuario_existente.telefone = telefone
            
            current_app.logger.info(f"Adicionando perfil médico ao usuário existente: {usuario_existente.nome_completo}")
            
            db.session.flush()
            usuario_para_profissional = usuario_existente
            
        else:
            # NOVO USUÁRIO - Criar usuário completo
            
            # Verificar se o email já está cadastrado
            email_existente = Usuario.query.filter_by(email=email).first()
            if email_existente:
                flash('Email já cadastrado por outro usuário', 'danger')
                return render_template('admin/form_profissional.html', especialidades=especialidades)
            
            # Criar usuário
            data_nascimento_obj = datetime.strptime(data_nascimento, '%Y-%m-%d')
            novo_usuario = Usuario(
                nome_completo=nome_completo,
                cpf=cpf,
                data_nascimento=data_nascimento_obj,
                email=email,
                telefone=telefone,
                senha=generate_password_hash(senha),
                ativo=True
            )
            
            # Adicionar perfil ao usuário
            novo_usuario.perfis.append(perfil_medico)
            
            db.session.add(novo_usuario)
            db.session.flush()  # Para obter o ID do usuário
            
            current_app.logger.info(f"Criando novo usuário médico: {novo_usuario.nome_completo}")
            usuario_para_profissional = novo_usuario
        
        # Upload de foto de perfil
        foto_perfil = None
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'perfil')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                file_path = os.path.join(upload_dir, f"{cpf}_{filename}")
                file.save(file_path)
                foto_perfil = file_path
        
        # Upload de assinatura digital
        assinatura_digital = None
        if 'assinatura_digital' in request.files:
            file = request.files['assinatura_digital']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'assinaturas')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                file_path = os.path.join(upload_dir, f"{cpf}_{filename}")
                file.save(file_path)
                assinatura_digital = file_path
        
        try:
            # Verificar se já existe um registro de profissional para este usuário
            profissional_existente = Profissional.query.filter_by(usuario_id=usuario_para_profissional.id).first()
            
            if profissional_existente:
                # Atualizar profissional existente
                profissional_existente.especialidade_id = especialidade_id
                profissional_existente.registro_profissional = registro_profissional
                profissional_existente.biografia = biografia
                if foto_perfil:
                    profissional_existente.foto_perfil = foto_perfil
                if assinatura_digital:
                    profissional_existente.assinatura_digital = assinatura_digital
                
                current_app.logger.info(f"Atualizando profissional existente: {usuario_para_profissional.nome_completo}")
            else:
                # Criar novo profissional
                novo_profissional = Profissional(
                    usuario_id=usuario_para_profissional.id,
                    especialidade_id=especialidade_id,
                    registro_profissional=registro_profissional,
                    biografia=biografia,
                    foto_perfil=foto_perfil,
                    assinatura_digital=assinatura_digital
                )
                
                db.session.add(novo_profissional)
                current_app.logger.info(f"Criando novo profissional: {usuario_para_profissional.nome_completo}")
            
            db.session.commit()
            
            if usuario_existente:
                flash('Perfil de médico adicionado com sucesso ao usuário existente', 'success')
            else:
                flash('Profissional cadastrado com sucesso', 'success')
            return redirect(url_for('admin.profissionais'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao cadastrar profissional: {str(e)}")
            flash(f'Erro ao cadastrar profissional: {str(e)}', 'danger')
            return render_template('admin/form_profissional.html', especialidades=especialidades)
    
    return render_template('admin/form_profissional.html', especialidades=especialidades)

@admin_bp.route('/profissionais/editar/<int:id>', methods=['GET', 'POST'])
def editar_profissional(id):
    profissional = Profissional.query.get_or_404(id)
    usuario = Usuario.query.get_or_404(profissional.usuario_id)
    especialidades = Especialidade.query.all()
    
    if request.method == 'POST':
        # Dados do usuário
        nome_completo = request.form.get('nome_completo')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        
        # Dados do profissional
        especialidade_id = request.form.get('especialidade_id')
        registro_profissional = request.form.get('registro_profissional')
        biografia = request.form.get('biografia')
        
        # Validação básica
        if not nome_completo or not email or not especialidade_id or not registro_profissional:
            flash('Todos os campos obrigatórios devem ser preenchidos', 'danger')
            return render_template('admin/form_profissional.html', profissional=profissional, usuario=usuario, especialidades=especialidades)
        
        # Verificar se o email já está cadastrado por outro usuário
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente and usuario_existente.id != usuario.id:
            flash('Email já cadastrado por outro usuário', 'danger')
            return render_template('admin/form_profissional.html', profissional=profissional, usuario=usuario, especialidades=especialidades)
        
        # Upload de foto de perfil
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'perfil')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                file_path = os.path.join(upload_dir, f"{usuario.cpf}_{filename}")
                file.save(file_path)
                profissional.foto_perfil = file_path
        
        # Upload de assinatura digital
        if 'assinatura_digital' in request.files:
            file = request.files['assinatura_digital']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'assinaturas')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                file_path = os.path.join(upload_dir, f"{usuario.cpf}_{filename}")
                file.save(file_path)
                profissional.assinatura_digital = file_path
        
        try:
            # Atualizar usuário
            usuario.nome_completo = nome_completo
            usuario.email = email
            usuario.telefone = telefone
            
            # Atualizar profissional
            profissional.especialidade_id = especialidade_id
            profissional.registro_profissional = registro_profissional
            profissional.biografia = biografia
            
            db.session.commit()
            
            flash('Profissional atualizado com sucesso', 'success')
            return redirect(url_for('admin.profissionais'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar profissional: {str(e)}")
            flash(f'Erro ao atualizar profissional: {str(e)}', 'danger')
            return render_template('admin/form_profissional.html', profissional=profissional, usuario=usuario, especialidades=especialidades)
    
    return render_template('admin/form_profissional.html', profissional=profissional, usuario=usuario, especialidades=especialidades)

@admin_bp.route('/profissionais/<int:id>/toggle_status', methods=['POST'])
def toggle_status_profissional(id):
    try:
        # Buscar o profissional
        profissional = Profissional.query.get(id)
        if not profissional:
            flash('Profissional não encontrado', 'danger')
            return redirect(url_for('admin.profissionais'))
        
        # Buscar o usuário
        usuario = Usuario.query.get(profissional.usuario_id)
        if not usuario:
            flash('Usuário do profissional não encontrado', 'danger')
            return redirect(url_for('admin.profissionais'))
        
        # Inverter o status
        usuario.ativo = not usuario.ativo
        status_texto = "ativado" if usuario.ativo else "desativado"
        
        # Salvar no banco de dados
        db.session.commit()
        
        flash(f'Profissional {status_texto} com sucesso', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao alterar status: {str(e)}")
        flash('Erro ao alterar status do profissional', 'danger')
    
    return redirect(url_for('admin.profissionais'))

@admin_bp.route('/profissionais/excluir/<int:id>', methods=['POST'])
def excluir_profissional(id):
    try:
        # Buscar o profissional
        profissional = Profissional.query.get(id)
        if not profissional:
            flash('Profissional não encontrado', 'danger')
            return redirect(url_for('admin.profissionais'))
        
        # Buscar o usuário
        usuario = Usuario.query.get(profissional.usuario_id)
        if not usuario:
            flash('Usuário do profissional não encontrado', 'danger')
            return redirect(url_for('admin.profissionais'))
        
        nome_profissional = usuario.nome_completo
        
        # Primeiro excluir as disponibilidades do profissional
        try:
            DisponibilidadeProfissional.query.filter_by(profissional_id=id).delete()
        except:
            pass
        
        # Excluir o profissional
        db.session.delete(profissional)
        
        # Remover perfil de médico do usuário
        perfil_medico = Perfil.query.filter_by(nome='medico').first()
        if perfil_medico and perfil_medico in usuario.perfis:
            usuario.perfis.remove(perfil_medico)
        
        # Se o usuário não tem mais perfis, excluir o usuário
        if not usuario.perfis:
            db.session.delete(usuario)
        
        db.session.commit()
        
        flash(f'Profissional {nome_profissional} excluído com sucesso', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao excluir profissional: {str(e)}")
        flash('Erro ao excluir profissional', 'danger')
    
    return redirect(url_for('admin.profissionais'))

# Gerenciamento de Disponibilidade
@admin_bp.route('/profissionais/<int:id>/disponibilidade')
def disponibilidade_profissional(id):
    profissional = Profissional.query.get_or_404(id)
    usuario = Usuario.query.get_or_404(profissional.usuario_id)
    
    try:
        disponibilidades = DisponibilidadeProfissional.query.filter_by(profissional_id=id).all()
    except:
        disponibilidades = []
    
    dias_semana = {
        0: 'Domingo',
        1: 'Segunda-feira',
        2: 'Terça-feira',
        3: 'Quarta-feira',
        4: 'Quinta-feira',
        5: 'Sexta-feira',
        6: 'Sábado'
    }
    
    return render_template('admin/disponibilidade.html', 
                          profissional=profissional, 
                          usuario=usuario, 
                          disponibilidades=disponibilidades,
                          dias_semana=dias_semana)

@admin_bp.route('/profissionais/<int:id>/disponibilidade/nova', methods=['GET', 'POST'])
def nova_disponibilidade(id):
    profissional = Profissional.query.get_or_404(id)
    
    if request.method == 'POST':
        dia_semana = request.form.get('dia_semana')
        hora_inicio = request.form.get('hora_inicio')
        hora_fim = request.form.get('hora_fim')
        intervalo_minutos = request.form.get('intervalo_minutos')
        
        # Validação básica
        if not dia_semana or not hora_inicio or not hora_fim or not intervalo_minutos:
            flash('Todos os campos são obrigatórios', 'danger')
            return redirect(url_for('admin.nova_disponibilidade', id=id))
        
        try:
            # Converter strings para objetos time
            hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
            hora_fim_obj = datetime.strptime(hora_fim, '%H:%M').time()
            
            # Verificar se hora_fim é maior que hora_inicio
            if hora_fim_obj <= hora_inicio_obj:
                flash('A hora de término deve ser maior que a hora de início', 'danger')
                return redirect(url_for('admin.nova_disponibilidade', id=id))
            
            # Verificar se já existe disponibilidade para este dia e horário
            try:
                disponibilidade_existente = DisponibilidadeProfissional.query.filter_by(
                    profissional_id=id,
                    dia_semana=dia_semana
                ).filter(
                    (DisponibilidadeProfissional.hora_inicio <= hora_fim_obj) &
                    (DisponibilidadeProfissional.hora_fim >= hora_inicio_obj)
                ).first()
                
                if disponibilidade_existente:
                    flash('Já existe disponibilidade cadastrada para este dia e horário', 'danger')
                    return redirect(url_for('admin.nova_disponibilidade', id=id))
            except:
                pass
            
            # Criar nova disponibilidade
            nova_disponibilidade = DisponibilidadeProfissional(
                profissional_id=id,
                dia_semana=dia_semana,
                hora_inicio=hora_inicio_obj,
                hora_fim=hora_fim_obj,
                intervalo_minutos=intervalo_minutos,
                ativo=True
            )
            
            db.session.add(nova_disponibilidade)
            db.session.commit()
            
            flash('Disponibilidade cadastrada com sucesso', 'success')
            return redirect(url_for('admin.disponibilidade_profissional', id=id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao cadastrar disponibilidade: {str(e)}")
            flash(f'Erro ao cadastrar disponibilidade: {str(e)}', 'danger')
            return redirect(url_for('admin.nova_disponibilidade', id=id))
    
    dias_semana = {
        0: 'Domingo',
        1: 'Segunda-feira',
        2: 'Terça-feira',
        3: 'Quarta-feira',
        4: 'Quinta-feira',
        5: 'Sexta-feira',
        6: 'Sábado'
    }
    
    return render_template('admin/form_disponibilidade.html', 
                          profissional=profissional,
                          dias_semana=dias_semana)

@admin_bp.route('/disponibilidade/editar/<int:id>', methods=['GET', 'POST'])
def editar_disponibilidade(id):
    disponibilidade = DisponibilidadeProfissional.query.get_or_404(id)
    profissional = Profissional.query.get_or_404(disponibilidade.profissional_id)
    
    if request.method == 'POST':
        dia_semana = request.form.get('dia_semana')
        hora_inicio = request.form.get('hora_inicio')
        hora_fim = request.form.get('hora_fim')
        intervalo_minutos = request.form.get('intervalo_minutos')
        ativo = 'ativo' in request.form
        
        # Validação básica
        if not dia_semana or not hora_inicio or not hora_fim or not intervalo_minutos:
            flash('Todos os campos são obrigatórios', 'danger')
            return redirect(url_for('admin.editar_disponibilidade', id=id))
        
        try:
            # Converter strings para objetos time
            hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
            hora_fim_obj = datetime.strptime(hora_fim, '%H:%M').time()
            
            # Verificar se hora_fim é maior que hora_inicio
            if hora_fim_obj <= hora_inicio_obj:
                flash('A hora de término deve ser maior que a hora de início', 'danger')
                return redirect(url_for('admin.editar_disponibilidade', id=id))
            
            # Verificar se já existe disponibilidade para este dia e horário (excluindo a atual)
            try:
                disponibilidade_existente = DisponibilidadeProfissional.query.filter_by(
                    profissional_id=disponibilidade.profissional_id,
                    dia_semana=dia_semana
                ).filter(
                    (DisponibilidadeProfissional.hora_inicio <= hora_fim_obj) &
                    (DisponibilidadeProfissional.hora_fim >= hora_inicio_obj) &
                    (DisponibilidadeProfissional.id != id)
                ).first()
                
                if disponibilidade_existente:
                    flash('Já existe disponibilidade cadastrada para este dia e horário', 'danger')
                    return redirect(url_for('admin.editar_disponibilidade', id=id))
            except:
                pass
            
            # Atualizar disponibilidade
            disponibilidade.dia_semana = dia_semana
            disponibilidade.hora_inicio = hora_inicio_obj
            disponibilidade.hora_fim = hora_fim_obj
            disponibilidade.intervalo_minutos = intervalo_minutos
            disponibilidade.ativo = ativo
            
            db.session.commit()
            
            flash('Disponibilidade atualizada com sucesso', 'success')
            return redirect(url_for('admin.disponibilidade_profissional', id=disponibilidade.profissional_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar disponibilidade: {str(e)}")
            flash(f'Erro ao atualizar disponibilidade: {str(e)}', 'danger')
            return redirect(url_for('admin.editar_disponibilidade', id=id))
    
    dias_semana = {
        0: 'Domingo',
        1: 'Segunda-feira',
        2: 'Terça-feira',
        3: 'Quarta-feira',
        4: 'Quinta-feira',
        5: 'Sexta-feira',
        6: 'Sábado'
    }
    
    return render_template('admin/form_disponibilidade.html', 
                          profissional=profissional,
                          disponibilidade=disponibilidade,
                          dias_semana=dias_semana)

@admin_bp.route('/disponibilidade/excluir/<int:id>', methods=['POST'])
def excluir_disponibilidade(id):
    disponibilidade = DisponibilidadeProfissional.query.get_or_404(id)
    profissional_id = disponibilidade.profissional_id
    
    # Verificar se há agendamentos para esta disponibilidade
    # Implementar lógica para verificar agendamentos futuros
    
    db.session.delete(disponibilidade)
    db.session.commit()
    
    flash('Disponibilidade excluída com sucesso', 'success')
    return redirect(url_for('admin.disponibilidade_profissional', id=profissional_id))

# Gerenciamento de Assistentes
@admin_bp.route('/assistentes')
def assistentes():
    # Buscar usuários com perfil de assistente
    perfil_assistente = Perfil.query.filter_by(nome='assistente').first()
    assistentes = []
    if perfil_assistente:
        assistentes = list(perfil_assistente.usuarios)
    
    return render_template('admin/assistentes.html', assistentes=assistentes)

@admin_bp.route('/assistentes/novo', methods=['GET', 'POST'])
def novo_assistente():
    if request.method == 'POST':
        nome_completo = request.form.get('nome_completo')
        cpf = request.form.get('cpf')
        data_nascimento = request.form.get('data_nascimento')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        senha = request.form.get('senha')
        
        # Validação básica
        if not nome_completo or not cpf or not data_nascimento or not email or not senha:
            flash('Todos os campos obrigatórios devem ser preenchidos', 'danger')
            return render_template('admin/form_assistente.html')
        
        # Limpar CPF
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # CORREÇÃO PRINCIPAL: Verificar se o CPF já está cadastrado
        usuario_existente = Usuario.query.filter_by(cpf=cpf).first()
        
        # Buscar ou criar perfil assistente
        perfil_assistente = Perfil.query.filter_by(nome='assistente').first()
        if not perfil_assistente:
            perfil_assistente = Perfil(nome='assistente', descricao='Assistente de Radiologia')
            db.session.add(perfil_assistente)
            db.session.flush()
        
        if usuario_existente:
            # USUÁRIO JÁ EXISTE - Verificar se já tem perfil de assistente
            if usuario_existente.has_perfil('assistente'):
                flash('Este usuário já possui perfil de assistente', 'warning')
                return render_template('admin/form_assistente.html')
            
            # Verificar se o email já está sendo usado por outro usuário
            email_existente = Usuario.query.filter_by(email=email).first()
            if email_existente and email_existente.id != usuario_existente.id:
                flash('Email já cadastrado por outro usuário', 'danger')
                return render_template('admin/form_assistente.html')
            
            # Adicionar perfil de assistente ao usuário existente
            usuario_existente.perfis.append(perfil_assistente)
            
            # Atualizar dados se necessário
            usuario_existente.email = email
            usuario_existente.telefone = telefone
            
            current_app.logger.info(f"Adicionando perfil assistente ao usuário existente: {usuario_existente.nome_completo}")
            
        else:
            # NOVO USUÁRIO - Criar usuário completo
            
            # Verificar se o email já está cadastrado
            email_existente = Usuario.query.filter_by(email=email).first()
            if email_existente:
                flash('Email já cadastrado por outro usuário', 'danger')
                return render_template('admin/form_assistente.html')
            
            # Criar usuário
            data_nascimento_obj = datetime.strptime(data_nascimento, '%Y-%m-%d')
            novo_usuario = Usuario(
                nome_completo=nome_completo,
                cpf=cpf,
                data_nascimento=data_nascimento_obj,
                email=email,
                telefone=telefone,
                senha=generate_password_hash(senha),
                ativo=True
            )
            
            # Adicionar perfil ao usuário
            novo_usuario.perfis.append(perfil_assistente)
            
            db.session.add(novo_usuario)
            current_app.logger.info(f"Criando novo usuário assistente: {novo_usuario.nome_completo}")
        
        try:
            db.session.commit()
            
            if usuario_existente:
                flash('Perfil de assistente adicionado com sucesso ao usuário existente', 'success')
            else:
                flash('Assistente cadastrado com sucesso', 'success')
            return redirect(url_for('admin.assistentes'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao cadastrar assistente: {str(e)}")
            flash(f'Erro ao cadastrar assistente: {str(e)}', 'danger')
            return render_template('admin/form_assistente.html')
    
    return render_template('admin/form_assistente.html')

@admin_bp.route('/assistentes/editar/<int:id>', methods=['GET', 'POST'])
def editar_assistente(id):
    assistente = Usuario.query.get_or_404(id)
    
    # Verificar se o usuário tem perfil de assistente
    if not assistente.has_perfil('assistente'):
        flash('Usuário não é um assistente', 'danger')
        return redirect(url_for('admin.assistentes'))
    
    if request.method == 'POST':
        nome_completo = request.form.get('nome_completo')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        
        # Validação básica
        if not nome_completo or not email:
            flash('Todos os campos obrigatórios devem ser preenchidos', 'danger')
            return render_template('admin/form_assistente.html', assistente=assistente)
        
        # Verificar se o email já está cadastrado por outro usuário
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente and usuario_existente.id != id:
            flash('Email já cadastrado por outro usuário', 'danger')
            return render_template('admin/form_assistente.html', assistente=assistente)
        
        try:
            # Atualizar usuário
            assistente.nome_completo = nome_completo
            assistente.email = email
            assistente.telefone = telefone
            
            db.session.commit()
            
            flash('Assistente atualizado com sucesso', 'success')
            return redirect(url_for('admin.assistentes'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar assistente: {str(e)}")
            flash(f'Erro ao atualizar assistente: {str(e)}', 'danger')
            return render_template('admin/form_assistente.html', assistente=assistente)
    
    return render_template('admin/form_assistente.html', assistente=assistente)

@admin_bp.route('/assistentes/<int:id>/toggle_status', methods=['POST'])
def toggle_status_assistente(id):
    try:
        # Buscar o assistente
        assistente = Usuario.query.get(id)
        
        if not assistente or not assistente.has_perfil('assistente'):
            flash('Assistente não encontrado', 'danger')
            return redirect(url_for('admin.assistentes'))
        
        # Inverter o status
        assistente.ativo = not assistente.ativo
        status_texto = "ativado" if assistente.ativo else "inativado"
        
        # Salvar no banco de dados
        db.session.commit()
        
        flash(f'Assistente {status_texto} com sucesso', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao alterar status: {str(e)}")
        flash('Erro ao alterar status do assistente', 'danger')
    
    return redirect(url_for('admin.assistentes'))

@admin_bp.route('/assistentes/excluir/<int:id>', methods=['POST'])
def excluir_assistente(id):
    try:
        # Buscar o assistente
        assistente = Usuario.query.get(id)
        
        if not assistente or not assistente.has_perfil('assistente'):
            flash('Assistente não encontrado', 'danger')
            return redirect(url_for('admin.assistentes'))
        
        nome_assistente = assistente.nome_completo
        
        # Remover perfil de assistente do usuário
        perfil_assistente = Perfil.query.filter_by(nome='assistente').first()
        if perfil_assistente and perfil_assistente in assistente.perfis:
            assistente.perfis.remove(perfil_assistente)
        
        # Se o usuário não tem mais perfis, excluir o usuário
        if not assistente.perfis:
            db.session.delete(assistente)
        
        db.session.commit()
        
        flash(f'Assistente {nome_assistente} excluído com sucesso', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao excluir assistente: {str(e)}")
        flash('Erro ao excluir assistente', 'danger')
    
    return redirect(url_for('admin.assistentes'))

# Rotas de compatibilidade (mantidas para não quebrar links existentes)
@admin_bp.route('/assistentes/desativar/<int:id>', methods=['POST'])
def desativar_assistente(id):
    assistente = Usuario.query.get_or_404(id)
    
    if not assistente.has_perfil('assistente'):
        flash('Usuário não é um assistente', 'danger')
        return redirect(url_for('admin.assistentes'))
    
    assistente.ativo = False
    db.session.commit()
    
    flash('Assistente desativado com sucesso', 'success')
    return redirect(url_for('admin.assistentes'))

@admin_bp.route('/assistentes/ativar/<int:id>', methods=['POST'])
def ativar_assistente(id):
    assistente = Usuario.query.get_or_404(id)
    
    if not assistente.has_perfil('assistente'):
        flash('Usuário não é um assistente', 'danger')
        return redirect(url_for('admin.assistentes'))
    
    assistente.ativo = True
    db.session.commit()
    
    flash('Assistente ativado com sucesso', 'success')
    return redirect(url_for('admin.assistentes'))

@admin_bp.route('/profissionais/desativar/<int:id>', methods=['POST'])
def desativar_profissional(id):
    profissional = Profissional.query.get_or_404(id)
    usuario = Usuario.query.get_or_404(profissional.usuario_id)
    
    usuario.ativo = False
    db.session.commit()
    
    flash('Profissional desativado com sucesso', 'success')
    return redirect(url_for('admin.profissionais'))

@admin_bp.route('/profissionais/ativar/<int:id>', methods=['POST'])
def ativar_profissional(id):
    profissional = Profissional.query.get_or_404(id)
    usuario = Usuario.query.get_or_404(profissional.usuario_id)
    
    usuario.ativo = True
    db.session.commit()
    
    flash('Profissional ativado com sucesso', 'success')
    return redirect(url_for('admin.profissionais'))


# NOVA FUNCIONALIDADE: Gerenciamento de perfis de paciente
@admin_bp.route('/adicionar_perfil_paciente/<int:usuario_id>', methods=['POST'])
def adicionar_perfil_paciente(usuario_id):
    """Adiciona perfil de paciente a um usuário existente"""
    try:
        usuario = Usuario.query.get_or_404(usuario_id)
        
        # Verificar se já tem perfil de paciente
        if usuario.has_perfil('paciente'):
            flash('Este usuário já possui perfil de paciente', 'warning')
            return redirect(request.referrer or url_for('admin.dashboard'))
        
        # Buscar ou criar perfil paciente
        perfil_paciente = Perfil.query.filter_by(nome='paciente').first()
        if not perfil_paciente:
            perfil_paciente = Perfil(nome='paciente', descricao='Paciente da clínica')
            db.session.add(perfil_paciente)
            db.session.flush()
        
        # Adicionar perfil ao usuário
        usuario.perfis.append(perfil_paciente)
        
        # Verificar se já existe registro na tabela pacientes
        from src.models.paciente import Paciente
        paciente_existente = Paciente.query.filter_by(usuario_id=usuario.id).first()
        
        if not paciente_existente:
            # Criar registro de paciente
            novo_paciente = Paciente(
                usuario_id=usuario.id,
                cartao_sus='',
                convenio='',
                numero_convenio=''
            )
            db.session.add(novo_paciente)
        
        db.session.commit()
        
        flash(f'Perfil de paciente adicionado com sucesso para {usuario.nome_completo}', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao adicionar perfil paciente: {str(e)}")
        flash('Erro ao adicionar perfil de paciente', 'danger')
    
    return redirect(request.referrer or url_for('admin.dashboard'))

@admin_bp.route('/notificacoes')
def dashboard_notificacoes():
    """Dashboard para monitorar notificações enviadas"""
    try:
        # Obter o admin logado
        user_id = session.get('user_id')
        admin = Usuario.query.filter_by(id=user_id).first()
        
        if not admin:
            flash('Perfil de administrador não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        # Importar estatísticas de notificação
        try:
            from src.services.notification_logger import get_notification_stats
            
            # Obter estatísticas para diferentes períodos
            stats_7_dias = get_notification_stats(7)
            stats_30_dias = get_notification_stats(30)
            
            # Verificar status dos serviços
            try:
                from src.services.notification_service import notification_service, NOTIFICATION_SERVICE_AVAILABLE
                if NOTIFICATION_SERVICE_AVAILABLE:
                    status_servicos = notification_service.get_status()
                    teste_servicos = notification_service.testar_servicos()
                else:
                    status_servicos = None
                    teste_servicos = None
            except ImportError:
                status_servicos = None
                teste_servicos = None
            
        except ImportError:
            current_app.logger.warning("Serviço de logs de notificação não disponível")
            stats_7_dias = stats_30_dias = None
            status_servicos = teste_servicos = None
        
        return render_template('admin/dashboard_notificacoes.html',
                              admin=admin,
                              stats_7_dias=stats_7_dias,
                              stats_30_dias=stats_30_dias,
                              status_servicos=status_servicos,
                              teste_servicos=teste_servicos)
        
    except Exception as e:
        current_app.logger.error(f"Erro no dashboard de notificações: {str(e)}")
        flash('Erro ao carregar dashboard de notificações', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/notificacoes/configuracoes')
def configuracoes_notificacoes():
    """Página de configurações dos serviços de notificação"""
    try:
        # Obter o admin logado
        user_id = session.get('user_id')
        admin = Usuario.query.filter_by(id=user_id).first()
        
        if not admin:
            flash('Perfil de administrador não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        # Verificar configurações atuais
        configuracoes = {
            'email': {
                'configurado': False,
                'provider': None,
                'detalhes': {}
            },
            'whatsapp': {
                'configurado': False,
                'api_type': None,
                'detalhes': {}
            }
        }
        
        # Verificar Email
        try:
            from src.services.unified_email_service import email_service, EMAIL_SERVICE_AVAILABLE, EMAIL_PROVIDER
            if EMAIL_SERVICE_AVAILABLE:
                configuracoes['email']['configurado'] = True
                configuracoes['email']['provider'] = EMAIL_PROVIDER
                configuracoes['email']['detalhes'] = email_service.get_provider_info() if email_service else {}
        except ImportError:
            pass
        
        # Verificar WhatsApp
        try:
            from src.services.whatsapp_service import whatsapp_service, WHATSAPP_AVAILABLE
            if WHATSAPP_AVAILABLE:
                configuracoes['whatsapp']['configurado'] = True
                configuracoes['whatsapp']['api_type'] = getattr(whatsapp_service, 'api_type', 'unknown')
                configuracoes['whatsapp']['detalhes'] = {
                    'api_url': bool(os.getenv('WHATSAPP_API_URL')),
                    'api_token': bool(os.getenv('WHATSAPP_API_TOKEN')),
                    'api_type': os.getenv('WHATSAPP_API_TYPE', 'z-api')
                }
        except ImportError:
            pass
        
        # Variáveis de ambiente disponíveis (mascaradas)
        variaveis_env = {
            'WHATSAPP_API_URL': bool(os.getenv('WHATSAPP_API_URL')),
            'WHATSAPP_API_TOKEN': bool(os.getenv('WHATSAPP_API_TOKEN')),
            'WHATSAPP_API_TYPE': os.getenv('WHATSAPP_API_TYPE', 'z-api'),
            'GMAIL_SENDER_EMAIL': bool(os.getenv('GMAIL_SENDER_EMAIL')),
            'SENDGRID_API_KEY': bool(os.getenv('SENDGRID_API_KEY')),
            'MAILGUN_API_KEY': bool(os.getenv('MAILGUN_API_KEY')),
            'RESEND_API_KEY': bool(os.getenv('RESEND_API_KEY'))
        }
        
        return render_template('admin/configuracoes_notificacoes.html',
                              admin=admin,
                              configuracoes=configuracoes,
                              variaveis_env=variaveis_env)
        
    except Exception as e:
        current_app.logger.error(f"Erro nas configurações de notificações: {str(e)}")
        flash('Erro ao carregar configurações de notificações', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/notificacoes/teste', methods=['GET', 'POST'])
def teste_notificacoes():
    """Página para testar envio de notificações"""
    try:
        # Obter o admin logado
        user_id = session.get('user_id')
        admin = Usuario.query.filter_by(id=user_id).first()
        
        if not admin:
            flash('Perfil de administrador não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        if request.method == 'POST':
            cpf = request.form.get('cpf')
            tipo_teste = request.form.get('tipo_teste')  # 'resultado' ou 'laudo'
            
            if not cpf:
                flash('CPF é obrigatório', 'danger')
                return redirect(url_for('admin.teste_notificacoes'))
            
            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            
            # Buscar paciente
            from src.models.paciente import Paciente
            paciente = Paciente.query.join(Usuario).filter(Usuario.cpf == cpf_limpo).first()
            
            if not paciente:
                flash('Paciente não encontrado', 'danger')
                return redirect(url_for('admin.teste_notificacoes'))
            
            # Enviar notificação de teste
            try:
                from src.services.notification_service import notification_service, NOTIFICATION_SERVICE_AVAILABLE
                
                if not NOTIFICATION_SERVICE_AVAILABLE:
                    flash('Serviço de notificações não está disponível', 'danger')
                    return redirect(url_for('admin.teste_notificacoes'))
                
                if tipo_teste == 'laudo':
                    resultado = notification_service.notificar_laudo_disponivel(
                        paciente=paciente,
                        tipo_exame="Ultrassom (TESTE ADMIN)",
                        data_realizacao=datetime.now().strftime('%d/%m/%Y'),
                        medico_responsavel="Dr. Admin Teste"
                    )
                else:
                    resultado = notification_service.notificar_resultado_disponivel(
                        paciente=paciente,
                        tipo_exame="Hemograma (TESTE ADMIN)",
                        data_realizacao=datetime.now().strftime('%d/%m/%Y'),
                        medico_solicitante="Dr. Admin Teste"
                    )
                
                # Processar resultado
                if resultado.get('resumo'):
                    sucessos = resultado['resumo'].get('sucessos', [])
                    if sucessos:
                        flash(f'Teste enviado com sucesso via {", ".join(sucessos)} para {paciente.usuario.nome_completo}!', 'success')
                    else:
                        flash(f'Falha no teste para {paciente.usuario.nome_completo}. Verifique logs para detalhes.', 'warning')
                        # Mostrar erros específicos
                        if not resultado['email']['sucesso']:
                            flash(f'Email: {resultado["email"]["erro"]}', 'info')
                        if not resultado['whatsapp']['sucesso']:
                            flash(f'WhatsApp: {resultado["whatsapp"]["erro"]}', 'info')
                else:
                    flash('Erro no teste de notificação', 'danger')
                
            except ImportError:
                flash('Serviço de notificações não está configurado', 'danger')
            except Exception as e:
                current_app.logger.error(f"Erro no teste de notificação: {str(e)}")
                flash(f'Erro no teste: {str(e)}', 'danger')
            
            return redirect(url_for('admin.teste_notificacoes'))
        
        # Buscar alguns pacientes para exemplo
        from src.models.paciente import Paciente
        pacientes_exemplo = Paciente.query.join(Usuario).filter(
            Usuario.email.isnot(None),
            Usuario.telefone.isnot(None)
        ).limit(10).all()
        
        return render_template('admin/teste_notificacoes.html',
                              admin=admin,
                              pacientes_exemplo=pacientes_exemplo)
        
    except Exception as e:
        current_app.logger.error(f"Erro na página de teste de notificações: {str(e)}")
        flash('Erro ao carregar página de teste', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/notificacoes/limpar-logs', methods=['POST'])
def limpar_logs_notificacoes():
    """Limpa logs antigos de notificações"""
    try:
        # Verificar se é admin
        user_id = session.get('user_id')
        admin = Usuario.query.filter_by(id=user_id).first()
        
        if not admin:
            flash('Acesso negado', 'danger')
            return redirect(url_for('auth.login'))
        
        days_to_keep = request.form.get('days_to_keep', 30)
        try:
            days_to_keep = int(days_to_keep)
        except ValueError:
            days_to_keep = 30
        
        # Limpar logs
        try:
            from src.services.notification_logger import notification_logger
            notification_logger.cleanup_old_logs(keep_days=days_to_keep)
            flash(f'Logs de notificações limpos! Mantidos logs dos últimos {days_to_keep} dias.', 'success')
        except ImportError:
            flash('Serviço de logs não disponível', 'warning')
        except Exception as e:
            current_app.logger.error(f"Erro ao limpar logs: {str(e)}")
            flash('Erro ao limpar logs', 'danger')
        
        return redirect(url_for('admin.dashboard_notificacoes'))
        
    except Exception as e:
        current_app.logger.error(f"Erro na limpeza de logs: {str(e)}")
        flash('Erro na operação de limpeza', 'danger')
        return redirect(url_for('admin.dashboard_notificacoes'))

@admin_bp.route('/notificacoes/api/stats/<int:days>')
def api_stats_notificacoes(days):
    """API para obter estatísticas de notificações (JSON)"""
    try:
        # Verificar se é admin
        user_id = session.get('user_id')
        admin = Usuario.query.filter_by(id=user_id).first()
        
        if not admin:
            return jsonify({'erro': 'Acesso negado'}), 403
        
        # Limitar dias (segurança)
        if days > 365:
            days = 365
        elif days < 1:
            days = 7
        
        # Obter estatísticas
        try:
            from src.services.notification_logger import get_notification_stats
            stats = get_notification_stats(days)
            stats['timestamp'] = datetime.now().isoformat()
            return jsonify(stats)
        except ImportError:
            return jsonify({
                'erro': 'Serviço de estatísticas não disponível',
                'timestamp': datetime.now().isoformat()
            }), 503
        
    except Exception as e:
        current_app.logger.error(f"Erro na API de stats: {str(e)}")
        return jsonify({
            'erro': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# NOVAS FUNCIONALIDADES: Relatórios de Assistentes
@admin_bp.route('/relatorio-assistentes')
def relatorio_assistentes():
    """Relatório de atividades dos assistentes"""
    # Filtros
    periodo = request.args.get('periodo', '30')  # 7, 30, 90 dias
    assistente_id = request.args.get('assistente_id', '')
    
    # Calcular período
    data_inicio = datetime.now() - timedelta(days=int(periodo))
    
    # Query base para assistentes
    query_assistentes = Usuario.query.filter(
        Usuario.perfis.any(Perfil.nome == 'assistente')
    )
    
    if assistente_id:
        query_assistentes = query_assistentes.filter(Usuario.id == assistente_id)
    
    assistentes = query_assistentes.all()
    
    # Dados de atividades
    atividades = []
    
    for assistente in assistentes:
        # Importar modelos dinamicamente para evitar erros se não existirem
        try:
            from src.models.exame_laboratorial import ExameLaboratorial
            # Exames laboratoriais cadastrados
            exames_lab = ExameLaboratorial.query.filter(
                and_(
                    ExameLaboratorial.assistente_id == assistente.id,
                    ExameLaboratorial.data_cadastro >= data_inicio
                )
            ).count()
            
            # Resultados laboratoriais anexados
            resultados_lab = ExameLaboratorial.query.filter(
                and_(
                    ExameLaboratorial.assistente_id == assistente.id,
                    ExameLaboratorial.data_resultado >= data_inicio,
                    ExameLaboratorial.status == 'resultado_disponivel'
                )
            ).count()
            
            # Coletas registradas
            coletas = ExameLaboratorial.query.filter(
                and_(
                    ExameLaboratorial.assistente_id == assistente.id,
                    ExameLaboratorial.data_coleta >= data_inicio
                )
            ).count()
        except ImportError:
            exames_lab = 0
            resultados_lab = 0
            coletas = 0
        
        # Exames de imagem cadastrados
        try:
            from src.models.exame_imagem import ExameImagem
            exames_img = ExameImagem.query.filter(
                and_(
                    ExameImagem.assistente_id == assistente.id,
                    ExameImagem.data_criacao >= data_inicio
                )
            ).count()
        except ImportError:
            exames_img = 0
        
        # Laudos anexados
        try:
            laudos = Documento.query.filter(
                and_(
                    Documento.assistente_id == assistente.id,
                    Documento.data_criacao >= data_inicio,
                    Documento.tipo == 'laudo'
                )
            ).count()
        except:
            laudos = 0
        
        # Agendamentos excluídos
        try:
            from src.models.agendamento_exclusao import AgendamentoExclusao
            exclusoes = AgendamentoExclusao.query.filter(
                and_(
                    AgendamentoExclusao.usuario_exclusao_id == assistente.id,
                    AgendamentoExclusao.data_exclusao >= data_inicio
                )
            ).count()
        except ImportError:
            exclusoes = 0
        
        total_atividades = exames_lab + exames_img + laudos + resultados_lab + coletas + exclusoes
        
        if total_atividades > 0:  # Só incluir assistentes com atividade
            atividades.append({
                'assistente': assistente,
                'exames_laboratoriais': exames_lab,
                'exames_imagem': exames_img,
                'laudos_anexados': laudos,
                'resultados_anexados': resultados_lab,
                'coletas_registradas': coletas,
                'agendamentos_excluidos': exclusoes,
                'total_atividades': total_atividades
            })
    
    # Ordenar por total de atividades
    atividades.sort(key=lambda x: x['total_atividades'], reverse=True)
    
    # Lista de assistentes para filtro
    todos_assistentes = Usuario.query.filter(
        Usuario.perfis.any(Perfil.nome == 'assistente')
    ).order_by(Usuario.nome_completo).all()
    
    return render_template('admin/relatorio_assistentes.html',
                          atividades=atividades,
                          periodo=periodo,
                          assistente_id=assistente_id,
                          todos_assistentes=todos_assistentes)

@admin_bp.route('/atividades-detalhadas/<int:assistente_id>')
def atividades_detalhadas(assistente_id):
    """Atividades detalhadas de um assistente específico"""
    assistente = Usuario.query.get_or_404(assistente_id)
    periodo = request.args.get('periodo', '30')
    data_inicio = datetime.now() - timedelta(days=int(periodo))
    
    # Buscar atividades detalhadas
    atividades_detalhadas = []
    
    # Exames laboratoriais cadastrados
    try:
        from src.models.exame_laboratorial import ExameLaboratorial
        exames_lab = ExameLaboratorial.query.filter(
            and_(
                ExameLaboratorial.assistente_id == assistente_id,
                ExameLaboratorial.data_cadastro >= data_inicio
            )
        ).order_by(desc(ExameLaboratorial.data_cadastro)).all()
        
        for exame in exames_lab:
            atividades_detalhadas.append({
                'tipo': 'exame_laboratorial_cadastrado',
                'data': exame.data_cadastro,
                'descricao': f'Cadastrou exame laboratorial: {exame.tipo_exame}',
                'paciente': exame.paciente.usuario.nome_completo,
                'detalhes': f'ID: {exame.id}'
            })
        
        # Resultados anexados
        resultados = ExameLaboratorial.query.filter(
            and_(
                ExameLaboratorial.assistente_id == assistente_id,
                ExameLaboratorial.data_resultado >= data_inicio,
                ExameLaboratorial.status == 'resultado_disponivel'
            )
        ).order_by(desc(ExameLaboratorial.data_resultado)).all()
        
        for resultado in resultados:
            atividades_detalhadas.append({
                'tipo': 'resultado_anexado',
                'data': resultado.data_resultado,
                'descricao': f'Anexou resultado: {resultado.tipo_exame}',
                'paciente': resultado.paciente.usuario.nome_completo,
                'detalhes': f'ID: {resultado.id}'
            })
        
        # Coletas registradas
        coletas = ExameLaboratorial.query.filter(
            and_(
                ExameLaboratorial.assistente_id == assistente_id,
                ExameLaboratorial.data_coleta >= data_inicio
            )
        ).order_by(desc(ExameLaboratorial.data_coleta)).all()
        
        for coleta in coletas:
            atividades_detalhadas.append({
                'tipo': 'coleta_registrada',
                'data': coleta.data_coleta,
                'descricao': f'Registrou coleta: {coleta.tipo_exame}',
                'paciente': coleta.paciente.usuario.nome_completo,
                'detalhes': f'ID: {coleta.id}'
            })
    except ImportError:
        pass
    
    # Exames de imagem
    try:
        from src.models.exame_imagem import ExameImagem
        exames_img = ExameImagem.query.filter(
            and_(
                ExameImagem.assistente_id == assistente_id,
                ExameImagem.data_criacao >= data_inicio
            )
        ).order_by(desc(ExameImagem.data_criacao)).all()
        
        for exame in exames_img:
            atividades_detalhadas.append({
                'tipo': 'exame_imagem_cadastrado',
                'data': exame.data_criacao,
                'descricao': f'Cadastrou exame de imagem: {exame.tipo_exame}',
                'paciente': exame.paciente.usuario.nome_completo,
                'detalhes': f'ID: {exame.id}'
            })
    except ImportError:
        pass
    
    # Laudos anexados
    try:
        laudos = Documento.query.filter(
            and_(
                Documento.assistente_id == assistente_id,
                Documento.data_criacao >= data_inicio,
                Documento.tipo == 'laudo'
            )
        ).order_by(desc(Documento.data_criacao)).all()
        
        for laudo in laudos:
            atividades_detalhadas.append({
                'tipo': 'laudo_anexado',
                'data': laudo.data_criacao,
                'descricao': f'Anexou laudo: {laudo.titulo}',
                'paciente': laudo.paciente.usuario.nome_completo,
                'detalhes': f'ID: {laudo.id}'
            })
    except:
        pass
    
    # Agendamentos excluídos
    try:
        from src.models.agendamento_exclusao import AgendamentoExclusao
        exclusoes = AgendamentoExclusao.query.filter(
            and_(
                AgendamentoExclusao.usuario_exclusao_id == assistente_id,
                AgendamentoExclusao.data_exclusao >= data_inicio
            )
        ).order_by(desc(AgendamentoExclusao.data_exclusao)).all()
        
        for exclusao in exclusoes:
            atividades_detalhadas.append({
                'tipo': 'agendamento_excluido',
                'data': exclusao.data_exclusao,
                'descricao': f'Excluiu agendamento: {exclusao.tipo_agendamento}',
                'paciente': exclusao.paciente_nome,
                'detalhes': f'Motivo: {exclusao.motivo_exclusao}'
            })
    except ImportError:
        pass
    
    # Ordenar por data (mais recente primeiro)
    atividades_detalhadas.sort(key=lambda x: x['data'], reverse=True)
    
    return render_template('admin/atividades_detalhadas.html',
                          assistente=assistente,
                          atividades=atividades_detalhadas,
                          periodo=periodo)

@admin_bp.route('/api/notificacoes-por-assistente')
def api_notificacoes_por_assistente():
    """API para dashboard - notificações enviadas por assistente"""
    try:
        from src.services.notification_logger import get_stats_por_assistente
        
        periodo = request.args.get('periodo', '7')
        data_inicio = datetime.now() - timedelta(days=int(periodo))
        
        stats = get_stats_por_assistente(data_inicio)
        
        return jsonify({
            'periodo': periodo,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except ImportError:
        return jsonify({'erro': 'Sistema de logs não disponível'}), 503
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
