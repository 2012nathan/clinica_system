print("=== CORRIGINDO ERRO NO AUTH.PY ===")

# Ler o arquivo auth.py
with open('src/routes/auth.py', 'r') as f:
    content = f.read()

# Guardar conteúdo original
content_original = content

# Corrigir o erro tipo_perfil_perfil
content = content.replace(
    "usuario.tipo_perfil_perfil",
    "usuario.tipo_perfil"
)

# Corrigir outras possíveis duplicações
content = content.replace(
    "tipo_perfil_perfil",
    "tipo_perfil"
)

# Verificar se houve mudanças
if content != content_original:
    with open('src/routes/auth.py', 'w') as f:
        f.write(content)
    print('✅ Erro corrigido: tipo_perfil_perfil → tipo_perfil')
else:
    print('✅ Nenhum erro encontrado')

# Verificar se ainda há erros
print("\n=== VERIFICANDO ERROS RESTANTES ===")
import re

# Buscar por padrões problemáticos
patterns = [
    (r'tipo_perfil_perfil', 'Duplicação de tipo_perfil'),
    (r'usuario\.tipo(?!_perfil)', 'Uso de usuario.tipo em vez de usuario.tipo_perfil'),
    (r'user\.tipo', 'Uso de user.tipo em vez de usuario.tipo_perfil')
]

errors_found = False
for pattern, description in patterns:
    matches = re.findall(pattern, content)
    if matches:
        print(f"❌ {description}: {len(matches)} ocorrência(s)")
        errors_found = True

if not errors_found:
    print("✅ Nenhum erro encontrado no arquivo")

print("\n=== TESTANDO SINTAXE PYTHON ===")
try:
    compile(content, 'src/routes/auth.py', 'exec')
    print("✅ Sintaxe Python válida")
except SyntaxError as e:
    print(f"❌ Erro de sintaxe: {e}")
    print(f"   Linha {e.lineno}: {e.text}")

print("\n=== MOSTRANDO LINHAS CORRIGIDAS ===")
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if 'session[\'user_tipo\']' in line or 'usuario.tipo_perfil' in line:
        print(f"Linha {i}: {line.strip()}")
EOF
