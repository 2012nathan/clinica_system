#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UltraClin System - Main Application File
Sistema de Gerenciamento de Clínica com Múltiplos Perfis
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import json
import random
import string

# CARREGAR ARQUIVO .ENV PRIMEIRO - ANTES DE QUALQUER COISA
from dotenv import load_dotenv
load_dotenv()

# Adicionar o diretório src ao path do Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, g
from werkzeug.security import generate_password_hash
from flask_migrate import upgrade

# Importações das extensões
from src.extensions import db, migrate, init_extensions

# Importações das configurações
from src.config import config_by_name

# Importações dos blueprints
from src.routes.auth import auth_bp
from src.routes.admin import admin_bp
from src.routes.medico import medico_bp
from src.routes.assistente import assistente_bp
from src.routes.paciente import paciente_bp
from src.routes.api import api_bp

# Importar blueprint main se existir
try:
    from src.routes.main import main_bp
    MAIN_BP_DISPONIVEL = True
except ImportError:
    MAIN_BP_DISPONIVEL = False
    print("⚠️  Blueprint main não encontrado - usando rotas padrão")

# Importar blueprint laboratorio se existir
try:
    from src.routes.laboratorio import laboratorio_bp
    LABORATORIO_DISPONIVEL = True
except ImportError:
    LABORATORIO_DISPONIVEL = False
    print("⚠️  Blueprint laboratorio não encontrado - recursos de laboratório não disponíveis")

# Importar blueprints de agenda se existirem
try:
    from src.routes.assistente_agenda import assistente_agenda_bp
    ASSISTENTE_AGENDA_DISPONIVEL = True
    print("✅ Blueprint assistente_agenda carregado com sucesso")
except ImportError:
    ASSISTENTE_AGENDA_DISPONIVEL = False
    print("⚠️  Blueprint assistente_agenda não encontrado")

try:
    from src.routes.paciente_agenda import paciente_agenda_bp
    PACIENTE_AGENDA_DISPONIVEL = True
    print("✅ Blueprint paciente_agenda carregado com sucesso")
except ImportError:
    PACIENTE_AGENDA_DISPONIVEL = False
    print("⚠️  Blueprint paciente_agenda não encontrado")

# Importações dos modelos (importante para migrations)
from src.models.usuario import Usuario
from src.models.perfil import Perfil
from src.models.paciente import Paciente
from src.models.profissional import Profissional
from src.models.especialidade import Especialidade
from src.models.agendamento import Agendamento
from src.models.documento import Documento
from src.models.exame_imagem import ExameImagem
from src.models.cartao_gestante import CartaoGestante
from src.models.disponibilidade import DisponibilidadeProfissional

# Importar text do SQLAlchemy para compatibilidade com 2.0
from sqlalchemy import text

# Importar exame_laboratorial se existir
try:
    from src.models.exame_laboratorial import ExameLaboratorial
    EXAME_LABORATORIAL_DISPONIVEL = True
except ImportError:
    EXAME_LABORATORIAL_DISPONIVEL = False
    print("⚠️  Modelo ExameLaboratorial não encontrado")

# Importar o serviço SHOSP
try:
    from src.services.shosp_service import shosp_service
    SHOSP_DISPONIVEL = True
    print("✅ Serviço SHOSP carregado com sucesso")
except ImportError as e:
    print(f"⚠️  Serviço SHOSP não disponível: {str(e)}")
    SHOSP_DISPONIVEL = False
    # Criar um mock do serviço para evitar erros
    class MockShospService:
        def buscar_paciente_por_cpf(self, cpf):
            return None
        def verificar_cpf_existe(self, cpf):
            return False
        def cadastrar_paciente(self, dados):
            return None
    shosp_service = MockShospService()

def create_app(config_name=None):
    """Factory function para criar a aplicação Flask"""
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    # Criar instância do Flask
    app = Flask(__name__, 
                template_folder='src/templates',
                static_folder='src/static')
    
    # Carregar configurações
    try:
        config_class = config_by_name.get(config_name, config_by_name['development'])
        app.config.from_object(config_class)
        app.logger.info(f"Configuração carregada: {config_name}")
    except Exception as e:
        app.logger.error(f"Erro ao carregar configuração: {str(e)}")
        # Configuração de fallback com correção das variáveis de banco
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
        
        # CORREÇÃO: Usar as variáveis corretas do .env
        db_user = os.getenv('DB_USER', os.getenv('DB_USERNAME', 'root'))
        db_password = os.getenv('DB_PASSWORD', 'password')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '3306')
        db_name = os.getenv('DB_NAME', 'ultraclin_db')
        
        app.config['SQLALCHEMY_DATABASE_URI'] = (
            f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        )
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        print(f"⚠️  Usando configuração de fallback para banco de dados")
        print(f"Database URI: mysql+pymysql://{db_user}:***@{db_host}:{db_port}/{db_name}")
    
    # Configurar logging
    if not app.debug:
        logging.basicConfig(level=logging.INFO)
    
    # Log das configurações carregadas
    app.logger.info(f"Configurações do banco carregadas com sucesso")
    
    # Inicializar extensões
    init_extensions(app)
    print("✅ Extensões inicializadas com sucesso!")
    
    # Registrar blueprint main se disponível
    if MAIN_BP_DISPONIVEL:
        app.register_blueprint(main_bp, url_prefix='/')
        print("✅ Blueprint main registrado")
    
    # Registrar blueprints principais
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(medico_bp, url_prefix='/medico')
    app.register_blueprint(assistente_bp, url_prefix='/assistente')
    app.register_blueprint(paciente_bp, url_prefix='/paciente')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Registrar blueprints de agenda se disponíveis
    if ASSISTENTE_AGENDA_DISPONIVEL:
        app.register_blueprint(assistente_agenda_bp, url_prefix='/assistente/agenda')
        print("✅ Blueprint assistente_agenda registrado")
    
    if PACIENTE_AGENDA_DISPONIVEL:
        app.register_blueprint(paciente_agenda_bp, url_prefix='/paciente/agenda')
        print("✅ Blueprint paciente_agenda registrado")
    
    # Registrar blueprint laboratorio se disponível
    if LABORATORIO_DISPONIVEL:
        app.register_blueprint(laboratorio_bp, url_prefix='/laboratorio')
        print("✅ Blueprint laboratorio registrado")
    
    # Context processors globais
    @app.context_processor
    def inject_globals():
        """Injeta variáveis globais nos templates"""
        return {
            'current_year': datetime.now().year,
            'is_authenticated': 'user_id' in session,
            'current_user_name': session.get('user_name', ''),
            'current_perfil': session.get('perfil_atual', session.get('user_tipo', '')),
            'session': session,
            'laboratorio_disponivel': LABORATORIO_DISPONIVEL,
            'exame_laboratorial_disponivel': EXAME_LABORATORIAL_DISPONIVEL
        }
    
    @app.before_request
    def before_request():
        """Executado antes de cada request"""
        g.start_time = datetime.now()
        
        # Log de debug das rotas
        if app.debug:
            app.logger.debug(f"Request: {request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        """Executado após cada request"""
        if hasattr(g, 'start_time'):
            duration = datetime.now() - g.start_time
            if app.debug:
                app.logger.debug(f"Request duration: {duration.total_seconds():.3f}s")
        return response
    
    # Rota principal (apenas se main_bp não estiver disponível)
    if not MAIN_BP_DISPONIVEL:
        @app.route('/')
        def index():
            """Página inicial - redireciona baseado no status de autenticação"""
            if 'user_id' in session:
                # Usuário logado - redirecionar para dashboard apropriado
                perfil_atual = session.get('perfil_atual', session.get('user_tipo', 'paciente'))
                
                if perfil_atual == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif perfil_atual == 'medico':
                    return redirect(url_for('medico.dashboard'))
                elif perfil_atual == 'assistente':
                    return redirect(url_for('assistente.dashboard'))
                elif perfil_atual == 'paciente':
                    return redirect(url_for('paciente.dashboard'))
                else:
                    # Perfil não reconhecido, voltar ao login
                    session.clear()
                    return redirect(url_for('auth.login'))
            else:
                # Usuário não logado - ir para login
                return redirect(url_for('auth.login'))
    
    # Handlers de erro
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f"Erro interno do servidor: {str(error)}")
        return render_template('500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('403.html'), 403
    
    # ================================
    # ROTAS DE INTEGRAÇÃO SHOSP
    # ================================
    
    @app.route('/api/auth/primeiro-acesso', methods=['POST'])
    def primeiro_acesso_api():
        """
        API para primeiro acesso - verifica CPF no SHOSP
        """
        try:
            if not SHOSP_DISPONIVEL:
                return jsonify({
                    'erro': 'Serviço SHOSP não disponível',
                    'encontrado': False,
                    'requer_cadastro_manual': True
                }), 503

            dados = request.get_json()
            if not dados:
                return jsonify({'erro': 'Dados não fornecidos'}), 400
                
            cpf = dados.get('cpf', '').replace('.', '').replace('-', '').replace(' ', '')
            
            if not cpf or len(cpf) != 11:
                return jsonify({'erro': 'CPF inválido'}), 400
            
            app.logger.info(f"Verificando primeiro acesso para CPF: {cpf}")
            
            # Verificar se paciente existe no SHOSP
            paciente_shosp = shosp_service.buscar_paciente_por_cpf(cpf)
            
            if paciente_shosp:
                app.logger.info(f"Paciente encontrado no SHOSP: {cpf}")
                # Paciente encontrado no SHOSP
                return jsonify({
                    'encontrado': True,
                    'paciente': {
                        'nome': paciente_shosp.get('nome'),
                        'cpf': paciente_shosp.get('cpf'),
                        'email': paciente_shosp.get('email'),
                        'dataNascimento': paciente_shosp.get('dataNascimento'),
                        'sexo': paciente_shosp.get('sexo'),
                        'telefone': paciente_shosp.get('telefone'),
                        'celular': paciente_shosp.get('celular'),
                        'prontuario': paciente_shosp.get('prontuario'),
                        'nomeMae': paciente_shosp.get('nomeMae'),
                        'endereco': paciente_shosp.get('logradouro')
                    },
                    'origem': 'shosp'
                })
            else:
                app.logger.info(f"Paciente NÃO encontrado no SHOSP: {cpf}")
                # Paciente NÃO encontrado no SHOSP
                return jsonify({
                    'encontrado': False,
                    'cpf': cpf,
                    'origem': 'novo',
                    'requer_cadastro': True
                })
                
        except Exception as e:
            app.logger.error(f"Erro no primeiro acesso: {str(e)}")
            return jsonify({'erro': f'Erro interno: {str(e)}'}), 500

    @app.route('/api/paciente/cadastrar-completo', methods=['POST'])
    def cadastrar_paciente_completo():
        """
        API para cadastrar paciente (local e no SHOSP)
        """
        try:
            dados = request.get_json()
            if not dados:
                return jsonify({'erro': 'Dados não fornecidos'}), 400
            
            # Validar dados obrigatórios
            campos_obrigatorios = ['cpf', 'nome_completo', 'email', 'data_nascimento']
            for campo in campos_obrigatorios:
                if not dados.get(campo):
                    return jsonify({'erro': f'Campo obrigatório: {campo}'}), 400
            
            cpf = dados.get('cpf', '').replace('.', '').replace('-', '').replace(' ', '')
            
            if len(cpf) != 11:
                return jsonify({'erro': 'CPF inválido'}), 400
            
            app.logger.info(f"Iniciando cadastro completo para CPF: {cpf}")
            
            # Verificar se já existe usuário local com este CPF
            usuario_existente = Usuario.query.filter_by(cpf=cpf).first()
            if usuario_existente:
                return jsonify({'erro': 'CPF já cadastrado no sistema local'}), 400
            
            # Verificar se email já existe
            email_existente = Usuario.query.filter_by(email=dados['email']).first()
            if email_existente:
                return jsonify({'erro': 'Email já cadastrado por outro usuário'}), 400
            
            resultado_cadastro = {
                'sucesso_local': False,
                'sucesso_shosp': False,
                'dados_shosp': None,
                'usuario_id': None,
                'mensagens': []
            }
            
            # 1. Tentar cadastrar no SHOSP primeiro (se disponível)
            if SHOSP_DISPONIVEL:
                # Verificar se já existe no SHOSP
                paciente_existente_shosp = shosp_service.buscar_paciente_por_cpf(cpf)
                
                if not paciente_existente_shosp:
                    # Preparar dados para SHOSP
                    sexo = dados.get('sexo', 'M').upper()
                    if sexo not in ['M', 'F']:
                        sexo = 'M'  # Padrão
                    
                    dados_shosp = {
                        'cpf': cpf,
                        'nome': dados['nome_completo'].upper(),
                        'email': dados['email'].lower(),
                        'dataNascimento': dados['data_nascimento'],
                        'sexo': sexo,
                        'telefone': dados.get('telefone', ''),
                        'celular': dados.get('celular', ''),
                        'nomeMae': dados.get('nome_mae', ''),
                        'logradouro': dados.get('endereco', ''),
                        'numero': dados.get('numero', ''),
                        'bairro': dados.get('bairro', ''),
                        'cep': dados.get('cep', '')
                    }
                    
                    app.logger.info(f"Tentando cadastrar no SHOSP: {cpf}")
                    paciente_shosp = shosp_service.cadastrar_paciente(dados_shosp)
                    
                    if paciente_shosp:
                        resultado_cadastro['sucesso_shosp'] = True
                        resultado_cadastro['dados_shosp'] = paciente_shosp
                        resultado_cadastro['mensagens'].append('Cadastrado com sucesso no SHOSP')
                        app.logger.info(f"Paciente cadastrado no SHOSP: {cpf}")
                    else:
                        resultado_cadastro['mensagens'].append('Falha ao cadastrar no SHOSP, prosseguindo apenas localmente')
                        app.logger.warning(f"Falha ao cadastrar no SHOSP: {cpf}")
                else:
                    resultado_cadastro['sucesso_shosp'] = True
                    resultado_cadastro['dados_shosp'] = paciente_existente_shosp
                    resultado_cadastro['mensagens'].append('Paciente já existia no SHOSP')
                    app.logger.info(f"Paciente já existia no SHOSP: {cpf}")
            
            # 2. Cadastrar localmente
            try:
                # Buscar ou criar perfil paciente
                perfil_paciente = Perfil.query.filter_by(nome='paciente').first()
                if not perfil_paciente:
                    perfil_paciente = Perfil(nome='paciente', descricao='Paciente da clínica')
                    db.session.add(perfil_paciente)
                    db.session.flush()
                
                # Gerar senha provisória
                def gerar_senha_provisoria(tamanho=8):
                    caracteres = string.ascii_letters + string.digits
                    return ''.join(random.choice(caracteres) for i in range(tamanho))
                
                senha_provisoria = gerar_senha_provisoria()
                
                # Criar usuário
                novo_usuario = Usuario(
                    nome_completo=dados['nome_completo'],
                    cpf=cpf,
                    data_nascimento=datetime.strptime(dados['data_nascimento'], '%Y-%m-%d').date(),
                    email=dados['email'],
                    telefone=dados.get('celular', dados.get('telefone', '')),
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
                    cartao_sus=dados.get('cartao_sus', ''),
                    convenio=dados.get('convenio', ''),
                    numero_convenio=dados.get('numero_convenio', '')
                )
                
                # Adicionar observações se houver
                if hasattr(novo_paciente, 'observacoes'):
                    observacoes = []
                    if dados.get('como_conheceu'):
                        observacoes.append(f"Como conheceu: {dados['como_conheceu']}")
                    observacoes.append(f"Cadastrado via sistema em {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}")
                    novo_paciente.observacoes = ". ".join(observacoes)
                
                db.session.add(novo_paciente)
                db.session.commit()
                
                resultado_cadastro['sucesso_local'] = True
                resultado_cadastro['usuario_id'] = novo_usuario.id
                resultado_cadastro['senha_provisoria'] = senha_provisoria
                resultado_cadastro['mensagens'].append('Cadastrado com sucesso no sistema local')
                
                app.logger.info(f"Paciente cadastrado localmente: {cpf} - ID: {novo_usuario.id}")
                
                # Tentar enviar senha provisória por email
                try:
                    from src.services.unified_email_service import enviar_senha_provisoria
                    enviar_senha_provisoria(novo_usuario, senha_provisoria)
                    resultado_cadastro['mensagens'].append('Senha provisória enviada por email')
                except Exception as e:
                    app.logger.error(f"Erro ao enviar email: {str(e)}")
                    resultado_cadastro['mensagens'].append('Erro ao enviar email - senha provisória disponível no retorno')
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erro no cadastro local: {str(e)}")
                return jsonify({'erro': f'Erro no cadastro local: {str(e)}'}), 500
            
            # 3. Preparar resposta
            if resultado_cadastro['sucesso_local']:
                return jsonify({
                    'sucesso': True,
                    'usuario_id': resultado_cadastro['usuario_id'],
                    'senha_provisoria': resultado_cadastro.get('senha_provisoria'),
                    'shosp_sincronizado': resultado_cadastro['sucesso_shosp'],
                    'dados_shosp': resultado_cadastro['dados_shosp'],
                    'mensagens': resultado_cadastro['mensagens']
                })
            else:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Falha no cadastro local',
                    'mensagens': resultado_cadastro['mensagens']
                }), 500
                
        except Exception as e:
            app.logger.error(f"Erro no cadastro completo: {str(e)}")
            return jsonify({'erro': f'Erro interno: {str(e)}'}), 500

    @app.route('/api/verificar-cpf', methods=['POST'])
    def verificar_cpf_api():
        """
        API para verificar se CPF existe no SHOSP
        """
        try:
            dados = request.get_json()
            if not dados:
                return jsonify({'erro': 'Dados não fornecidos'}), 400
                
            cpf = dados.get('cpf', '').replace('.', '').replace('-', '').replace(' ', '')
            
            if not cpf or len(cpf) != 11:
                return jsonify({'erro': 'CPF inválido'}), 400
            
            # Verificar no sistema local primeiro
            usuario_local = Usuario.query.filter_by(cpf=cpf).first()
            
            resultado = {
                'cpf': cpf,
                'existe_local': usuario_local is not None,
                'existe_shosp': False,
                'dados_shosp': None,
                'pode_cadastrar': True
            }
            
            # Verificar no SHOSP se disponível
            if SHOSP_DISPONIVEL:
                existe_shosp = shosp_service.verificar_cpf_existe(cpf)
                paciente_shosp = shosp_service.buscar_paciente_por_cpf(cpf) if existe_shosp else None
                
                resultado['existe_shosp'] = existe_shosp
                resultado['dados_shosp'] = paciente_shosp
            
            # Determinar se pode cadastrar
            resultado['pode_cadastrar'] = not usuario_local
            
            if usuario_local:
                resultado['perfis_locais'] = [perfil.nome for perfil in usuario_local.perfis]
            
            return jsonify(resultado)
            
        except Exception as e:
            app.logger.error(f"Erro ao verificar CPF: {str(e)}")
            return jsonify({'erro': str(e)}), 500

    # ================================
    # ROTAS DE DEBUG (apenas em modo debug)
    # ================================

    @app.route('/debug/shosp/<cpf>')
    def debug_shosp(cpf):
        """
        Função de debug para testar SHOSP
        """
        if not app.debug:
            return jsonify({'erro': 'Disponível apenas em modo debug'}), 403
        
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        if len(cpf_limpo) != 11:
            return jsonify({'erro': 'CPF deve ter 11 dígitos'}), 400
        
        try:
            resultado = {
                'cpf_pesquisado': cpf_limpo,
                'shosp_disponivel': SHOSP_DISPONIVEL,
                'timestamp': datetime.now().isoformat()
            }
            
            if SHOSP_DISPONIVEL:
                # Testar GET (buscar)
                resultado_get = shosp_service.buscar_paciente_por_cpf(cpf_limpo)
                resultado.update({
                    'encontrado': resultado_get is not None,
                    'dados': resultado_get,
                    'status': 'SHOSP funcionando!' if resultado_get else 'CPF não encontrado no SHOSP'
                })
            else:
                resultado.update({
                    'encontrado': False,
                    'dados': None,
                    'status': 'SHOSP não disponível'
                })
            
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({
                'erro': str(e),
                'cpf_pesquisado': cpf_limpo,
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/debug/teste-completo-shosp')
    def teste_completo_shosp():
        """
        Teste completo da integração SHOSP
        """
        if not app.debug:
            return jsonify({'erro': 'Disponível apenas em modo debug'}), 403
        
        resultados = {
            'shosp_disponivel': SHOSP_DISPONIVEL,
            'timestamp': datetime.now().isoformat()
        }
        
        if not SHOSP_DISPONIVEL:
            resultados['status'] = 'SHOSP não disponível - configurações podem estar incorretas'
            return jsonify(resultados)
        
        try:
            # Teste 1: Buscar CPF existente (use um CPF real que existe no SHOSP)
            cpf_teste = "10545855713"  # CPF de teste - substitua por um real se necessário
            paciente = shosp_service.buscar_paciente_por_cpf(cpf_teste)
            resultados['teste_busca'] = {
                'cpf': cpf_teste,
                'encontrado': paciente is not None,
                'dados': paciente
            }
            
            # Teste 2: Verificar CPF inexistente
            cpf_inexistente = "12345678901"
            existe = shosp_service.verificar_cpf_existe(cpf_inexistente)
            resultados['teste_inexistente'] = {
                'cpf': cpf_inexistente,
                'existe': existe
            }
            
            # Teste 3: Verificar configurações
            resultados['configuracoes'] = {
                'api_id_configurado': bool(os.getenv('SHOSP_API_ID')),
                'api_key_configurado': bool(os.getenv('SHOSP_API_KEY')),
                'api_url_configurado': bool(os.getenv('SHOSP_API_URL')),
                'url_completa': os.getenv('SHOSP_API_URL')
            }
            
            resultados['status'] = 'SHOSP integração funcionando!'
            
        except Exception as e:
            resultados['erro'] = str(e)
            resultados['status'] = 'Erro na integração SHOSP'
        
        return jsonify(resultados)

    @app.route('/debug/config-shosp')
    def debug_config_shosp():
        """
        Debug das configurações SHOSP
        """
        if not app.debug:
            return jsonify({'erro': 'Disponível apenas em modo debug'}), 403
        
        config_info = {
            'shosp_disponivel': SHOSP_DISPONIVEL,
            'variaveis_ambiente': {
                'SHOSP_API_ID': bool(os.getenv('SHOSP_API_ID')),
                'SHOSP_API_KEY': bool(os.getenv('SHOSP_API_KEY')),
                'SHOSP_API_URL': os.getenv('SHOSP_API_URL'),
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Mascarar dados sensíveis para log
        if os.getenv('SHOSP_API_ID'):
            api_id = os.getenv('SHOSP_API_ID')
            config_info['api_id_preview'] = api_id[:4] + '*' * (len(api_id) - 4) if len(api_id) > 4 else api_id
        
        if os.getenv('SHOSP_API_KEY'):
            api_key = os.getenv('SHOSP_API_KEY')
            config_info['api_key_preview'] = api_key[:4] + '*' * (len(api_key) - 4) if len(api_key) > 4 else api_key
        
        return jsonify(config_info)

    # ================================
    # ROTA PARA TESTAR BANCO DE DADOS
    # ================================
    
    @app.route('/debug/test-db')
    def test_database():
        """
        Testa a conexão com o banco de dados
        """
        if not app.debug:
            return jsonify({'erro': 'Disponível apenas em modo debug'}), 403
        
        try:
            # Testar conexão básica - CORRIGIDO PARA SQLALCHEMY 2.0
            result = db.session.execute(text('SELECT 1'))
            result.scalar()
            
            # Contar registros de usuários
            total_usuarios = Usuario.query.count()
            total_perfis = Perfil.query.count()
            
            # Verificar configurações de banco
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'Não configurado')
            
            return jsonify({
                'status': 'Conexão OK',
                'total_usuarios': total_usuarios,
                'total_perfis': total_perfis,
                'database_uri': db_uri.replace(db_uri.split('@')[0].split('://')[-1], '***') if '@' in db_uri else db_uri,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            app.logger.error(f"Erro no teste de banco: {str(e)}")
            return jsonify({
                'status': 'Erro na conexão',
                'erro': str(e),
                'database_uri': app.config.get('SQLALCHEMY_DATABASE_URI', 'Não configurado'),
                'timestamp': datetime.now().isoformat()
            }), 500

    # ================================
    # COMANDOS CLI
    # ================================
    
    @app.cli.command()
    def init_db():
        """Inicializa o banco de dados"""
        try:
            db.create_all()
            print("✅ Banco de dados inicializado com sucesso!")
            
            # Criar perfis padrão
            perfis_padrao = [
                {'nome': 'admin', 'descricao': 'Administrador do sistema'},
                {'nome': 'medico', 'descricao': 'Médico/Profissional de Saúde'},
                {'nome': 'assistente', 'descricao': 'Assistente de Radiologia'},
                {'nome': 'paciente', 'descricao': 'Paciente da clínica'}
            ]
            
            for perfil_data in perfis_padrao:
                perfil_existente = Perfil.query.filter_by(nome=perfil_data['nome']).first()
                if not perfil_existente:
                    novo_perfil = Perfil(**perfil_data)
                    db.session.add(novo_perfil)
                    print(f"✅ Perfil criado: {perfil_data['nome']}")
            
            db.session.commit()
            print("✅ Perfis padrão criados com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro ao inicializar banco: {str(e)}")
            db.session.rollback()

    @app.cli.command()
    def create_admin():
        """Cria um usuário administrador"""
        try:
            # Verificar se já existe admin
            perfil_admin = Perfil.query.filter_by(nome='admin').first()
            if not perfil_admin:
                print("❌ Perfil admin não encontrado. Execute 'flask init-db' primeiro.")
                return
            
            admin_existente = None
            for usuario in perfil_admin.usuarios:
                admin_existente = usuario
                break
            
            if admin_existente:
                print(f"✅ Admin já existe: {admin_existente.nome_completo} ({admin_existente.email})")
                return
            
            # Dados do admin
            nome = input("Nome completo do administrador: ").strip()
            email = input("Email do administrador: ").strip()
            cpf = input("CPF do administrador (apenas números): ").strip()
            senha = input("Senha do administrador: ").strip()
            
            if not all([nome, email, cpf, senha]):
                print("❌ Todos os campos são obrigatórios")
                return
            
            # Criar usuário admin
            admin_user = Usuario(
                nome_completo=nome,
                cpf=cpf,
                email=email,
                data_nascimento=datetime.now().date(),
                telefone='',
                senha=generate_password_hash(senha),
                ativo=True,
                senha_provisoria=False
            )
            
            admin_user.perfis.append(perfil_admin)
            
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"✅ Administrador criado com sucesso: {nome} ({email})")
            
        except Exception as e:
            print(f"❌ Erro ao criar admin: {str(e)}")
            db.session.rollback()

    @app.cli.command()
    def reset_db():
        """Remove e recria o banco de dados"""
        try:
            print("⚠️  ATENÇÃO: Esta operação irá APAGAR todos os dados!")
            confirmacao = input("Digite 'CONFIRMAR' para continuar: ").strip()
            
            if confirmacao != 'CONFIRMAR':
                print("❌ Operação cancelada")
                return
            
            # Remover todas as tabelas
            db.drop_all()
            print("🗑️  Tabelas removidas")
            
            # Recriar tabelas
            db.create_all()
            print("🔧 Tabelas recriadas")
            
            # Criar perfis padrão
            perfis_padrao = [
                {'nome': 'admin', 'descricao': 'Administrador do sistema'},
                {'nome': 'medico', 'descricao': 'Médico/Profissional de Saúde'},
                {'nome': 'assistente', 'descricao': 'Assistente de Radiologia'},
                {'nome': 'paciente', 'descricao': 'Paciente da clínica'}
            ]
            
            for perfil_data in perfis_padrao:
                novo_perfil = Perfil(**perfil_data)
                db.session.add(novo_perfil)
                print(f"✅ Perfil criado: {perfil_data['nome']}")
            
            db.session.commit()
            print("✅ Banco de dados resetado com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro ao resetar banco: {str(e)}")
            db.session.rollback()

    @app.cli.command()
    def test_shosp():
        """Testa a conexão com o SHOSP"""
        try:
            print("🔍 Testando integração SHOSP...")
            print(f"Status: {'✅ Disponível' if SHOSP_DISPONIVEL else '❌ Indisponível'}")
            
            if not SHOSP_DISPONIVEL:
                print("❌ Serviço SHOSP não está disponível")
                print("Verifique as variáveis de ambiente:")
                print("- SHOSP_API_URL")
                print("- SHOSP_API_ID") 
                print("- SHOSP_API_KEY")
                return
            
            # Testar com CPF de exemplo
            cpf_teste = "12345678901"
            print(f"🔍 Testando busca com CPF: {cpf_teste}")
            
            resultado = shosp_service.buscar_paciente_por_cpf(cpf_teste)
            if resultado:
                print(f"✅ Paciente encontrado: {resultado.get('nome', 'N/A')}")
            else:
                print("ℹ️  CPF não encontrado no SHOSP (comportamento esperado para CPF de teste)")
            
            print("✅ Teste da integração SHOSP concluído!")
            
        except Exception as e:
            print(f"❌ Erro no teste SHOSP: {str(e)}")

    @app.cli.command()
    def show_config():
        """Mostra as configurações atuais"""
        try:
            print("📋 Configurações do Sistema")
            print("=" * 50)
            print(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
            print(f"Debug: {app.debug}")
            
            # Mostrar configuração de banco mascarando senha
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'Não configurado')
            if '@' in db_uri and '://' in db_uri:
                masked_uri = db_uri.replace(db_uri.split('@')[0].split('://')[-1], '***')
            else:
                masked_uri = db_uri
            print(f"Database URI: {masked_uri}")
            
            print(f"Secret Key: {'✅ Configurado' if app.config.get('SECRET_KEY') else '❌ Não configurado'}")
            print(f"SHOSP: {'✅ Disponível' if SHOSP_DISPONIVEL else '❌ Indisponível'}")
            print(f"Laboratório: {'✅ Disponível' if LABORATORIO_DISPONIVEL else '❌ Indisponível'}")
            print(f"Exame Laboratorial: {'✅ Disponível' if EXAME_LABORATORIAL_DISPONIVEL else '❌ Indisponível'}")
            
            print(f"\n🔧 Variáveis de Ambiente do Banco:")
            print(f"DB_USER: {'✅ Configurado' if os.getenv('DB_USER') else '❌ Não configurado'}")
            print(f"DB_USERNAME: {'✅ Configurado' if os.getenv('DB_USERNAME') else '❌ Não configurado'}")
            print(f"DB_PASSWORD: {'✅ Configurado' if os.getenv('DB_PASSWORD') else '❌ Não configurado'}")
            print(f"DB_HOST: {os.getenv('DB_HOST', 'Não configurado')}")
            print(f"DB_NAME: {os.getenv('DB_NAME', 'Não configurado')}")
            
            if SHOSP_DISPONIVEL:
                print("\n🔧 Configurações SHOSP:")
                print(f"API URL: {os.getenv('SHOSP_API_URL', 'Não configurado')}")
                print(f"API ID: {'✅ Configurado' if os.getenv('SHOSP_API_ID') else '❌ Não configurado'}")
                print(f"API Key: {'✅ Configurado' if os.getenv('SHOSP_API_KEY') else '❌ Não configurado'}")
            
        except Exception as e:
            print(f"❌ Erro ao mostrar configurações: {str(e)}")

    return app

# Criar instância da aplicação
app = create_app()

@app.route('/debug/notificacoes/status')
def debug_notificacoes_status():
    """Status detalhado dos serviços de notificação"""
    if not app.debug:
        return jsonify({'erro': 'Disponível apenas em modo debug'}), 403
    
    try:
        # Verificar se serviços estão disponíveis
        try:
            from src.services.notification_service import notification_service, NOTIFICATION_SERVICE_AVAILABLE
            notif_available = NOTIFICATION_SERVICE_AVAILABLE
            notif_service = notification_service
        except ImportError:
            notif_available = False
            notif_service = None
        
        try:
            from src.services.whatsapp_service import whatsapp_service, WHATSAPP_AVAILABLE
            whats_available = WHATSAPP_AVAILABLE
            whats_service = whatsapp_service
        except ImportError:
            whats_available = False
            whats_service = None
        
        try:
            from src.services.unified_email_service import email_service, EMAIL_SERVICE_AVAILABLE
            email_available = EMAIL_SERVICE_AVAILABLE
            email_srv = email_service
        except ImportError:
            email_available = False
            email_srv = None
        
        resultado = {
            'timestamp': datetime.now().isoformat(),
            'notification_service': {
                'disponivel': notif_available,
                'status': notif_service.get_status() if notif_service else None
            },
            'email_service': {
                'disponivel': email_available,
                'provider': getattr(email_srv, 'provider', None) if email_srv else None
            },
            'whatsapp_service': {
                'disponivel': whats_available,
                'api_type': getattr(whats_service, 'api_type', None) if whats_service else None
            },
            'configuracoes_env': {
                'WHATSAPP_API_URL': bool(os.getenv('WHATSAPP_API_URL')),
                'WHATSAPP_API_TOKEN': bool(os.getenv('WHATSAPP_API_TOKEN')),
                'WHATSAPP_API_TYPE': os.getenv('WHATSAPP_API_TYPE', 'z-api'),
                'EMAIL_CONFIGURADO': email_available
            }
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        app.logger.error(f"Erro no debug de notificações: {str(e)}")
        return jsonify({
            'erro': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/debug/notificacoes/teste/<cpf>')
def debug_teste_notificacao(cpf):
    """Testa notificação para um paciente específico"""
    if not app.debug:
        return jsonify({'erro': 'Disponível apenas em modo debug'}), 403
    
    try:
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        if len(cpf_limpo) != 11:
            return jsonify({'erro': 'CPF deve ter 11 dígitos'}), 400
        
        # Buscar paciente
        paciente = Paciente.query.join(Usuario).filter(Usuario.cpf == cpf_limpo).first()
        
        if not paciente:
            return jsonify({'erro': 'Paciente não encontrado'}), 404
        
        # Importar serviço de notificação
        from src.services.notification_service import notification_service, NOTIFICATION_SERVICE_AVAILABLE
        
        if not NOTIFICATION_SERVICE_AVAILABLE:
            return jsonify({'erro': 'Serviço de notificação não disponível'}), 503
        
        # Teste de notificação de resultado
        resultado_resultado = notification_service.notificar_resultado_disponivel(
            paciente=paciente,
            tipo_exame="Hemograma Completo (TESTE)",
            data_realizacao=datetime.now().strftime('%d/%m/%Y'),
            medico_solicitante="Dr. Teste"
        )
        
        # Teste de notificação de laudo  
        resultado_laudo = notification_service.notificar_laudo_disponivel(
            paciente=paciente,
            tipo_exame="Ultrassom Obstétrico (TESTE)",
            data_realizacao=datetime.now().strftime('%d/%m/%Y'),
            medico_responsavel="Dr. Teste Radiologista"
        )
        
        return jsonify({
            'paciente': {
                'nome': paciente.usuario.nome_completo,
                'email': paciente.usuario.email,
                'telefone': paciente.usuario.telefone
            },
            'teste_resultado': resultado_resultado,
            'teste_laudo': resultado_laudo,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Erro no teste de notificação: {str(e)}")
        return jsonify({
            'erro': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/debug/notificacoes/whatsapp/teste/<telefone>')
def debug_teste_whatsapp(telefone):
    """Testa envio direto via WhatsApp"""
    if not app.debug:
        return jsonify({'erro': 'Disponível apenas em modo debug'}), 403
    
    try:
        from src.services.whatsapp_service import whatsapp_service, WHATSAPP_AVAILABLE
        
        if not WHATSAPP_AVAILABLE:
            return jsonify({'erro': 'WhatsApp service não disponível'}), 503
        
        mensagem_teste = f"""🏥 *UltraClin - TESTE* 

Olá! Esta é uma mensagem de teste do sistema de notificações.

📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')}

✅ Se você recebeu esta mensagem, o WhatsApp está funcionando perfeitamente!

_Equipe UltraClin_ 💙"""
        
        resultado = whatsapp_service.enviar_mensagem(telefone, mensagem_teste)
        
        return jsonify({
            'telefone_original': telefone,
            'resultado': resultado,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Erro no teste WhatsApp: {str(e)}")
        return jsonify({
            'erro': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # Configurações para desenvolvimento
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 'yes']
    
    print("=" * 50)
    print("🏥 UltraClin System Starting...")
    print("=" * 50)
    print(f"🌐 Servidor: http://localhost:{port}")
    print(f"🔧 Debug: {debug}")
    print(f"🎯 SHOSP: {'✅ Disponível' if SHOSP_DISPONIVEL else '❌ Indisponível'}")
    print(f"🧪 Laboratório: {'✅ Disponível' if LABORATORIO_DISPONIVEL else '❌ Indisponível'}")
    print("=" * 50)
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug,
            threaded=True
        )
    except Exception as e:
        print(f"❌ Erro ao iniciar aplicação: {str(e)}")
        sys.exit(1)
