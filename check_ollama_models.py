"""
Script para verificar modelos do Ollama e testar o modelo fine-tuned
"""
import ollama

print("=" * 60)
print("MODELOS DISPONÍVEIS NO OLLAMA")
print("=" * 60)

try:
    client = ollama.Client(host="http://localhost:11434")
    models = client.list()
    
    print(f"\nTotal de modelos: {len(models.models)}\n")
    
    for i, model in enumerate(models.models, 1):
        # Handle both dict and object formats
        if isinstance(model, dict):
            name = model.get('name', model.get('model', 'unknown'))
            size = model.get('size', 0)
            modified = model.get('modified_at', 'N/A')
            digest = model.get('digest', 'N/A')
        else:
            name = getattr(model, 'name', getattr(model, 'model', 'unknown'))
            size = getattr(model, 'size', 0)
            modified = getattr(model, 'modified_at', 'N/A')
            digest = getattr(model, 'digest', 'N/A')
        
        print(f"{i}. Nome: {name}")
        print(f"   Tamanho: {size / (1024**3):.2f} GB")
        print(f"   Modificado: {modified}")
        if digest != 'N/A':
            print(f"   ID: {str(digest)[:12]}...")
        print()
    
    print("=" * 60)
    print("VERIFICAÇÃO DO BAGACINHO 🍊")
    print("=" * 60)
    
    # Check if bagacinho model exists
    if any('bagacinho' in (m.get('name', '') if isinstance(m, dict) else getattr(m, 'name', '')) for m in models.models):
        print("\n✅ ÓTIMO! Modelo 'bagacinho' encontrado!")
        print("   O assistente usará automaticamente o modelo treinado.")
    else:
        print("\n⚠️  Modelo 'bagacinho' NÃO encontrado")
        print("   O assistente usará o modelo padrão (llama3.1)")
        print("\n   Para usar o modelo customizado 'bagacinho':")
        print("   1. Treine seu modelo com fine-tuning")
        print("   2. Execute: ollama create bagacinho -f Modelfile")
        print("   3. Verifique novamente com este script")
    
    print("\n" + "=" * 60)
    print("SELEÇÃO AUTOMÁTICA DE MODELO")
    print("=" * 60)
    print("\nO CP2B Maps detecta automaticamente modelos disponíveis:")
    print("• Se 'bagacinho' existe → usa o modelo treinado 🍊")
    print("• Se não existe → fallback para llama3.1 ou outro modelo")
    print("\nVocê pode trocar o modelo no dropdown da interface!")
    print()
    
except Exception as e:
    print(f"Erro ao conectar com Ollama: {e}")
    print("\nCertifique-se que o Docker Ollama está rodando:")
    print("docker ps | Select-String 'ollama'")
