# Documentação de Alterações: `terminal.py` vs. `forensicsterminal.py`

Esta documentação descreve de forma detalhada as modificações realizadas no arquivo **`terminal.py`** para dar origem ao **`forensicsterminal.py`**.  

O objetivo da alteração foi transformar o emulador de terminal demonstrativo em uma **ferramenta de coleta forense de evidências**, capaz de interceptar atalhos de teclado (`Ctrl+S`), registrar o último comando executado com sua respectiva saída sanitizada, calcular um hash de integridade (SHA-256) e salvar o snapshot em formato JSON.

## 1.0 Instalação e Execução

Antes de executar o **`forensicsterminal.py`**, é necessário garantir que as dependências do projeto e o módulo principal (`bittty`) estejam devidamente configurados no ambiente Python.

Abaixo estão descritas as diferentes formas de preparar o ambiente e rodar a aplicação:

### 1. Métodos de Instalação e Execução

#### Opção A: Instalação em Modo Editável (Recomendado)

Instala o pacote no ambiente Python atual em modo de desenvolvimento (`-e`), permitindo que alterações no código-fonte do `bittty` sejam refletidas imediatamente.

```bash
# Instala o projeto em modo editável
pip install -e .

# Executa o terminal forense
python demo/forensicsterminal.py
```

#### Opção B: Execução Direta via `PYTHONPATH`

Ideal para testes rápidos sem a necessidade de instalar o pacote no ambiente global ou virtual. O parâmetro `PYTHONPATH=src` informa ao Python onde encontrar os arquivos-fonte do projeto diretamente.

```bash
PYTHONPATH=src python demo/forensicsterminal.py
```

#### Opção C: Ambiente Virtual Isolado via `Makefile` (Automatizado)

Para manter o ambiente completamente limpo e isolado, você pode utilizar o `make` para automatizar a criação da `.venv` e a instalação das dependências.

Bash

```bash
# 1. Cria o ambiente virtual e instala as dependências/pacote em modo dev
make dev

# 2. Ativa o ambiente virtual criado
source .venv/bin/activate

# 3. Executa a demo
python demo/forensicsterminal.py
```

### Dica de Uso Forense

Assim que o terminal estiver em execução:

1. Digite comandos normalmente na sessão da *shell*.
2. Sempre que quiser registrar uma evidência do **último comando executado e sua respectiva saída**, pressione o atalho **`Ctrl + S`**.
3. O registro sanitizado com o hash SHA-256 correspondente será automaticamente gravado no arquivo `evidencia_snapshot.json`.

## 1.1 Visão Geral das Diferenças

| **Componente / Recurso**     | **terminal.py (Original)  PY**        | **forensicsterminal.py (Forense)  PY**                    |
| ---------------------------- | ------------------------------------- | --------------------------------------------------------- |
| **Módulos Adicionais**       | Apenas I/O de terminal e `asyncio`    | `datetime`, `hashlib`, `json`, `re`                       |
| **Atalhos de Teclado**       | Apenas passa dados diretamente ao PTY | Intercepta `Ctrl+S` (`\x13`) para salvar evidências       |
| **Rastreamento de Comandos** | Não armazena histórico de digitação   | Reconstrói a linha de comando do usuário no buffer        |
| **Captura de Saída (PTY)**   | Repassa direto para o parser visual   | Armazena dados brutos e remove códigos ANSI/VT100         |
| **Persistência de Dados**    | Nenhuma                               | Grava registros estruturados em `evidencia_snapshot.json` |
| **Cálculo de Integridade**   | Não possui                            | Gera hash SHA-256 (`cmd` + `output`)                      |
| **Interface / Status Bar**   | Exibe apenas dimensões e instruções   | Exibe status dinâmico de confirmação do salvamento        |



## 1.2 Detalhamento Técnico das Implementações

### 1. Inclusão de Dependências de Sistema

No `forensicsterminal.py`, foram importadas bibliotecas nativas do Python para manipulação do JSON, geração de hash e tratamento de expressões regulares:  

Python

```python
from datetime import datetime
import hashlib
import json
import re
```

### 2. Expansão do Estado da Classe (`__init__`)

A classe `StdoutFrontend` recebeu atributos adicionais para manter o estado do comando ativo e o buffer da saída recebida do PTY:  

```python
# Atributos adicionados em forensicsterminal.py
self.current_cmd_buffer = ""      # Buffer de texto enquanto o usuário digita
self.last_command = ""            # Guarda o último comando confirmado com Enter
self.last_output_raw = ""         # Guarda a saída bruta (raw) enviada pelo PTY
self.json_filename = "evidencia_snapshot.json"
self.status_msg = ""              # Mensagem temporária na barra inferior
```

### 3. Rastreamento e Intercepção de Teclas (`handle_input`)

Em `terminal.py`, a entrada de teclado era diretamente repassada para o `bittty.input()`. No `forensicsterminal.py`, a função analisa caractere por caractere antes do repasse:  

1. **Intercepção de `Ctrl+S` (`\x13`)**: Quando detectado no fluxo de dados, aciona o método `save_evidence_json()` e remove o caractere do fluxo do PTY.  
2. **Reconstrução do Comando**:
   - **`Enter` (`\r`, `\n`)**: Define `self.last_command`, limpa os buffers para preparar o próximo comando e reseta mensagens de status.  
   - **`Backspace` (`\b`, `\x7f`)**: Remove o último caractere digitado do buffer.  
   - **Caracteres imprimíveis**: Acumula os caracteres na variável `current_cmd_buffer`.  

### 4. Captura e Sanitização da Saída PTY

- **Captura (`handle_pty_data`)**: A cada novo bloco de dados retornado pelo processo PTY, o texto bruto é acumulado em `self.last_output_raw += data`.  
- **Sanitização (`clean_output`)**: Método novo criado para remover sequências de escape ANSI (como códigos de cores ou movimentação de cursor) via Regex e padronizar quebras de linha (`\r\n` $\rightarrow$ `\n`), garantindo um texto limpo para arquivamento:  

```python
def clean_output(self, raw_data: str) -> str:
    """Remove códigos de controle ANSI e ajusta quebras de linha."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    cleaned = ansi_escape.sub("", raw_data)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "")
    return cleaned.strip()
```

### 5. Geração e Persistência da Evidência (`save_evidence_json`)

Este novo método executa os seguintes passos forenses:  

1. Obtém o comando (`last_command`) e a saída tratada (`clean_output`).  
2. Registra o *timestamp* no formato `YYYY-MM-DD HH:MM:SS`.  
3. Realiza o cálculo do hash **SHA-256** concatenando a string do comando com a string da saída (`cmd + output`).  
4. Lê o arquivo JSON existente (se houver), anexa o novo registro e grava com formatação legível (`indent=4`).  
5. Atualiza `self.status_msg` para notificar visualmente o usuário na barra de status do terminal.  

### 6. Atualização Visual da Barra de Status (`render_screen`)

A barra inferior da interface foi adaptada para indicar o novo comando disponível ou fornecer feedback visual assim que uma evidência for salva:  

```python
# Trecho de render_screen() em forensicsterminal.py
if self.status_msg:
    status = f"bittty demo | {self.status_msg}"
else:
    status = f"bittty demo | {self.width}x{self.height} | [Ctrl+S] Salvar JSON | exit normally to quit"
```



## 1.3 Estrutura do Arquivo JSON Gerado (`evidencia_snapshot.json`)

Como resultado dessas modificações, cada acionamento do atalho `Ctrl+S` gera uma nova entrada no arquivo final com a seguinte estrutura:  

```json
[
    {
        "timestamp": "2026-05-16 14:54:37",
        "cmd": "ls -lh",
        "output": "total 128K\n-rw-r--r-- 1 user user  227 mai 16 14:54 evidencia_snapshot.json\n-rw-r--r-- 1 user user    0 mai 16 14:54 malware",
        "hash_sha256": "e9dfe43af7f47848cb8e4b7d4ae9399cbbc0b360dd35262b29eed98ed7069ec9"
    }
]
```