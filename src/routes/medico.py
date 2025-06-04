from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.utils import secure_filename
from src.extensions import db
from src.models.usuario import Usuario
from src.models.profissional import Profissional
from src.models.paciente import Paciente
from src.models.documento import Documento
from src.models.cartao_gestante import CartaoGestante, ConsultaPreNatal, ExamePreNatal, MedicacaoGestante
import os
from datetime import datetime

medico_bp = Blueprint('medico', __name__)

# Middleware para verificar se o usuário é médico
@medico_bp.before_request
def check_medico():
    # Verificar se está logado
    if 'user_id' not in session:
        flash('Acesso restrito. Faça login primeiro.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Verificar se tem perfil de médico (compatível com múltiplos perfis)
    if session.get('user_tipo') != 'medico' and session.get('perfil_atual') != 'medico':
        flash('Acesso restrito a médicos', 'danger')
        return redirect(url_for('auth.login'))

@medico_bp.route('/dashboard')
def dashboard():
    # Obter o profissional logado
    user_id = session.get('user_id')
    profissional = Profissional.query.join(Usuario).filter(Usuario.id == user_id).first()
    
    if not profissional:
        flash('Perfil de profissional não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Contagem de consultas agendadas
    try:
        from src.models.agendamento import Agendamento
        total_agendamentos = Agendamento.query.filter_by(
            profissional_id=profissional.id, 
            status='agendado'
        ).count()
    except Exception as e:
        current_app.logger.error(f"Erro ao contar agendamentos: {str(e)}")
        total_agendamentos = 0
    
    # Contagem de documentos emitidos
    try:
        total_documentos = Documento.query.filter_by(
            profissional_id=profissional.id
        ).count()
    except Exception as e:
        current_app.logger.error(f"Erro ao contar documentos: {str(e)}")
        total_documentos = 0
    
    # Contagem de pacientes atendidos (agendamentos realizados)
    try:
        from src.models.agendamento import Agendamento
        total_pacientes = Agendamento.query.filter_by(
            profissional_id=profissional.id, 
            status='realizado'
        ).count()
    except Exception as e:
        current_app.logger.error(f"Erro ao contar pacientes: {str(e)}")
        total_pacientes = 0
    
    # Próximos agendamentos
    try:
        from src.models.agendamento import Agendamento
        proximos_agendamentos = Agendamento.query.filter_by(
            profissional_id=profissional.id, 
            status='agendado'
        ).order_by(Agendamento.data_hora_inicio).limit(5).all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar próximos agendamentos: {str(e)}")
        proximos_agendamentos = []
    
    return render_template('medico/dashboard.html', 
                          profissional=profissional,
                          total_agendamentos=total_agendamentos,
                          total_documentos=total_documentos,
                          total_pacientes=total_pacientes,
                          proximos_agendamentos=proximos_agendamentos)

@medico_bp.route('/agenda')
def agenda():
    # Obter o profissional logado
    user_id = session.get('user_id')
    profissional = Profissional.query.join(Usuario).filter(Usuario.id == user_id).first()
    
    if not profissional:
        flash('Perfil de profissional não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter agendamentos
    try:
        from src.models.agendamento import Agendamento
        agendamentos = Agendamento.query.filter_by(
            profissional_id=profissional.id
        ).order_by(Agendamento.data_hora_inicio).all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar agendamentos: {str(e)}")
        agendamentos = []
    
    return render_template('medico/agenda.html', 
                          profissional=profissional,
                          agendamentos=agendamentos)

@medico_bp.route('/pacientes')
def pacientes():
    # Obter o profissional logado
    user_id = session.get('user_id')
    profissional = Profissional.query.join(Usuario).filter(Usuario.id == user_id).first()
    
    if not profissional:
        flash('Perfil de profissional não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter pacientes atendidos pelo profissional (agendamentos realizados)
    try:
        from src.models.agendamento import Agendamento
        pacientes_ids = db.session.query(Agendamento.paciente_id).filter_by(
            profissional_id=profissional.id
        ).distinct().all()
        
        pacientes_ids = [p[0] for p in pacientes_ids]
        pacientes = Paciente.query.filter(Paciente.id.in_(pacientes_ids)).all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar pacientes: {str(e)}")
        pacientes = []
    
    return render_template('medico/pacientes.html', 
                          profissional=profissional,
                          pacientes=pacientes)

@medico_bp.route('/paciente/<int:id>')
def paciente_detalhes(id):
    # Obter o profissional logado
    user_id = session.get('user_id')
    profissional = Profissional.query.join(Usuario).filter(Usuario.id == user_id).first()
    
    if not profissional:
        flash('Perfil de profissional não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter paciente
    paciente = Paciente.query.get_or_404(id)
    
    # Obter histórico de agendamentos
    try:
        from src.models.agendamento import Agendamento
        agendamentos = Agendamento.query.filter_by(
            profissional_id=profissional.id,
            paciente_id=paciente.id
        ).order_by(Agendamento.data_hora_inicio.desc()).all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar agendamentos do paciente: {str(e)}")
        agendamentos = []
    
    # Obter documentos
    try:
        documentos = Documento.query.filter_by(
            profissional_id=profissional.id,
            paciente_id=paciente.id
        ).order_by(Documento.data_criacao.desc()).all()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar documentos do paciente: {str(e)}")
        documentos = []
    
    # Verificar se paciente tem cartão gestante
    try:
        cartao_gestante = CartaoGestante.query.filter_by(
            paciente_id=paciente.id
        ).first()
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar cartão gestante: {str(e)}")
        cartao_gestante = None
    
    return render_template('medico/paciente_detalhes.html', 
                          profissional=profissional,
                          paciente=paciente,
                          agendamentos=agendamentos,
                          documentos=documentos,
                          cartao_gestante=cartao_gestante)

@medico_bp.route('/buscar_paciente', methods=['GET', 'POST'])
def buscar_paciente():
    # Obter o profissional logado
    user_id = session.get('user_id')
    profissional = Profissional.query.join(Usuario).filter(Usuario.id == user_id).first()
    
    if not profissional:
        flash('Perfil de profissional não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        
        if not cpf:
            flash('CPF é obrigatório', 'danger')
            return render_template('medico/buscar_paciente.html', profissional=profissional)
        
        # Limpar CPF
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # Buscar paciente pelo CPF
        paciente = Paciente.query.join(Usuario).filter(Usuario.cpf == cpf).first()
        
        if not paciente:
            flash('Paciente não encontrado', 'warning')
            return render_template('medico/buscar_paciente.html', profissional=profissional)
        
        return redirect(url_for('medico.paciente_detalhes', id=paciente.id))
    
    return render_template('medico/buscar_paciente.html', profissional=profissional)

@medico_bp.route('/documento/novo/<int:paciente_id>', methods=['GET', 'POST'])
def novo_documento(paciente_id):
    # Obter o profissional logado
    user_id = session.get('user_id')
    profissional = Profissional.query.join(Usuario).filter(Usuario.id == user_id).first()
    
    if not profissional:
        flash('Perfil de profissional não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter paciente
    paciente = Paciente.query.get_or_404(paciente_id)
    
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        
        if not tipo or not titulo:
            flash('Tipo e título são obrigatórios', 'danger')
            return render_template('medico/form_documento.html', profissional=profissional, paciente=paciente)
        
        # Upload do arquivo
        arquivo = None
        if 'arquivo' in request.files:
            file = request.files['arquivo']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'documentos', tipo, str(paciente_id))
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                file_path = os.path.join(upload_dir, f"{timestamp}_{filename}")
                file.save(file_path)
                arquivo = file_path
        
        if not arquivo:
            flash('Arquivo é obrigatório', 'danger')
            return render_template('medico/form_documento.html', profissional=profissional, paciente=paciente)
        
        # Criar documento
        documento = Documento(
            paciente_id=paciente_id,
            tipo=tipo,
            titulo=titulo,
            descricao=descricao,
            arquivo_caminho=arquivo,
            status='disponivel'
        )
        
        # Adicionar profissional_id apenas se o campo existir
        if hasattr(documento, 'profissional_id'):
            documento.profissional_id = profissional.id
        
        db.session.add(documento)
        db.session.commit()
        
        flash('Documento cadastrado com sucesso', 'success')
        return redirect(url_for('medico.paciente_detalhes', id=paciente_id))
    
    return render_template('medico/form_documento.html', profissional=profissional, paciente=paciente)

@medico_bp.route('/cartao_gestante/<int:paciente_id>', methods=['GET', 'POST'])
def cartao_gestante(paciente_id):
    # Obter o profissional logado
    user_id = session.get('user_id')
    profissional = Profissional.query.join(Usuario).filter(Usuario.id == user_id).first()
    
    if not profissional:
        flash('Perfil de profissional não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter paciente
    paciente = Paciente.query.get_or_404(paciente_id)
    
    # Verificar se o paciente é do sexo feminino (se o campo existir)
    if hasattr(paciente.usuario, 'sexo') and paciente.usuario.sexo != 'F':
        flash('Cartão gestante só pode ser criado para pacientes do sexo feminino', 'warning')
        return redirect(url_for('medico.paciente_detalhes', id=paciente_id))
    
    # Verificar se já existe cartão gestante
    cartao = CartaoGestante.query.filter_by(paciente_id=paciente_id).first()
    
    if request.method == 'POST':
        data_ultima_menstruacao = request.form.get('data_ultima_menstruacao')
        gestacoes_previas = request.form.get('gestacoes_previas')
        partos_previos = request.form.get('partos_previos')
        abortos_previos = request.form.get('abortos_previos')
        altura_cm = request.form.get('altura_cm')
        peso_inicial_kg = request.form.get('peso_inicial_kg')
        grupo_sanguineo = request.form.get('grupo_sanguineo')
        fator_rh = request.form.get('fator_rh')
        
        # Validação básica
        if not data_ultima_menstruacao:
            flash('Data da última menstruação é obrigatória', 'danger')
            return render_template('medico/form_cartao_gestante.html', 
                                  profissional=profissional, 
                                  paciente=paciente,
                                  cartao=cartao)
        
        # Converter data
        data_ultima_menstruacao_obj = datetime.strptime(data_ultima_menstruacao, '%Y-%m-%d').date()
        
        # Calcular data provável do parto (DUM + 280 dias)
        from datetime import timedelta
        data_provavel_parto = data_ultima_menstruacao_obj + timedelta(days=280)
        
        # Calcular IMC se altura e peso foram informados
        imc_inicial = None
        if altura_cm and peso_inicial_kg:
            altura_m = float(altura_cm) / 100
            imc_inicial = float(peso_inicial_kg) / (altura_m * altura_m)
        
        if cartao:
            # Atualizar cartão existente
            cartao.data_ultima_menstruacao = data_ultima_menstruacao_obj
            cartao.data_provavel_parto = data_provavel_parto
            cartao.gestacoes_previas = gestacoes_previas
            cartao.partos_previos = partos_previos
            cartao.abortos_previos = abortos_previos
            cartao.altura_cm = altura_cm
            cartao.peso_inicial_kg = peso_inicial_kg
            cartao.imc_inicial = imc_inicial
            cartao.grupo_sanguineo = grupo_sanguineo
            cartao.fator_rh = fator_rh
            cartao.data_atualizacao = datetime.utcnow()
            
            db.session.commit()
            flash('Cartão gestante atualizado com sucesso', 'success')
        else:
            # Criar novo cartão
            novo_cartao = CartaoGestante(
                paciente_id=paciente_id,
                data_ultima_menstruacao=data_ultima_menstruacao_obj,
                data_provavel_parto=data_provavel_parto,
                gestacoes_previas=gestacoes_previas,
                partos_previos=partos_previos,
                abortos_previos=abortos_previos,
                altura_cm=altura_cm,
                peso_inicial_kg=peso_inicial_kg,
                imc_inicial=imc_inicial,
                grupo_sanguineo=grupo_sanguineo,
                fator_rh=fator_rh
            )
            
            db.session.add(novo_cartao)
            db.session.commit()
            flash('Cartão gestante criado com sucesso', 'success')
            
            # Atualizar variável cartao para uso na view
            cartao = novo_cartao
        
        return redirect(url_for('medico.cartao_gestante', paciente_id=paciente_id))
    
    # Obter consultas pré-natal
    consultas = []
    exames = []
    medicacoes = []
    
    if cartao:
        try:
            consultas = ConsultaPreNatal.query.filter_by(cartao_gestante_id=cartao.id).order_by(ConsultaPreNatal.data_consulta.desc()).all()
            exames = ExamePreNatal.query.filter_by(cartao_gestante_id=cartao.id).order_by(ExamePreNatal.data_solicitacao.desc()).all()
            medicacoes = MedicacaoGestante.query.filter_by(cartao_gestante_id=cartao.id).all()
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar dados do cartão gestante: {str(e)}")
    
    return render_template('medico/cartao_gestante.html', 
                          profissional=profissional, 
                          paciente=paciente,
                          cartao=cartao,
                          consultas=consultas,
                          exames=exames,
                          medicacoes=medicacoes)

@medico_bp.route('/consulta_pre_natal/<int:cartao_id>', methods=['GET', 'POST'])
def nova_consulta_pre_natal(cartao_id):
    # Obter o profissional logado
    user_id = session.get('user_id')
    profissional = Profissional.query.join(Usuario).filter(Usuario.id == user_id).first()
    
    if not profissional:
        flash('Perfil de profissional não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter cartão gestante
    cartao = CartaoGestante.query.get_or_404(cartao_id)
    paciente = Paciente.query.get_or_404(cartao.paciente_id)
    
    if request.method == 'POST':
        data_consulta = request.form.get('data_consulta')
        semanas_gestacao = request.form.get('semanas_gestacao')
        peso_kg = request.form.get('peso_kg')
        pressao_arterial = request.form.get('pressao_arterial')
        altura_uterina_cm = request.form.get('altura_uterina_cm')
        bcf = request.form.get('bcf')
        movimentos_fetais = 'movimentos_fetais' in request.form
        edema = request.form.get('edema')
        observacoes_medicas = request.form.get('observacoes_medicas')
        observacoes_gestante = request.form.get('observacoes_gestante')
        
        # Validação básica
        if not data_consulta:
            flash('Data da consulta é obrigatória', 'danger')
            return render_template('medico/form_consulta_pre_natal.html', 
                                  profissional=profissional, 
                                  paciente=paciente,
                                  cartao=cartao)
        
        # Converter data
        data_consulta_obj = datetime.strptime(data_consulta, '%Y-%m-%d').date()
        
        # Criar consulta
        consulta = ConsultaPreNatal(
            cartao_gestante_id=cartao_id,
            profissional_id=profissional.id,
            data_consulta=data_consulta_obj,
            semanas_gestacao=semanas_gestacao,
            peso_kg=peso_kg,
            pressao_arterial=pressao_arterial,
            altura_uterina_cm=altura_uterina_cm,
            bcf=bcf,
            movimentos_fetais=movimentos_fetais,
            edema=edema,
            observacoes_medicas=observacoes_medicas,
            observacoes_gestante=observacoes_gestante
        )
        
        db.session.add(consulta)
        db.session.commit()
        
        flash('Consulta pré-natal registrada com sucesso', 'success')
        return redirect(url_for('medico.cartao_gestante', paciente_id=paciente.id))
    
    return render_template('medico/form_consulta_pre_natal.html', 
                          profissional=profissional, 
                          paciente=paciente,
                          cartao=cartao)

@medico_bp.route('/exame_pre_natal/<int:cartao_id>', methods=['GET', 'POST'])
def novo_exame_pre_natal(cartao_id):
    # Obter o profissional logado
    user_id = session.get('user_id')
    profissional = Profissional.query.join(Usuario).filter(Usuario.id == user_id).first()
    
    if not profissional:
        flash('Perfil de profissional não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter cartão gestante
    cartao = CartaoGestante.query.get_or_404(cartao_id)
    paciente = Paciente.query.get_or_404(cartao.paciente_id)
    
    if request.method == 'POST':
        tipo_exame = request.form.get('tipo_exame')
        data_solicitacao = request.form.get('data_solicitacao')
        observacoes = request.form.get('observacoes')
        
        # Validação básica
        if not tipo_exame or not data_solicitacao:
            flash('Tipo de exame e data de solicitação são obrigatórios', 'danger')
            return render_template('medico/form_exame_pre_natal.html', 
                                  profissional=profissional, 
                                  paciente=paciente,
                                  cartao=cartao)
        
        # Converter data
        data_solicitacao_obj = datetime.strptime(data_solicitacao, '%Y-%m-%d').date()
        
        # Criar exame
        exame = ExamePreNatal(
            cartao_gestante_id=cartao_id,
            tipo_exame=tipo_exame,
            data_solicitacao=data_solicitacao_obj,
            observacoes=observacoes
        )
        
        db.session.add(exame)
        db.session.commit()
        
        flash('Exame pré-natal registrado com sucesso', 'success')
        return redirect(url_for('medico.cartao_gestante', paciente_id=paciente.id))
    
    return render_template('medico/form_exame_pre_natal.html', 
                          profissional=profissional, 
                          paciente=paciente,
                          cartao=cartao)

@medico_bp.route('/medicacao_gestante/<int:cartao_id>', methods=['GET', 'POST'])
def nova_medicacao_gestante(cartao_id):
    # Obter o profissional logado
    user_id = session.get('user_id')
    profissional = Profissional.query.join(Usuario).filter(Usuario.id == user_id).first()
    
    if not profissional:
        flash('Perfil de profissional não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter cartão gestante
    cartao = CartaoGestante.query.get_or_404(cartao_id)
    paciente = Paciente.query.get_or_404(cartao.paciente_id)
    
    if request.method == 'POST':
        nome_medicacao = request.form.get('nome_medicacao')
        dosagem = request.form.get('dosagem')
        posologia = request.form.get('posologia')
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        motivo = request.form.get('motivo')
        lembrete_ativo = 'lembrete_ativo' in request.form
        horario_lembrete = request.form.get('horario_lembrete')
        
        # Validação básica
        if not nome_medicacao or not dosagem or not posologia or not data_inicio:
            flash('Nome da medicação, dosagem, posologia e data de início são obrigatórios', 'danger')
            return render_template('medico/form_medicacao_gestante.html', 
                                  profissional=profissional, 
                                  paciente=paciente,
                                  cartao=cartao)
        
        # Converter datas
        data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date() if data_fim else None
        
        # Converter horário
        horario_lembrete_obj = datetime.strptime(horario_lembrete, '%H:%M').time() if horario_lembrete else None
        
        # Criar medicação
        medicacao = MedicacaoGestante(
            cartao_gestante_id=cartao_id,
            nome_medicacao=nome_medicacao,
            dosagem=dosagem,
            posologia=posologia,
            data_inicio=data_inicio_obj,
            data_fim=data_fim_obj,
            motivo=motivo,
            lembrete_ativo=lembrete_ativo,
            horario_lembrete=horario_lembrete_obj
        )
        
        db.session.add(medicacao)
        db.session.commit()
        
        flash('Medicação registrada com sucesso', 'success')
        return redirect(url_for('medico.cartao_gestante', paciente_id=paciente.id))
    
    return render_template('medico/form_medicacao_gestante.html', 
                          profissional=profissional, 
                          paciente=paciente,
                          cartao=cartao)
