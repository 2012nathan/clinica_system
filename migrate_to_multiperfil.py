#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.extensions import db
from src.models.usuario import Usuario
from src.models.perfil import Perfil
from werkzeug.security import generate_password_hash
from datetime import datetime

def migrate_users():
    print("Iniciando migração para sistema multi-perfil...")
    
    try:
        # Obter todos os usuários
        usuarios = Usuario.query.all()
        print(f"Encontrados {len(usuarios)} usuários para migração")
        
        for usuario in usuarios:
            print(f"Migrando usuário: {usuario.nome_completo} (tipo: {usuario.tipo_perfil})")
            
            # Buscar o perfil correspondente
            perfil = Perfil.query.filter_by(nome=usuario.tipo_perfil).first()
            
            if perfil:
                # Verificar se o usuário já tem esse perfil
                if perfil not in usuario.perfis:
                    usuario.perfis.append(perfil)
                    print(f"  - Perfil '{perfil.nome}' adicionado")
                else:
                    print(f"  - Usuário já possui o perfil '{perfil.nome}'")
            else:
                print(f"  - ERRO: Perfil '{usuario.tipo_perfil}' não encontrado!")
        
        db.session.commit()
        print("Migração concluída com sucesso!")
        
        # Verificar se existe admin
        admin = Usuario.query.filter_by(tipo_perfil='admin').first()
        if not admin:
            print("Criando usuário admin padrão...")
            criar_admin_padrao()
        else:
            print(f"Admin existente encontrado: {admin.email}")
        
    except Exception as e:
        print(f"Erro durante a migração: {str(e)}")
        db.session.rollback()

def criar_admin_padrao():
    """Cria o usuário admin padrão se não existir"""
    try:
        admin = Usuario(
            nome_completo='Administrador',
            cpf='00000000000',
            data_nascimento=datetime.strptime('2000-01-01', '%Y-%m-%d').date(),
            email='admin@clinica.com',
            senha=generate_password_hash('admin123'),
            tipo_perfil='admin',
            ativo=True
        )
        
        db.session.add(admin)
        db.session.flush()
        
        # Adicionar perfil de admin
        perfil_admin = Perfil.query.filter_by(nome='admin').first()
        if perfil_admin:
            admin.perfis.append(perfil_admin)
        
        db.session.commit()
        print("Admin padrão criado:")
        print("  Email: admin@clinica.com")
        print("  Senha: admin123")
        
    except Exception as e:
        print(f"Erro ao criar admin: {str(e)}")
        db.session.rollback()

def verificar_perfis():
    """Verifica se os perfis padrão existem"""
    print("\nVerificando perfis padrão...")
    perfis_necessarios = ['admin', 'medico', 'assistente', 'paciente']
    
    for nome_perfil in perfis_necessarios:
        perfil = Perfil.query.filter_by(nome=nome_perfil).first()
        if perfil:
            print(f"  ✓ Perfil '{nome_perfil}' existe")
        else:
            print(f"  ✗ Perfil '{nome_perfil}' não encontrado")

if __name__ == '__main__':
    # Importar a aplicação para configurar o contexto
    from src.main import app
    
    with app.app_context():
        verificar_perfis()
        migrate_users()
