import json
import os
import time
import sys
# Importa o proxy fornecido para fazer as chamadas às LLMs
from interface.proxy_llm import chamar_proxy_llm

def gerar_prompt_analise(comando, saida):
    """
    Gera o prompt estruturado para que a LLM atue como perita forense.
    """
    prompt = f"""Você é um perito forense digital altamente especializado em segurança da informação, resposta a incidentes e análise de sistemas Linux/Unix.

Analise o seguinte comando executado no terminal e a respectiva saída capturada em uma auditoria forense de preservação de evasão/evidências:

=========================================
COMANDO EXECUTADO:
$ {comando}

SAÍDA DO COMANDO:
{saida}
=========================================

Você está no papel do perito e deve documentar o comando e sua respectiva saída considerando:
1. **Propósito do Comando:** Para que serve o comando e o que se pode esperar da saída do comando?
2. **Análise da Saída:** Analise a saída apresentada e destaque qualquer anomalia, comportamento suspeito ou indício de comprometimento do sistema. Senão, informe também que não há tais indícios
3. **Análise de Artefatos:** Se houver artefatos suspeitos, descreva-os e explique o que eles indicam sobre a atividade do sistema ou do usuário.
4. **Próximos Passos Recomendados:** Se houver suspeita de comprometimento, qual ação o perito deve tomar a seguir?

Responda mantendo um tom estritamente técnico, objetivo e profissional.
"""
    return prompt

def processaComandos(nome_arquivo):
    """
    Lê o arquivo JSON de evidências, monta o prompt técnico de forense,
    envia cada registro para a LLM através do proxy com pausas de 15 segundos entre eles.
    """    
    print(f"##INICIANDO ANÁLISE FORENSE (LLM) NO ARQUIVO: {nome_arquivo}")


    if not os.path.exists(nome_arquivo):
        print(f"Erro: O arquivo {nome_arquivo} não foi encontrado.")
        return

    try:
        with open(nome_arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)
        
        if not dados:
            print("O arquivo está vazio.")
            return

        total_registros = len(dados)
        for i, entry in enumerate(dados, 1):
            timestamp = entry.get('timestamp')
            cmd = entry.get('cmd')
            output = entry.get('output')
            sha256 = entry.get('hash_sha256')

            print(f"\n[PROCESSO #{i} de {total_registros}] - {timestamp}")
            print(f"COMANDO ENVIADO: $ {cmd}")
            print(f"HASH SHA-256 DO REGISTRO: {sha256}")      
    

            # Monta o prompt utilizando os dados salvos da sessão
            prompt = gerar_prompt_analise(cmd, output)

            try:
                # Dispara a chamada unificada do proxy configurado no seu config.yaml
                resposta_llm = chamar_proxy_llm(prompt)
                
                print(resposta_llm.strip())
                
            except Exception as error_llm:
                print(f"\n⚠️ Falha ao obter análise da LLM para este registro: {error_llm}\n")
            
            print("-" * 40)
            
            # Realiza a pausa de 15 segundos apenas se NÃO for o último registro da lista
            if i < total_registros:
                #print("⏸️ Aguardando 15 segundos para respeitar a taxa de requisições...")
                time.sleep(15)
            
        print(f"\nTotal de registros processados: {total_registros}")

    except Exception as e:
        print(f"Ocorreu um erro ao ler ou processar o JSON: {e}")


if __name__ == "__main__":
    # Verifica se o usuário passou o nome do arquivo como argumento
    if len(sys.argv) < 2:
        print("Uso correto: python processador_forense.py <nome_do_arquivo_de_evidencia.json>")
    else:
        arquivo_evidencia = sys.argv[1]
        processaComandos(arquivo_evidencia)