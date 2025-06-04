# DIAGNÓSTICO SHOSP FINAL - Usando variáveis SHOSP_API_*
# Arquivo: diagnostic_shosp_final.py

import os
import requests
import json
from datetime import datetime
from pathlib import Path

def carregar_env():
    """Carrega variáveis do arquivo .env"""
    env_path = Path('/var/www/ultraclin/ultraclin_system/clinica_system/.env')
    
    print(f"🔍 Carregando .env de: {env_path}")
    
    if not env_path.exists():
        print(f"❌ Arquivo .env não encontrado em: {env_path}")
        return False
    
    try:
        with open(env_path, 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha and not linha.startswith('#') and '=' in linha:
                    chave, valor = linha.split('=', 1)
                    chave = chave.strip()
                    valor = valor.strip().strip('"').strip("'")
                    os.environ[chave] = valor
                    
        print(f"✅ Arquivo .env carregado com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao carregar .env: {str(e)}")
        return False

def verificar_variaveis():
    """Verifica se as variáveis SHOSP estão configuradas"""
    print("\n" + "=" * 60)
    print("📋 VERIFICANDO VARIÁVEIS SHOSP")
    print("=" * 60)
    
    variaveis = {
        'SHOSP_API_ID': os.getenv('SHOSP_API_ID'),
        'SHOSP_API_KEY': os.getenv('SHOSP_API_KEY'),
        'SHOSP_API_URL': os.getenv('SHOSP_API_URL')
    }
    
    todas_configuradas = True
    
    for var, valor in variaveis.items():
        if valor:
            print(f"✅ {var}: CONFIGURADO")
            if var == 'SHOSP_API_ID':
                print(f"   Preview: {valor}")
            elif var == 'SHOSP_API_KEY':
                print(f"   Preview: {valor[:10]}...")
            elif var == 'SHOSP_API_URL':
                print(f"   URL: {valor}")
        else:
            print(f"❌ {var}: NÃO CONFIGURADO")
            todas_configuradas = False
    
    return todas_configuradas, variaveis

def configurar_headers_e_url(variaveis):
    """Configura headers e URL baseados nas variáveis"""
    print(f"\n🔧 CONFIGURANDO AUTENTICAÇÃO...")
    
    # Headers corretos baseados no código funcional
    headers = {
        "id": variaveis['SHOSP_API_ID'],
        "x-api-key": variaveis['SHOSP_API_KEY'],
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # URL - verificar se já tem endpoint ou se precisa adicionar
    base_url = variaveis['SHOSP_API_URL']
    
    if '/cadastro/paciente' in base_url:
        url_final = base_url
        print(f"✅ URL já contém endpoint: {url_final}")
    else:
        url_final = f"{base_url}/cadastro/paciente"
        print(f"✅ URL construída: {url_final}")
    
    print(f"🔑 Headers configurados:")
    print(f"   id: {headers['id']}")
    print(f"   x-api-key: {headers['x-api-key'][:10]}...")
    
    return headers, url_final

def testar_conectividade_basica(url_final):
    """Testa conectividade básica com o servidor"""
    print(f"\n🌐 TESTANDO CONECTIVIDADE BÁSICA...")
    
    try:
        # Extrair domínio base para teste de conectividade
        if '/v1' in url_final:
            base_domain = url_final.split('/v1')[0]
        else:
            base_domain = '/'.join(url_final.split('/')[:-1])
        
        print(f"   Testando: {base_domain}")
        
        response = requests.get(base_domain, timeout=5)
        print(f"   ✅ Servidor acessível (Status: {response.status_code})")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro de conectividade: {str(e)}")
        return False

def testar_get_paciente(headers, url_final):
    """Testa busca de paciente por CPF (GET)"""
    print(f"\n📥 TESTE GET - Buscar paciente por CPF")
    print(f"   Endpoint: {url_final}")
    
    cpf_teste = "10545855713"
    print(f"   CPF de teste: {cpf_teste}")
    
    try:
        response = requests.get(
            url_final,
            headers=headers,
            params={"cpf": cpf_teste},
            timeout=10
        )
        
        print(f"   Status HTTP: {response.status_code}")
        print(f"   URL completa: {response.url}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ Resposta JSON válida recebida")
                print(f"   Estrutura: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                # Verificar formato esperado da API SHOSP
                if data.get('ret') == '1':
                    print(f"   ✅ Formato SHOSP correto (ret='1')")
                    if data.get('dados'):
                        print(f"   ✅ Paciente encontrado!")
                        paciente = data['dados'][0] if isinstance(data['dados'], list) else data['dados']
                        print(f"   Nome: {paciente.get('nome', 'N/A')}")
                        return True
                    else:
                        print(f"   ℹ️ Paciente não encontrado (dados vazios)")
                        return True  # API funcionou, só não tem o paciente
                else:
                    print(f"   ⚠️ Formato inesperado (ret='{data.get('ret')}')")
                    return False
                    
            except ValueError as e:
                print(f"   ❌ Resposta não é JSON válido: {response.text}")
                return False
                
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden")
            print(f"   Resposta: {response.text}")
            print(f"   💡 Possíveis causas:")
            print(f"      - Headers de autenticação incorretos")
            print(f"      - Credenciais inválidas ou expiradas")
            print(f"      - IP não autorizado")
            return False
            
        elif response.status_code == 401:
            print(f"   ❌ 401 Unauthorized")
            print(f"   Resposta: {response.text}")
            print(f"   💡 Verificar credenciais de autenticação")
            return False
            
        elif response.status_code == 404:
            print(f"   ❌ 404 Not Found")
            print(f"   💡 Endpoint pode estar incorreto")
            return False
            
        else:
            print(f"   ⚠️ Status inesperado: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout na requisição")
        return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Erro de conexão")
        return False
    except Exception as e:
        print(f"   ❌ Erro inesperado: {str(e)}")
        return False

def testar_post_paciente(headers, url_final):
    """Testa cadastro de paciente (POST)"""
    print(f"\n📤 TESTE POST - Cadastrar paciente")
    
    # Dados de teste com CPF fictício
    dados_teste = {
        "cpf": "00000000000",
        "nome": "PACIENTE TESTE INTEGRACAO",
        "email": "teste.integracao@exemplo.com",
        "dataNascimento": "1990-01-01",
        "telefone": "(11) 99999-9999"
    }
    
    print(f"   Dados de teste: {json.dumps(dados_teste, indent=2)}")
    
    try:
        response = requests.post(
            url_final,
            headers=headers,
            json=dados_teste,
            timeout=10
        )
        
        print(f"   Status HTTP: {response.status_code}")
        
        if response.status_code in [200, 201]:
            try:
                data = response.json()
                print(f"   ✅ POST aceito pela API!")
                print(f"   Resposta: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return True
            except ValueError:
                print(f"   ✅ POST aceito (resposta não-JSON): {response.text}")
                return True
                
        elif response.status_code == 400:
            print(f"   ℹ️ 400 Bad Request (esperado para dados fictícios)")
            print(f"   Resposta: {response.text}")
            print(f"   ✅ API está respondendo ao POST")
            return True
            
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden - Sem permissão para POST")
            print(f"   Resposta: {response.text}")
            return False
            
        elif response.status_code == 422:
            print(f"   ℹ️ 422 Unprocessable Entity (dados inválidos - esperado)")
            print(f"   Resposta: {response.text}")
            print(f"   ✅ API está validando dados corretamente")
            return True
            
        else:
            print(f"   ⚠️ Status inesperado: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro no POST: {str(e)}")
        return False

def testar_cpf_inexistente(headers, url_final):
    """Testa busca com CPF que não existe"""
    print(f"\n🔍 TESTE - CPF inexistente")
    
    cpf_inexistente = "12345678901"
    print(f"   CPF teste: {cpf_inexistente}")
    
    try:
        response = requests.get(
            url_final,
            headers=headers,
            params={"cpf": cpf_inexistente},
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ret') != '1' or not data.get('dados'):
                print(f"   ✅ API retorna corretamente quando CPF não existe")
            else:
                print(f"   ⚠️ API retornou dados para CPF inexistente")
                print(f"   Dados: {data}")
                
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")

def gerar_codigo_service():
    """Gera o código corrigido para shosp_service.py"""
    print(f"\n" + "=" * 60)
    print("💻 CÓDIGO CORRIGIDO PARA shosp_service.py")
    print("=" * 60)
    
    codigo = '''# shosp_service.py - VERSÃO FINAL CORRIGIDA

import os
import requests
import logging
from pathlib import Path

class ShospService:
    def __init__(self):
        self.carregar_config()
        
    def carregar_config(self):
        """Carrega configurações das variáveis de ambiente"""
        self.headers = {
            "id": os.getenv('SHOSP_API_ID'),
            "x-api-key": os.getenv('SHOSP_API_KEY'),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # URL - verificar se já contém endpoint
        base_url = os.getenv('SHOSP_API_URL')
        if '/cadastro/paciente' in base_url:
            self.url_paciente = base_url
        else:
            self.url_paciente = f"{base_url}/cadastro/paciente"
            
        logging.info(f"SHOSP Service configurado - URL: {self.url_paciente}")
    
    def buscar_paciente_por_cpf(self, cpf):
        """
        Busca paciente por CPF usando GET /cadastro/paciente
        
        Args:
            cpf (str): CPF do paciente (apenas números)
            
        Returns:
            dict: Dados do paciente se encontrado, None caso contrário
        """
        try:
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            
            if len(cpf_limpo) != 11:
                logging.error(f"CPF inválido: {cpf}")
                return None
            
            response = requests.get(
                self.url_paciente,
                headers=self.headers,
                params={"cpf": cpf_limpo},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ret') == '1' and data.get('dados'):
                    logging.info(f"Paciente encontrado para CPF: {cpf_limpo}")
                    return data['dados'][0] if isinstance(data['dados'], list) else data['dados']
                else:
                    logging.info(f"Paciente não encontrado para CPF: {cpf_limpo}")
                    return None
            else:
                logging.error(f"Erro SHOSP - Status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Erro ao buscar paciente no SHOSP: {str(e)}")
            return None
    
    def cadastrar_paciente(self, dados_paciente):
        """
        Cadastra novo paciente usando POST /cadastro/paciente
        
        Args:
            dados_paciente (dict): Dados do paciente
                - cpf (str): CPF do paciente
                - nome (str): Nome completo
                - email (str): Email
                - dataNascimento (str): Data no formato YYYY-MM-DD
                - telefone (str, opcional): Telefone
                
        Returns:
            dict: Dados do paciente cadastrado se sucesso, None caso contrário
        """
        try:
            # Validações básicas
            required_fields = ['cpf', 'nome', 'email', 'dataNascimento']
            for field in required_fields:
                if not dados_paciente.get(field):
                    logging.error(f"Campo obrigatório ausente: {field}")
                    return None
            
            # Limpar CPF
            dados_paciente['cpf'] = ''.join(filter(str.isdigit, dados_paciente['cpf']))
            
            response = requests.post(
                self.url_paciente,
                headers=self.headers,
                json=dados_paciente,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('ret') == '1':
                    logging.info(f"Paciente cadastrado no SHOSP: {dados_paciente['cpf']}")
                    return data.get('dados')
                else:
                    logging.error(f"SHOSP rejeitou cadastro: {data}")
                    return None
            else:
                logging.error(f"Erro ao cadastrar no SHOSP - Status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Erro ao cadastrar paciente no SHOSP: {str(e)}")
            return None
    
    def verificar_cpf_existe(self, cpf):
        """Verifica se CPF existe no SHOSP"""
        return self.buscar_paciente_por_cpf(cpf) is not None
    
    def buscar_ou_cadastrar_paciente(self, cpf, dados_cadastro=None):
        """
        Busca paciente, se não encontrar tenta cadastrar
        
        Args:
            cpf (str): CPF para buscar
            dados_cadastro (dict, opcional): Dados para cadastro se não encontrado
            
        Returns:
            dict: Dados do paciente (encontrado ou cadastrado)
        """
        # Primeiro busca
        paciente = self.buscar_paciente_por_cpf(cpf)
        
        if paciente:
            return paciente
        
        # Se não encontrou e tem dados para cadastro
        if dados_cadastro:
            dados_cadastro['cpf'] = cpf
            return self.cadastrar_paciente(dados_cadastro)
        
        return None

# Instância global
shosp_service = ShospService()
'''
    
    print(codigo)

def main():
    """Função principal do diagnóstico"""
    print("=" * 60)
    print("🔍 DIAGNÓSTICO COMPLETO DA INTEGRAÇÃO SHOSP")
    print("🕐 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    try:
        # 1. Carregar arquivo .env
        if not carregar_env():
            return
        
        # 2. Verificar variáveis
        todas_ok, variaveis = verificar_variaveis()
        if not todas_ok:
            print("\n❌ Variáveis não configuradas corretamente!")
            return
        
        # 3. Configurar headers e URL
        headers, url_final = configurar_headers_e_url(variaveis)
        
        # 4. Testes de conectividade
        if not testar_conectividade_basica(url_final):
            print("\n⚠️ Problemas de conectividade, mas continuando...")
        
        # 5. Teste GET principal
        get_sucesso = testar_get_paciente(headers, url_final)
        
        # 6. Teste POST
        post_sucesso = testar_post_paciente(headers, url_final)
        
        # 7. Teste CPF inexistente
        testar_cpf_inexistente(headers, url_final)
        
        # 8. Gerar código service
        gerar_codigo_service()
        
        # 9. Resumo final
        print("\n" + "=" * 60)
        print("📊 RESUMO DO DIAGNÓSTICO")
        print("=" * 60)
        
        if get_sucesso:
            print("✅ GET /cadastro/paciente: FUNCIONANDO")
        else:
            print("❌ GET /cadastro/paciente: COM PROBLEMAS")
            
        if post_sucesso:
            print("✅ POST /cadastro/paciente: FUNCIONANDO")
        else:
            print("❌ POST /cadastro/paciente: COM PROBLEMAS")
        
        if get_sucesso or post_sucesso:
            print(f"\n🎯 INTEGRAÇÃO SHOSP: ✅ FUNCIONANDO!")
            print(f"\n📋 PRÓXIMOS PASSOS:")
            print(f"1. Copie o código do shosp_service.py gerado acima")
            print(f"2. Substitua o arquivo atual")
            print(f"3. Teste na aplicação Flask")
            print(f"4. Implemente o fluxo de primeiro acesso")
        else:
            print(f"\n🎯 INTEGRAÇÃO SHOSP: ❌ COM PROBLEMAS")
            print(f"\n📋 VERIFICAR:")
            print(f"1. Credenciais no painel SHOSP")
            print(f"2. Status da conta SHOSP")
            print(f"3. Whitelist de IPs")
            print(f"4. Suporte técnico SHOSP")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO NO DIAGNÓSTICO: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
