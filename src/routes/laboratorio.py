from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.utils import secure_filename
from src.extensions import db
from src.models.usuario import Usuario
from src.models.paciente import Paciente
from src.models.exame_laboratorial import ExameLaboratorial
from src.routes.auth import login_required
import os
from datetime import datetime
import json

# Importar serviço de notificação
try:
    from src.services.notification_service import notificar_resultado_disponivel, NOTIFICATION_SERVICE_AVAILABLE
    NOTIFICACAO_DISPONIVEL = NOTIFICATION_SERVICE_AVAILABLE
except ImportError as e:
    current_app.logger.warning(f"⚠️ Serviço de notificação não disponível: {str(e)}")
    NOTIFICACAO_DISPONIVEL = False
    notificar_resultado_disponivel = None

laboratorio_bp = Blueprint('laboratorio', __name__)

# Middleware para verificar se o usuário é assistente
@laboratorio_bp.before_request
def check_assistente():
    if 'user_id' not in session or session.get('user_tipo') != 'assistente':
        flash('Acesso restrito a assistentes', 'danger')
        return redirect(url_for('auth.login'))

@laboratorio_bp.route('/exames_laboratoriais')
@login_required
def exames_laboratoriais():
    # Obter o assistente logado
    user_id = session.get('user_id')
    assistente = Usuario.query.filter_by(id=user_id, tipo='assistente').first()
    
    if not assistente:
        flash('Perfil de assistente não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Filtro de status
    status = request.args.get('status', 'todos')
    
    # Consulta base
    query = ExameLaboratorial.query
    
    # Aplicar filtro de status
    if status == 'pendente':
        query = query.filter_by(status='pendente')
    elif status == 'coletado':
        query = query.filter_by(status='coletado')
    elif status == 'resultado_disponivel':
        query = query.filter_by(status='resultado_disponivel')
    
    # Ordenar por data de solicitação (mais recentes primeiro)
    exames = query.order_by(ExameLaboratorial.data_solicitacao.desc()).all()
    
    return render_template('assistente/exames_laboratoriais.html', 
                          assistente=assistente,
                          exames=exames,
                          status_filtro=status)

@laboratorio_bp.route('/cadastrar_exame_laboratorial', methods=['GET', 'POST'])
@login_required
def cadastrar_exame_laboratorial():
    # Obter o assistente logado
    user_id = session.get('user_id')
    assistente = Usuario.query.filter_by(id=user_id, tipo='assistente').first()
    
    if not assistente:
        flash('Perfil de assistente não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    if request.method == 'POST':
        paciente_id = request.form.get('paciente_id')
        tipo_exame = request.form.get('tipo_exame')
        data_solicitacao = request.form.get('data_solicitacao')
        medico_solicitante = request.form.get('medico_solicitante')
        observacoes = request.form.get('observacoes')
        
        if not paciente_id or not tipo_exame or not data_solicitacao:
            flash('Paciente, tipo de exame e data de solicitação são obrigatórios', 'danger')
            pacientes = Paciente.query.join(Usuario).order_by(Usuario.nome_completo).all()
            return render_template('assistente/cadastrar_exame_laboratorial.html', 
                                  assistente=assistente,
                                  pacientes=pacientes)
        
        # Converter data de string para objeto datetime
        data_solicitacao_obj = datetime.strptime(data_solicitacao, '%Y-%m-%d')
        
        # Criar exame laboratorial
        novo_exame = ExameLaboratorial(
            paciente_id=paciente_id,
            tipo_exame=tipo_exame,
            data_solicitacao=data_solicitacao_obj,
            medico_solicitante=medico_solicitante,
            observacoes=observacoes,
            status='pendente',
            assistente_id=assistente.id
        )
        
        db.session.add(novo_exame)
        db.session.commit()
        
        flash('Exame laboratorial cadastrado com sucesso', 'success')
        return redirect(url_for('laboratorio.exame_laboratorial_detalhes', id=novo_exame.id))
    
    # Buscar pacientes para o select
    pacientes = Paciente.query.join(Usuario).order_by(Usuario.nome_completo).all()
    
    return render_template('assistente/cadastrar_exame_laboratorial.html', 
                          assistente=assistente,
                          pacientes=pacientes)

@laboratorio_bp.route('/exame_laboratorial/<int:id>')
@login_required
def exame_laboratorial_detalhes(id):
    # Obter o assistente logado
    user_id = session.get('user_id')
    assistente = Usuario.query.filter_by(id=user_id, tipo='assistente').first()
    
    if not assistente:
        flash('Perfil de assistente não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter exame
    exame = ExameLaboratorial.query.get_or_404(id)
    
    return render_template('assistente/exame_laboratorial_detalhes.html', 
                          assistente=assistente,
                          exame=exame)

@laboratorio_bp.route('/registrar_coleta/<int:exame_id>', methods=['POST'])
@login_required
def registrar_coleta(exame_id):
    # Obter o assistente logado
    user_id = session.get('user_id')
    assistente = Usuario.query.filter_by(id=user_id, tipo='assistente').first()
    
    if not assistente:
        flash('Perfil de assistente não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter exame
    exame = ExameLaboratorial.query.get_or_404(exame_id)
    
    # Verificar se o exame já foi coletado
    if exame.status != 'pendente':
        flash('Este exame já foi coletado ou já possui resultado', 'warning')
        return redirect(url_for('laboratorio.exame_laboratorial_detalhes', id=exame.id))
    
    # Atualizar status e data de coleta
    exame.status = 'coletado'
    exame.data_coleta = datetime.utcnow()
    
    db.session.commit()
    
    flash('Coleta registrada com sucesso', 'success')
    return redirect(url_for('laboratorio.exame_laboratorial_detalhes', id=exame.id))

@laboratorio_bp.route('/anexar_resultado/<int:exame_id>', methods=['GET', 'POST'])
@login_required
def anexar_resultado(exame_id):
    # Obter o assistente logado
    user_id = session.get('user_id')
    assistente = Usuario.query.filter_by(id=user_id, tipo='assistente').first()
    
    if not assistente:
        flash('Perfil de assistente não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter exame
    exame = ExameLaboratorial.query.get_or_404(exame_id)
    
    # Verificar se o exame já possui resultado
    if exame.status == 'resultado_disponivel':
        flash('Este exame já possui resultado anexado', 'warning')
        return redirect(url_for('laboratorio.exame_laboratorial_detalhes', id=exame.id))
    
    if request.method == 'POST':
        observacoes = request.form.get('observacoes')
        
        # Upload do arquivo
        arquivo = None
        if 'arquivo' in request.files:
            file = request.files['arquivo']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'laboratorio', str(exame.paciente_id))
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                file_path = os.path.join(upload_dir, f"{timestamp}_{filename}")
                file.save(file_path)
                arquivo = file_path
        
        if not arquivo:
            flash('Arquivo é obrigatório', 'danger')
            return render_template('assistente/anexar_resultado_laboratorial.html', 
                                  assistente=assistente,
                                  exame=exame)
        
        try:
            # Atualizar exame
            exame.arquivo_resultado = arquivo
            exame.observacoes = observacoes if observacoes else exame.observacoes
            exame.status = 'resultado_disponivel'
            exame.data_resultado = datetime.utcnow()
            
            db.session.commit()
            
            # ==============================================
            # NOVA FUNCIONALIDADE: ENVIAR NOTIFICAÇÕES
            # ==============================================
            
            try:
                if NOTIFICACAO_DISPONIVEL and notificar_resultado_disponivel:
                    current_app.logger.info(f"📧 Enviando notificações para paciente: {exame.paciente.usuario.nome_completo}")
                    
                    # Preparar dados para notificação
                    data_realizacao_str = None
                    if exame.data_solicitacao:
                        data_realizacao_str = exame.data_solicitacao.strftime('%d/%m/%Y')
                    
                    # Enviar notificação
                    resultado_notificacao = notificar_resultado_disponivel(
                        paciente=exame.paciente,
                        tipo_exame=exame.tipo_exame,
                        data_realizacao=data_realizacao_str,
                        medico_solicitante=exame.medico_solicitante
                    )
                    
                    # Processar resultado da notificação
                    if resultado_notificacao.get('resumo'):
                        sucessos = resultado_notificacao['resumo'].get('sucessos', [])
                        if sucessos:
                            flash(f'Resultado anexado e paciente notificado via {", ".join(sucessos)}!', 'success')
                            current_app.logger.info(f"✅ Notificações enviadas via: {', '.join(sucessos)}")
                        else:
                            flash('Resultado anexado com sucesso! Porém não foi possível enviar notificações.', 'warning')
                            current_app.logger.warning("⚠️ Nenhuma notificação foi enviada")
                            
                            # Log detalhado dos erros
                            if not resultado_notificacao['email']['sucesso']:
                                current_app.logger.warning(f"Email não enviado: {resultado_notificacao['email']['erro']}")
                            if not resultado_notificacao['whatsapp']['sucesso']:
                                current_app.logger.warning(f"WhatsApp não enviado: {resultado_notificacao['whatsapp']['erro']}")
                    else:
                        flash('Resultado anexado com sucesso! Porém houve erro nas notificações.', 'warning')
                        current_app.logger.error(f"❌ Erro no resultado da notificação: {resultado_notificacao}")
                        
                else:
                    flash('Resultado anexado com sucesso!', 'success')
                    current_app.logger.warning("⚠️ Serviço de notificação não disponível")
                    
            except Exception as e:
                # Se a notificação falhar, não deve afetar o anexo do resultado
                current_app.logger.error(f"❌ Erro ao enviar notificações: {str(e)}")
                flash('Resultado anexado com sucesso! Porém houve erro ao enviar notificações.', 'warning')
            
            return redirect(url_for('laboratorio.exame_laboratorial_detalhes', id=exame.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao anexar resultado: {str(e)}")
            flash(f'Erro ao anexar resultado: {str(e)}', 'danger')
            return render_template('assistente/anexar_resultado_laboratorial.html', 
                                  assistente=assistente,
                                  exame=exame)
    
    return render_template('assistente/anexar_resultado_laboratorial.html', 
                          assistente=assistente,
                          exame=exame)

@laboratorio_bp.route('/remover_resultado/<int:exame_id>', methods=['POST'])
@login_required
def remover_resultado(exame_id):
    # Obter o assistente logado
    user_id = session.get('user_id')
    assistente = Usuario.query.filter_by(id=user_id, tipo='assistente').first()
    
    if not assistente:
        flash('Perfil de assistente não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Obter exame
    exame = ExameLaboratorial.query.get_or_404(exame_id)
    
    # Verificar se o exame possui resultado
    if exame.status != 'resultado_disponivel' or not exame.arquivo_resultado:
        flash('Este exame não possui resultado para remover', 'danger')
        return redirect(url_for('laboratorio.exame_laboratorial_detalhes', id=exame.id))
    
    # Remover arquivo físico
    if os.path.exists(exame.arquivo_resultado):
        os.remove(exame.arquivo_resultado)
    
    # Atualizar exame
    exame.arquivo_resultado = None
    exame.status = 'coletado' if exame.data_coleta else 'pendente'
    exame.data_resultado = None
    
    db.session.commit()
    
    flash('Resultado removido com sucesso', 'success')
    return redirect(url_for('laboratorio.exame_laboratorial_detalhes', id=exame.id))

@laboratorio_bp.route('/buscar_paciente_laboratorio', methods=['GET', 'POST'])
@login_required
def buscar_paciente_laboratorio():
    # Obter o assistente logado
    user_id = session.get('user_id')
    assistente = Usuario.query.filter_by(id=user_id, tipo='assistente').first()
    
    if not assistente:
        flash('Perfil de assistente não encontrado', 'danger')
        return redirect(url_for('auth.logout'))
    
    if request.method == 'POST':
        cpf = request.form.get('cpf')
        
        if not cpf:
            flash('CPF é obrigatório', 'danger')
            return render_template('assistente/buscar_paciente_laboratorio.html', assistente=assistente)
        
        # Buscar paciente pelo CPF
        paciente = Paciente.query.join(Usuario).filter(Usuario.cpf == cpf).first()
        
        if not paciente:
            flash('Paciente não encontrado', 'warning')
            return render_template('assistente/buscar_paciente_laboratorio.html', assistente=assistente)
        
        # Buscar exames do paciente
        exames = ExameLaboratorial.query.filter_by(
            paciente_id=paciente.id
        ).order_by(ExameLaboratorial.data_solicitacao.desc()).all()
        
        return render_template('assistente/paciente_exames_laboratoriais.html', 
                              assistente=assistente,
                              paciente=paciente,
                              exames=exames)
    
    return render_template('assistente/buscar_paciente_laboratorio.html', assistente=assistente)

# ==============================================
# NOVA ROTA: DEBUG DE NOTIFICAÇÕES
# ==============================================

@laboratorio_bp.route('/debug/notificacoes')
@login_required
def debug_notificacoes():
    """Rota de debug para testar serviços de notificação (apenas em modo debug)"""
    if not current_app.debug:
        flash('Função disponível apenas em modo debug', 'danger')
        return redirect(url_for('laboratorio.exames_laboratoriais'))
    
    try:
        if NOTIFICACAO_DISPONIVEL:
            from src.services.notification_service import notification_service
            status = notification_service.get_status()
            teste = notification_service.testar_servicos()
            
            return jsonify({
                'notificacao_disponivel': NOTIFICACAO_DISPONIVEL,
                'status': status,
                'teste': teste,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'notificacao_disponivel': False,
                'erro': 'Serviço de notificação não foi inicializado',
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        return jsonify({
            'erro': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
