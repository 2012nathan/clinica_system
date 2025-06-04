from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.utils import secure_filename
from src.extensions import db
from src.models.usuario import Usuario
from src.models.exame_imagem import ExameImagem
from src.models.documento import Documento
from src.models.paciente import Paciente
import os
import requests
from datetime import datetime
import json

# Importar serviço de notificação
try:
    from src.services.notification_service import notificar_laudo_disponivel, NOTIFICATION_SERVICE_AVAILABLE
    NOTIFICACAO_DISPONIVEL = NOTIFICATION_SERVICE_AVAILABLE
except ImportError as e:
    print(f"⚠️ Serviço de notificação não disponível: {str(e)}")
    NOTIFICACAO_DISPONIVEL = False
    notificar_laudo_disponivel = None

assistente_bp = Blueprint('assistente', __name__)

# Middleware para verificar se o usuário é assistente
@assistente_bp.before_request
def check_assistente():
    # Permitir acesso às rotas públicas
    if request.endpoint and (
        request.endpoint.endswith('static') or 
        request.endpoint in ['assistente.dashboard', 'assistente.index']
    ):
        pass
    
    # Verificar se está logado
    if 'user_id' not in session:
        flash('Acesso restrito. Faça login primeiro.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Verificar se tem perfil de assistente (compatível com múltiplos perfis)
    if session.get('user_tipo') != 'assistente' and session.get('perfil_atual') != 'assistente':
        flash('Acesso restrito a assistentes', 'danger')
        return redirect(url_for('auth.login'))

@assistente_bp.route('/')
def index():
    """Rota padrão que redireciona para dashboard"""
    return redirect(url_for('assistente.dashboard'))

@assistente_bp.route('/dashboard')
def dashboard():
    try:
        # Obter o assistente logado
        user_id = session.get('user_id')
        current_app.logger.info(f"Dashboard assistente - User ID: {user_id}")
        
        # Buscar usuário
        assistente = Usuario.query.filter_by(id=user_id).first()
        
        if not assistente:
            current_app.logger.error(f"Assistente não encontrado para ID: {user_id}")
            flash('Perfil de assistente não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        current_app.logger.info(f"Dashboard assistente carregado para: {assistente.nome_completo}")
        
        # Contagem de exames pendentes de laudo
        try:
            total_pendentes = ExameImagem.query.filter_by(status='pendente').count()
        except Exception as e:
            current_app.logger.error(f"Erro ao contar exames pendentes: {str(e)}")
            total_pendentes = 0
        
        # Contagem de exames coletados
        try:
            total_coletados = ExameImagem.query.filter_by(status='coletado').count()
        except Exception as e:
            current_app.logger.error(f"Erro ao contar exames coletados: {str(e)}")
            total_coletados = 0
        
        # Contagem de exames com laudo
        try:
            total_laudados = ExameImagem.query.filter_by(status='laudado').count()
        except Exception as e:
            current_app.logger.error(f"Erro ao contar exames laudados: {str(e)}")
            total_laudados = 0
        
        # Exames recentes pendentes
        try:
            exames_pendentes = ExameImagem.query.filter_by(
                status='pendente'
            ).order_by(ExameImagem.data_realizacao.desc()).limit(5).all()
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar exames pendentes: {str(e)}")
            exames_pendentes = []
        
        return render_template('assistente/dashboard.html', 
                              assistente=assistente,
                              total_pendentes=total_pendentes,
                              total_coletados=total_coletados,
                              total_laudados=total_laudados,
                              exames_pendentes=exames_pendentes)
        
    except Exception as e:
        current_app.logger.error(f"Erro no dashboard do assistente: {str(e)}")
        flash('Erro ao carregar dashboard. Tente novamente.', 'danger')
        return redirect(url_for('auth.login'))

@assistente_bp.route('/exames')
def exames():
    try:
        # Obter o assistente logado
        user_id = session.get('user_id')
        assistente = Usuario.query.filter_by(id=user_id).first()
        
        if not assistente:
            flash('Perfil de assistente não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        # Filtro de status
        status = request.args.get('status', 'todos')
        
        # Consulta base
        query = ExameImagem.query
        
        # Aplicar filtro de status
        if status == 'pendente':
            query = query.filter_by(status='pendente')
        elif status == 'laudado':
            query = query.filter_by(status='laudado')
        
        # Ordenar por data de exame (mais recentes primeiro)
        exames = query.order_by(ExameImagem.data_realizacao.desc()).all()
        
        return render_template('assistente/exames.html', 
                              assistente=assistente,
                              exames=exames,
                              status_filtro=status)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao listar exames: {str(e)}")
        flash('Erro ao carregar exames. Tente novamente.', 'danger')
        return redirect(url_for('assistente.dashboard'))

@assistente_bp.route('/buscar_exames_orthanc')
def buscar_exames_orthanc():
    try:
        # Obter o assistente logado
        user_id = session.get('user_id')
        assistente = Usuario.query.filter_by(id=user_id).first()
        
        if not assistente:
            flash('Perfil de assistente não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        # Buscar estudos no Orthanc
        try:
            estudos = obter_estudos_orthanc()
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar estudos no Orthanc: {str(e)}")
            flash(f'Erro ao buscar estudos no Orthanc: {str(e)}', 'danger')
            estudos = []
        
        # Verificar quais estudos já estão cadastrados
        estudos_cadastrados = []
        for estudo in estudos:
            try:
                # Verificar se o estudo já está cadastrado
                exame = ExameImagem.query.filter_by(
                    orthanc_study_uid=estudo['ID']
                ).first()
                
                estudo['cadastrado'] = exame is not None
                estudo['status'] = exame.status if exame else None
                estudos_cadastrados.append(estudo)
            except Exception as e:
                current_app.logger.error(f"Erro ao verificar estudo {estudo.get('ID', 'unknown')}: {str(e)}")
                continue
        
        return render_template('assistente/buscar_exames_orthanc.html', 
                              assistente=assistente,
                              estudos=estudos_cadastrados)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar exames Orthanc: {str(e)}")
        flash('Erro ao carregar página de busca. Tente novamente.', 'danger')
        return redirect(url_for('assistente.dashboard'))

@assistente_bp.route('/cadastrar_exame_orthanc/<string:orthanc_study_uid>', methods=['GET', 'POST'])
def cadastrar_exame_orthanc(orthanc_study_uid):
    try:
        # Obter o assistente logado
        user_id = session.get('user_id')
        assistente = Usuario.query.filter_by(id=user_id).first()
        
        if not assistente:
            flash('Perfil de assistente não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        # Verificar se o exame já está cadastrado
        exame_existente = ExameImagem.query.filter_by(
            orthanc_study_uid=orthanc_study_uid
        ).first()
        
        if exame_existente:
            flash('Este exame já está cadastrado no sistema', 'warning')
            return redirect(url_for('assistente.exame_detalhes', id=exame_existente.id))
        
        # Buscar detalhes do estudo no Orthanc
        try:
            estudo = obter_detalhes_estudo_orthanc(orthanc_study_uid)
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar detalhes do estudo {orthanc_study_uid}: {str(e)}")
            flash(f'Erro ao buscar detalhes do estudo no Orthanc: {str(e)}', 'danger')
            return redirect(url_for('assistente.buscar_exames_orthanc'))
        
        if request.method == 'POST':
            paciente_id = request.form.get('paciente_id')
            tipo_exame = request.form.get('tipo_exame')
            descricao = request.form.get('descricao')
            
            if not paciente_id or not tipo_exame:
                flash('Paciente e tipo de exame são obrigatórios', 'danger')
                pacientes = Paciente.query.join(Usuario).order_by(Usuario.nome_completo).all()
                return render_template('assistente/cadastrar_exame_orthanc.html', 
                                      assistente=assistente,
                                      estudo=estudo,
                                      pacientes=pacientes)
            
            # Criar exame
            novo_exame = ExameImagem(
                paciente_id=paciente_id,
                orthanc_study_uid=orthanc_study_uid,
                tipo_exame=tipo_exame,
                descricao=descricao or '',
                data_realizacao=datetime.utcnow(),  # Idealmente, usar a data do DICOM
                status='pendente'
            )
            
            db.session.add(novo_exame)
            db.session.commit()
            
            flash('Exame cadastrado com sucesso', 'success')
            return redirect(url_for('assistente.exame_detalhes', id=novo_exame.id))
        
        # Buscar pacientes para o select
        pacientes = Paciente.query.join(Usuario).order_by(Usuario.nome_completo).all()
        
        return render_template('assistente/cadastrar_exame_orthanc.html', 
                              assistente=assistente,
                              estudo=estudo,
                              pacientes=pacientes)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao cadastrar exame Orthanc: {str(e)}")
        flash('Erro ao processar cadastro de exame. Tente novamente.', 'danger')
        return redirect(url_for('assistente.buscar_exames_orthanc'))

@assistente_bp.route('/exame/<int:id>')
def exame_detalhes(id):
    try:
        # Obter o assistente logado
        user_id = session.get('user_id')
        assistente = Usuario.query.filter_by(id=user_id).first()
        
        if not assistente:
            flash('Perfil de assistente não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        # Obter exame
        exame = ExameImagem.query.get_or_404(id)
        
        # Buscar detalhes do estudo no Orthanc
        try:
            estudo = obter_detalhes_estudo_orthanc(exame.orthanc_study_uid) if exame.orthanc_study_uid else None
        except Exception as e:
            current_app.logger.warning(f"Erro ao buscar detalhes do estudo no Orthanc: {str(e)}")
            estudo = None
        
        # Obter laudo (se existir)
        laudo = Documento.query.filter_by(
            exame_imagem_id=exame.id,
            tipo='laudo'
        ).first()
        
        return render_template('assistente/exame_detalhes.html', 
                              assistente=assistente,
                              exame=exame,
                              estudo=estudo,
                              laudo=laudo)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar detalhes do exame: {str(e)}")
        flash('Erro ao carregar detalhes do exame. Tente novamente.', 'danger')
        return redirect(url_for('assistente.exames'))

@assistente_bp.route('/anexar_laudo/<int:exame_id>', methods=['GET', 'POST'])
def anexar_laudo(exame_id):
    try:
        # Obter o assistente logado
        user_id = session.get('user_id')
        assistente = Usuario.query.filter_by(id=user_id).first()
        
        if not assistente:
            flash('Perfil de assistente não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        # Obter exame
        exame = ExameImagem.query.get_or_404(exame_id)
        
        # Verificar se já existe laudo
        laudo_existente = Documento.query.filter_by(
            exame_imagem_id=exame.id,
            tipo='laudo'
        ).first()
        
        if laudo_existente:
            flash('Este exame já possui um laudo anexado', 'warning')
            return redirect(url_for('assistente.exame_detalhes', id=exame.id))
        
        if request.method == 'POST':
            titulo = request.form.get('titulo')
            descricao = request.form.get('descricao', '')
            
            if not titulo:
                flash('Título é obrigatório', 'danger')
                return render_template('assistente/anexar_laudo.html', 
                                      assistente=assistente,
                                      exame=exame)
            
            # Upload do arquivo
            arquivo_caminho = None
            if 'arquivo' in request.files:
                file = request.files['arquivo']
                if file and file.filename and file.filename.endswith('.pdf'):
                    filename = secure_filename(file.filename)
                    upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'laudos', str(exame.paciente_id))
                    
                    # Criar diretório se não existir
                    if not os.path.exists(upload_dir):
                        os.makedirs(upload_dir, exist_ok=True)
                    
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    file_path = os.path.join(upload_dir, f"{timestamp}_{filename}")
                    file.save(file_path)
                    arquivo_caminho = file_path
                else:
                    flash('Arquivo deve ser um PDF válido', 'danger')
                    return render_template('assistente/anexar_laudo.html', 
                                          assistente=assistente,
                                          exame=exame)
            
            if not arquivo_caminho:
                flash('Arquivo é obrigatório', 'danger')
                return render_template('assistente/anexar_laudo.html', 
                                      assistente=assistente,
                                      exame=exame)
            
            try:
                # Criar documento
                documento = Documento(
                    paciente_id=exame.paciente_id,
                    exame_imagem_id=exame.id,
                    tipo='laudo',
                    titulo=titulo,
                    descricao=descricao,
                    arquivo_caminho=arquivo_caminho,
                    status='disponivel',
                    data_criacao=datetime.utcnow()
                )
                
                # Adicionar assistente_id apenas se o campo existir
                if hasattr(documento, 'assistente_id'):
                    documento.assistente_id = assistente.id
                
                db.session.add(documento)
                
                # Atualizar status do exame
                exame.status = 'laudado'
                if hasattr(exame, 'data_laudo'):
                    exame.data_laudo = datetime.utcnow()
                
                db.session.commit()
                
                # ==============================================
                # NOVA FUNCIONALIDADE: ENVIAR NOTIFICAÇÕES
                # ==============================================
                
                try:
                    if NOTIFICACAO_DISPONIVEL and notificar_laudo_disponivel:
                        current_app.logger.info(f"📧 Enviando notificações de laudo para paciente: {exame.paciente.usuario.nome_completo}")
                        
                        # Preparar dados para notificação
                        data_realizacao_str = None
                        if exame.data_realizacao:
                            data_realizacao_str = exame.data_realizacao.strftime('%d/%m/%Y')
                        
                        # Tentar obter médico responsável do documento ou exame
                        medico_responsavel = None
                        if hasattr(documento, 'profissional') and documento.profissional:
                            medico_responsavel = documento.profissional.usuario.nome_completo
                        elif hasattr(exame, 'medico_solicitante'):
                            medico_responsavel = exame.medico_solicitante
                        
                        # Enviar notificação
                        resultado_notificacao = notificar_laudo_disponivel(
                            paciente=exame.paciente,
                            tipo_exame=exame.tipo_exame,
                            data_realizacao=data_realizacao_str,
                            medico_responsavel=medico_responsavel
                        )
                        
                        # Processar resultado da notificação
                        if resultado_notificacao.get('resumo'):
                            sucessos = resultado_notificacao['resumo'].get('sucessos', [])
                            if sucessos:
                                flash(f'Laudo anexado e paciente notificado via {", ".join(sucessos)}!', 'success')
                                current_app.logger.info(f"✅ Notificações de laudo enviadas via: {', '.join(sucessos)}")
                            else:
                                flash('Laudo anexado com sucesso! Porém não foi possível enviar notificações.', 'warning')
                                current_app.logger.warning("⚠️ Nenhuma notificação de laudo foi enviada")
                                
                                # Log detalhado dos erros
                                if not resultado_notificacao['email']['sucesso']:
                                    current_app.logger.warning(f"Email de laudo não enviado: {resultado_notificacao['email']['erro']}")
                                if not resultado_notificacao['whatsapp']['sucesso']:
                                    current_app.logger.warning(f"WhatsApp de laudo não enviado: {resultado_notificacao['whatsapp']['erro']}")
                        else:
                            flash('Laudo anexado com sucesso! Porém houve erro nas notificações.', 'warning')
                            current_app.logger.error(f"❌ Erro no resultado da notificação de laudo: {resultado_notificacao}")
                            
                    else:
                        flash('Laudo anexado com sucesso!', 'success')
                        current_app.logger.warning("⚠️ Serviço de notificação não disponível para laudo")
                        
                except Exception as e:
                    # Se a notificação falhar, não deve afetar o anexo do laudo
                    current_app.logger.error(f"❌ Erro ao enviar notificações de laudo: {str(e)}")
                    flash('Laudo anexado com sucesso! Porém houve erro ao enviar notificações.', 'warning')
                
                return redirect(url_for('assistente.exame_detalhes', id=exame.id))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erro ao anexar laudo: {str(e)}")
                flash(f'Erro ao anexar laudo: {str(e)}', 'danger')
                return render_template('assistente/anexar_laudo.html', 
                                      assistente=assistente,
                                      exame=exame)
        
        return render_template('assistente/anexar_laudo.html', 
                              assistente=assistente,
                              exame=exame)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao anexar laudo: {str(e)}")
        flash('Erro ao anexar laudo. Tente novamente.', 'danger')
        return redirect(url_for('assistente.exame_detalhes', id=exame_id))

@assistente_bp.route('/remover_laudo/<int:exame_id>', methods=['POST'])
def remover_laudo(exame_id):
    try:
        # Obter o assistente logado
        user_id = session.get('user_id')
        assistente = Usuario.query.filter_by(id=user_id).first()
        
        if not assistente:
            flash('Perfil de assistente não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        # Obter exame
        exame = ExameImagem.query.get_or_404(exame_id)
        
        # Obter laudo
        laudo = Documento.query.filter_by(
            exame_imagem_id=exame.id,
            tipo='laudo'
        ).first()
        
        if not laudo:
            flash('Laudo não encontrado', 'danger')
            return redirect(url_for('assistente.exame_detalhes', id=exame.id))
        
        # Remover arquivo físico
        if laudo.arquivo_caminho and os.path.exists(laudo.arquivo_caminho):
            try:
                os.remove(laudo.arquivo_caminho)
            except Exception as e:
                current_app.logger.warning(f"Erro ao remover arquivo físico: {str(e)}")
        
        # Remover laudo do banco de dados
        db.session.delete(laudo)
        
        # Atualizar status do exame
        exame.status = 'pendente'
        if hasattr(exame, 'data_laudo'):
            exame.data_laudo = None
        
        db.session.commit()
        
        flash('Laudo removido com sucesso', 'success')
        return redirect(url_for('assistente.exame_detalhes', id=exame.id))
    
    except Exception as e:
        current_app.logger.error(f"Erro ao remover laudo: {str(e)}")
        flash('Erro ao remover laudo. Tente novamente.', 'danger')
        return redirect(url_for('assistente.exame_detalhes', id=exame_id))

@assistente_bp.route('/visualizar_imagens/<string:orthanc_study_uid>')
def visualizar_imagens(orthanc_study_uid):
    try:
        # Obter o assistente logado
        user_id = session.get('user_id')
        assistente = Usuario.query.filter_by(id=user_id).first()
        
        if not assistente:
            flash('Perfil de assistente não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        # Obter URL do visualizador DICOM
        orthanc_viewer_url = current_app.config.get('ORTHANC_VIEWER_URL')
        
        if not orthanc_viewer_url:
            flash('URL do visualizador DICOM não configurada', 'danger')
            return redirect(url_for('assistente.exames'))
        
        # Construir URL completa
        url_completa = f"{orthanc_viewer_url}?study={orthanc_study_uid}"
        
        return redirect(url_completa)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao visualizar imagens: {str(e)}")
        flash('Erro ao abrir visualizador de imagens. Tente novamente.', 'danger')
        return redirect(url_for('assistente.exames'))

@assistente_bp.route('/buscar_paciente', methods=['GET', 'POST'])
def buscar_paciente():
    try:
        # Obter o assistente logado
        user_id = session.get('user_id')
        assistente = Usuario.query.filter_by(id=user_id).first()
        
        if not assistente:
            flash('Perfil de assistente não encontrado', 'danger')
            return redirect(url_for('auth.logout'))
        
        if request.method == 'POST':
            cpf = request.form.get('cpf')
            
            if not cpf:
                flash('CPF é obrigatório', 'danger')
                return render_template('assistente/buscar_paciente.html', assistente=assistente)
            
            # Limpar CPF
            cpf = ''.join(filter(str.isdigit, cpf))
            
            # Buscar paciente pelo CPF
            paciente = Paciente.query.join(Usuario).filter(Usuario.cpf == cpf).first()
            
            if not paciente:
                flash('Paciente não encontrado', 'warning')
                return render_template('assistente/buscar_paciente.html', assistente=assistente)
            
            # Buscar exames do paciente
            exames = ExameImagem.query.filter_by(
                paciente_id=paciente.id
            ).order_by(ExameImagem.data_realizacao.desc()).all()
            
            return render_template('assistente/paciente_exames.html', 
                                  assistente=assistente,
                                  paciente=paciente,
                                  exames=exames)
        
        return render_template('assistente/buscar_paciente.html', assistente=assistente)
    
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar paciente: {str(e)}")
        flash('Erro ao buscar paciente. Tente novamente.', 'danger')
        return redirect(url_for('assistente.dashboard'))

# ==============================================
# NOVA ROTA: DEBUG DE NOTIFICAÇÕES
# ==============================================

@assistente_bp.route('/debug/notificacoes')
def debug_notificacoes_assistente():
    """Rota de debug para testar serviços de notificação (apenas em modo debug)"""
    if not current_app.debug:
        flash('Função disponível apenas em modo debug', 'danger')
        return redirect(url_for('assistente.dashboard'))
    
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

# Funções auxiliares para interação com o Orthanc

def obter_estudos_orthanc():
    """Obtém a lista de estudos do Orthanc"""
    # Configurações do Orthanc
    orthanc_url = current_app.config.get('ORTHANC_URL')
    orthanc_user = current_app.config.get('ORTHANC_USER')
    orthanc_password = current_app.config.get('ORTHANC_PASSWORD')
    
    if not orthanc_url:
        raise Exception("URL do Orthanc não configurada")
    
    # Autenticação
    auth = (orthanc_user, orthanc_password) if orthanc_user and orthanc_password else None
    
    # Buscar estudos
    response = requests.get(f"{orthanc_url}/studies", auth=auth, timeout=10)
    
    if response.status_code != 200:
        raise Exception(f"Erro ao buscar estudos: {response.text}")
    
    # Obter IDs dos estudos
    study_ids = response.json()
    
    # Buscar detalhes de cada estudo (limitar a 10 estudos para performance)
    estudos = []
    for study_id in study_ids[:10]:
        try:
            estudo = obter_detalhes_estudo_orthanc(study_id)
            estudos.append(estudo)
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar detalhes do estudo {study_id}: {str(e)}")
            continue
    
    return estudos

def obter_detalhes_estudo_orthanc(study_id):
    """Obtém os detalhes de um estudo específico do Orthanc"""
    # Configurações do Orthanc
    orthanc_url = current_app.config.get('ORTHANC_URL')
    orthanc_user = current_app.config.get('ORTHANC_USER')
    orthanc_password = current_app.config.get('ORTHANC_PASSWORD')
    
    if not orthanc_url:
        raise Exception("URL do Orthanc não configurada")
    
    # Autenticação
    auth = (orthanc_user, orthanc_password) if orthanc_user and orthanc_password else None
    
    # Buscar detalhes do estudo
    response = requests.get(f"{orthanc_url}/studies/{study_id}", auth=auth, timeout=10)
    
    if response.status_code != 200:
        raise Exception(f"Erro ao buscar detalhes do estudo: {response.text}")
    
    # Processar resposta
    estudo = response.json()
    
    # Extrair informações relevantes
    resultado = {
        'ID': estudo.get('ID', study_id),
        'PatientName': estudo.get('PatientMainDicomTags', {}).get('PatientName', 'Desconhecido'),
        'PatientID': estudo.get('PatientMainDicomTags', {}).get('PatientID', ''),
        'StudyDate': estudo.get('MainDicomTags', {}).get('StudyDate', ''),
        'StudyTime': estudo.get('MainDicomTags', {}).get('StudyTime', ''),
        'StudyDescription': estudo.get('MainDicomTags', {}).get('StudyDescription', ''),
        'AccessionNumber': estudo.get('MainDicomTags', {}).get('AccessionNumber', ''),
        'ReferringPhysicianName': estudo.get('MainDicomTags', {}).get('ReferringPhysicianName', ''),
        'SeriesCount': len(estudo.get('Series', [])),
        'InstancesCount': sum(len(serie.get('Instances', [])) for serie in estudo.get('Series', []))
    }
    
    return resultado
