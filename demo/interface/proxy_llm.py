import yaml
from google import genai
from openai import OpenAI
from groq import Groq
from mistralai.client import Mistral
from cerebras.cloud.sdk import Cerebras

import os
import yaml

def carregar_configuracao(nome_arquivo="config.yaml"):
    """Carrega as configurações e chaves do arquivo YAML usando caminho absoluto."""
    # 1. Descobre a pasta onde este script está salvo
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Cria o caminho absoluto ANTES do try para garantir que a variável exista
    caminho_absoluto = os.path.join(diretorio_atual, nome_arquivo)
    
    try:
        # 3. Abre o arquivo usando o caminho absoluto garantido
        with open(caminho_absoluto, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
            
    except Exception as e:
        # Agora 'caminho_absoluto' está visível aqui e vai te mostrar o caminho real do erro
        raise RuntimeError(f"Erro ao carregar o arquivo {caminho_absoluto}: {e}")

def chamar_proxy_llm(mensagem: str) -> str:
    """
    Proxy que direciona a mensagem para a API configurada no config.yaml
    e retorna apenas o texto da resposta.
    """
    config = carregar_configuracao()
    provedor = config.get("provedor_ativo", "").lower()
    chaves = config.get("chaves_api", {})
    
    api_key = chaves.get(provedor)
    if not api_key or "<minha" in api_key:
        raise ValueError(f"Chave de API para o provedor '{provedor}' não foi configurada corretamente no YAML.")

    # --- ROTEAMENTO DE APIS ---
    
    if provedor == "gemini":
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=mensagem,
        )
        return response.text

    elif provedor == "openai":
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{"role": "user", "content": mensagem}]
        )
        return response.choices[0].message.content

    elif provedor == "github":
        client = OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=api_key
        )
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{"role": "user", "content": mensagem}]
        )
        return response.choices[0].message.content

    elif provedor == "groq":
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": mensagem}],
        )
        return response.choices[0].message.content

    elif provedor == "mistral":
        client = Mistral(api_key=api_key)
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": mensagem}]
        )
        return response.choices[0].message.content

    elif provedor == "cerebras":
        client = Cerebras(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-oss-120b", 
            messages=[{"role": "user", "content": mensagem}],
        )
        return response.choices[0].message.content

    else:
        raise ValueError(f"Provedor '{provedor}' é inválido ou não possui implementação no proxy.")

# --- TESTE DO PROXY ---
if __name__ == "__main__":
    prompt_teste = "Olá! Escreva uma frase curta de boas-vindas para testar o Proxy."
    
    try:
        print("Iniciando chamada via Proxy...")
        resposta = chamar_proxy_llm(prompt_teste)
        
        print("\n--- Resposta Unificada do Proxy ---")
        print(resposta)
        print("-----------------------------------")
        
    except Exception as e:
        print(f"Erro na execução do proxy: {e}")