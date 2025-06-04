#!/usr/bin/env python3
from src.services.unified_email_service import email_service, EMAIL_SERVICE_AVAILABLE

if EMAIL_SERVICE_AVAILABLE:
    print(f"✅ Serviço disponível: {email_service.provider.value}")
    
    # Teste básico
    resultado = email_service.enviar_email(
        "ultraclin.exames@gmail.com",  # Seu próprio email para teste
        "🏥 UltraClin - Teste Gmail API",
        """
        <div style="font-family: Arial; max-width: 600px; margin: 0 auto;">
            <div style="background: #ff6600; color: white; padding: 20px; text-align: center;">
                <h1>🏥 UltraClin</h1>
                <p>Sistema de Email Funcionando!</p>
            </div>
            <div style="padding: 20px; background: #f9f9f9;">
                <h2>✅ Gmail API Configurada!</h2>
                <p>Parabéns! O sistema de email está funcionando perfeitamente.</p>
                <ul>
                    <li>✅ Gmail API configurada</li>
                    <li>✅ OAuth funcionando</li>
                    <li>✅ Token válido</li>
                    <li>✅ Envio de emails operacional</li>
                </ul>
            </div>
        </div>
        """,
        "UltraClin - Gmail API funcionando! Sistema de email configurado com sucesso."
    )
    
    print(f"📧 Resultado do envio: {resultado}")
    
    if resultado['sucesso']:
        print("🎉 EMAIL ENVIADO COM SUCESSO!")
        print("Verifique sua caixa de entrada!")
    else:
        print(f"❌ Erro no envio: {resultado['erro']}")
else:
    print("❌ Serviço de email não disponível")
