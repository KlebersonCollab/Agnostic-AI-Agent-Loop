# Agnostic AI Agent Loop

Um framework de agente de IA **autônomo e agnóstico a provedores**, capaz de executar agentes que raciocinam passo a passo e utilizam ferramentas para interagir com o sistema de arquivos, realizar cálculos e — de forma avançada — **orquestrar subagentes em paralelo**. Suporta múltiplos provedores de LLM (OpenAI, Gemini, Anthropic, OpenRouter, Ollama, Groq, DeepSeek etc.) através de uma única interface unificada.

> 💡 O projeto já vem configurado no `.env.example` para usar o **OpenRouter** com o modelo `anthropic/claude-3.5-sonnet`, mas qualquer provedor suportado pode ser utilizado via linha de comando ou variáveis de ambiente.

## 🎯 Visão Geral

Este projeto implementa um **loop de agente autônomo** que:

- **Raciocina passo a passo** antes de tomar ações (e explica o seu raciocínio).
- **Utiliza ferramentas** para listar/ler/escrever arquivos, editar por bloco, buscar conteúdo, inspecionar a estrutura de código e calcular expressões matemáticas.
- **Carrega e descarrega dinamicamente *skills* e *rules*** para compor o *system prompt* de forma otimizada (via `ContextBuilder`), mantendo a janela de contexto enxuta.
- **Orquestra subagentes em paralelo** (`spawn_subagents_parallel`) para dividir tarefas grandes em partes menores executadas simultaneamente.
- **Suporta múltiplos provedores de LLM** por meio de uma camada de abstração unificada (`BaseLLMProvider` + factory `get_provider`).
- **É executado localmente**, com controle total sobre o ambiente de execução.
- Possui uma **interface de observação** (`AgentListener`) que desacopla a lógica do agente da apresentação (terminal, web, GUI etc.).

## 🏗️ Arquitetura

O projeto é organizado em módulos, cada um com uma responsabilidade bem definida:

```
┌─────────────────────────────────────────────────────────────────────┐
│                              main.py                                 │
│                          (chama run_cli)                             │
│                                │                                      │
│                                ▼                                      │
│                              cli.py                                  │
│  ┌──────────────────────┐   ┌──────────────────────────────────┐    │
│  │ ConsoleAgentListener │   │  run_cli() — parsing de argumentos│    │
│  │ (saída colorida)     │   │  e orquestração da sessão         │    │
│  └──────────┬───────────┘   └───────────────┬──────────────────┘    │
│             │                               │                        │
│             ▼                               ▼                        │
│  ┌─────────────────────────────────────────────────────┐           │
│  │                      agent.py                        │           │
│  │  ┌─────────────┐    ┌─────────────┐    ┌──────────┐  │           │
│  │  │   Agent     │───▶│  Provider   │───▶│  Tools   │  │           │
│  │  │   Loop      │    │  Factory    │    │(FS/Calc/ │  │           │
│  │  └──────┬──────┘    └──────┬──────┘    │ Subagents)│  │           │
│  │       AgentListener (classe base)  │          └──────────┘  │           │
│  └────────────┬───────────────┼──────────────────────────┘           │
│               │                │                                      │
│               ▼                ▼                                      │
│  ┌────────────────────┐  ┌──────────────────────────────────────┐   │
│  │ context_builder.py │  │            providers/                  │   │
│  │ (skills + rules)   │  │  OpenAI │ Gemini │ Anthropic │ ...    │   │
│  │   lê .agents/      │  └──────────────────────────────────────┘   │
│  └────────────────────┘                                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Componentes Principais

| Arquivo / Pacote | Descrição |
|---------|-----------|
| `main.py` | Ponto de entrada; apenas invoca `run_cli()` de `cli.py` |
| `cli.py` | Parsing de argumentos de linha de comando (via `argparse`), `ConsoleAgentListener` (saída colorida) e orquestração da sessão |
| `agent.py` | Loop principal do agente (`Agent`), classe base `AgentListener` (métodos no-op, não uma ABC) e o `SYSTEM_PROMPT` |
| `context_builder.py` | Compilador dinâmico do *system prompt*: lê **regras** (`.agents/rules`) e **skills** (`.agents/skills`), permitindo carga/descarga em tempo de execução para otimizar a janela de contexto |
| `providers/` | Pacote de abstração dos provedores de LLM: `base.py` (classe abstrata `BaseLLMProvider` + modelos Pydantic) e implementações (`openai.py`, `gemini.py`, `anthropic.py`); a factory `get_provider()` fica em `providers/__init__.py` |
| `tools/` | Pacote de ferramentas do agente, dividido em módulos: `io_tools.py` (ops. de arquivo/código), `math_tools.py` (cálculo) e `multi_agent.py` (orquestração de subagentes). O `__init__.py` expõe `TOOLS_METADATA`, `TOOLS_MAP` e `set_active_provider` |
| `.agents/` | Diretório de **contexto dinâmico**: `skills/` (diretrizes especializadas carregáveis) e `rules/` (restrições estruturais sempre ativas) |
| `pyproject.toml` | Metadados do projeto e dependências |

## 🚀 Início Rápido

### Pré-requisitos

- Python **3.14+**
- Chave de API de pelo menos um provedor suportado

### Instalação

```bash
# Clone e instale as dependências
git clone <repo-url>
cd <diretorio-do-projeto>

# Usando uv (recomendado — gerenciador usado pelo projeto, veja uv.lock)
uv sync

# Ou usando pip
pip install -e .
```

### Configuração

Crie um arquivo `.env` com suas chaves de API (o `.env.example` já traz um modelo voltado ao OpenRouter):

```bash
# Copie o exemplo
cp .env.example .env

# Edite com suas chaves
# OPENROUTER_API_KEY=sk-or-...
# GEMINI_API_KEY=...
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=...
```

> 💡 Você também pode definir `AGENT_PROVIDER` e `AGENT_MODEL` no `.env` para usar valores padrão sem passar flags na linha de comando.

### Executando o Agente

```bash
# Uso básico (provedor/modelo padrão do código: gemini / gemini-2.5-flash)
python main.py --prompt "Liste todos os arquivos Python do projeto"

# Especificar provedor e modelo
python main.py --provider openai --model gpt-4o-mini --prompt "Crie um script hello world"

# Usar OpenRouter (conforme .env.example)
python main.py --provider openrouter --model anthropic/claude-3.5-sonnet --prompt "Explique este código"

# Usar Ollama local
python main.py --provider ollama --model llama3.2 --base-url http://localhost:11434/v1 --prompt "Explique este código"

# Modo interativo (sem --prompt)
python main.py --provider anthropic --model claude-3-5-sonnet-20241022
```

## 💻 Linha de Comando (CLI)

A interface de linha de comando é construída com a biblioteca padrão **`argparse`** (sem dependências de terceiros como Click/Typer). É um **único comando plano** — não há subcomandos nem argumentos posicionais; todas as opções são *flags* opcionais. Se `--prompt` não for informado, o programa entra em **modo interativo** e solicita a entrada via `input()`.

| Opção | Tipo | Padrão | Override por env var | Descrição |
|-------|------|--------|----------------------|-----------|
| `--provider` | `str` | `gemini` | `AGENT_PROVIDER` | Provedor de LLM: `openai`, `gemini`, `anthropic`, `openrouter`, `openai_compatible` (Ollama/Groq) |
| `--model` | `str` | `gemini-2.5-flash` | `AGENT_MODEL` | Nome do modelo (ex.: `gemini-2.5-flash`, `gpt-4o-mini`, `claude-3-5-sonnet-20241022`) |
| `--api-key` | `str` | *(nenhum)* | — | Chave de API do provedor (opcional; recorre às variáveis de ambiente) |
| `--base-url` | `str` | *(nenhum)* | — | URL base customizada para endpoints compatíveis com OpenAI (Ollama, Groq, locais) |
| `--prompt` | `str` | *(nenhum)* | — | Tarefa para o agente. Se omitido, inicia o modo interativo |
| `--max-steps` | `int` | `200` | — | Número máximo de iterações/passos do loop do agente |

> ℹ️ O loop principal do agente chama o provedor com `temperature=0.2` (fixo) e `max_steps` definido pela flag `--max-steps` (padrão `200` na CLI; o construtor de `Agent` usa `15` caso nenhum valor seja passado).

### Fluxo de Execução

1. Faz o parsing dos argumentos via `argparse`.
2. Se `--prompt` estiver vazio, imprime um banner de boas-vindas e lê o prompt interativamente do terminal via `console.input()` do Rich (trata `Ctrl+C`/`EOF` com elegância, encerrando).
3. Inicializa o provedor de IA via `get_provider(provider_name, model_name, api_key, base_url)`; em caso de falha, imprime erro e sai.
4. Registra o provedor para as ferramentas via `set_active_provider(provider)` (definido em `tools/multi_agent.py` e reexportado por `tools/__init__.py`).
5. Cria um `ConsoleAgentListener` (saída colorida no terminal) e um `Agent` com as ferramentas disponíveis e `max_steps`.
6. Executa o loop do agente com `agent.run(prompt)`.

## 💾 Checkpoint & Retomada de Sessão (Handover)

O agente possui um mecanismo de **checkpoint de handover** que evita a perda de trabalho quando a tarefa não é concluída dentro do limite de passos (`--max-steps`).

Como funciona (`agent.py` + `cli.py`):

1. No **penúltimo passo** (`step == max_steps - 1`, desde que `max_steps > 2`), o agente entra em **modo de emergência**: o sistema envia um aviso instruindo-o a **não chamar ferramentas** e a redigir um *handover checkpoint report* em Markdown (Progress Achieved, Blockers/Delays, Backlog, Next Step). Nesse passo, as ferramentas são desativadas (`tools=None`).
2. O relatório é salvo em **`checkpoint.json`** (na raiz do projeto), junto com o `exit_reason` e o histórico completo da conversa (`history`), desde que `write_checkpoint_file=True` (padrão do `Agent`).
3. Ao iniciar uma nova execução em **modo interativo** (ou seja, sem `--prompt`), se existir um `checkpoint.json`, o `cli.py` o detecta e exibe o relatório, perguntando se você deseja **retomar a tarefa** (`y/n`, padrão `y`). Ao retomar, o agente recebe o relatório de handover como contexto e continua a partir dos próximos passos imediatos. (Caso um `--prompt` seja informado, a detecção de checkpoint é ignorada e a tarefa recomeça do zero.)
4. Se a tarefa for concluída com sucesso (`exit_reason != "MAX_STEPS_REACHED"`), o `cli.py` **remove automaticamente** o `checkpoint.json`. Se você recusar a retomada, o arquivo é renomeado para `checkpoint.json.old` para evitar conflito.

> 🔒 O `checkpoint.json` contém o histórico completo da conversa e já está listado no `.gitignore` — nunca deve ser commitado.

## 🧩 Sistema de Contexto Dinâmico (Skills & Rules)

O *system prompt* do agente **não é estático**. Ele é compilado a cada passo do loop pelo `ContextBuilder` (`context_builder.py`), que combina:

1. O **prompt base** do agente (`SYSTEM_PROMPT` em `agent.py`).
2. As **regras ativas** (`.agents/rules/*.md`) — restrições estruturais sempre injetadas no prompt.
3. Os **metadados das skills disponíveis** (`.agents/skills/*/SKILL.md`) — apenas nome, descrição e palavras-chave.
4. O **corpo detalhado das skills ativas** — carregado sob demanda.

### Como funciona

- **Regras (`.agents/rules/`)** são arquivos Markdown que descrevem restrições/comportamentos obrigatórios. São **ativadas por padrão** na inicialização e sempre incluídas no prompt. Podem ser ligadas/desligadas em tempo de execução via `load_rule`/`unload_rule`.
- **Skills (`.agents/skills/<nome>/SKILL.md`)** são diretrizes especializadas (ex.: `debug`, `refactor`, `search`). Cada `SKILL.md` possui um *frontmatter* YAML com `name`, `description` e `keywords`. Apenas os **metadados** são carregados no início; o **corpo completo** só é injetado quando o agente chama a ferramenta `load_skill(name)`, e removido com `unload_skill(name)` para liberar espaço na janela de contexto.

### Ferramentas de contexto

O agente controla esse sistema através das ferramentas `load_skill` e `unload_skill` (veja a tabela de ferramentas abaixo). Quando o modelo as invoca, o `Agent` intercepta a chamada e atualiza o `ContextBuilder` em tempo real; no passo seguinte, o `system prompt` é recompilado refletindo as skills ativas.

### Skills disponíveis no projeto

| Skill | Diretório | Propósito |
|-------|-----------|-----------|
| `debug` | `.agents/skills/debug` | Analisa erros, encontra causas raízes e sugere correções |
| `refactor` | `.agents/skills/refactor` | Melhora estrutura, padrões e arquitetura de código |
| `search` | `.agents/skills/search` | Busca informações no codebase, docs ou fontes externas |
| `sdd-planner` | `.agents/skills/sdd-planner` | Planejamento de projeto, visão e roadmap (Spec Driven Development) |
| `sdd-explorer` | `.agents/skills/sdd-explorer` | Mapeia codebases existentes em artefatos técnicos consolidados |
| `sdd-executor` | `.agents/skills/sdd-executor` | Implementação cirúrgica seguindo protocolos de qualidade |
| `sdd-review` | `.agents/skills/sdd-review` | Valida implementação contra critérios de aceitação |

> 📌 Cada skill pode conter uma pasta `references/` com documentos complementares (templates, guias) que são carregados junto com o corpo da skill. **Observação:** no projeto atual, apenas as skills `sdd-*` (`sdd-planner`, `sdd-explorer`, `sdd-executor`, `sdd-review`) possuem pasta `references/`; as skills `debug`, `refactor` e `search` contêm apenas o `SKILL.md`.

## 🛠️ Provedores Suportados

A factory `get_provider()` (em `providers/__init__.py`) mapeia os nomes abaixo para as respectivas implementações no pacote `providers/`:

| Nome (`--provider`) | Implementação | Observações |
|---------------------|---------------|-------------|
| `openai` | `OpenAIProvider` | Usa `OPENAI_API_KEY` / `OPENAI_BASE_URL` |
| `gemini` | `GeminiProvider` | Usa `GEMINI_API_KEY` |
| `anthropic` | `AnthropicProvider` | Usa `ANTHROPIC_API_KEY` |
| `openrouter` | `OpenRouterProvider` | Usa `OPENROUTER_API_KEY`; `base_url` fixo em `https://openrouter.ai/api/v1` e headers `HTTP-Referer`/`X-Title` (`X-Title: "Antigravity Agent"`) |
| `openai_compatible` | `OpenAICompatibleProvider` | Endpoint genérico compatível com a API OpenAI |
| `ollama` | `OpenAICompatibleProvider` | Alias; `base_url` padrão `http://localhost:11434/v1` e `api_key` padrão `"ollama"` |
| `groq` | `OpenAICompatibleProvider` | Alias |
| `deepseek` | `OpenAICompatibleProvider` | Alias |

> 🔌 Todos os provedores compatíveis com a API OpenAI (`OpenAICompatibleProvider`) aceitam `--base-url` e `--api-key` customizados, o que permite plugar qualquer endpoint OpenAI-like (incluindo servidores locais).

### Camada de Abstração (`providers/base.py`)

Todos os provedores estendem a classe abstrata **`BaseLLMProvider`** e implementam o método `_generate(messages, tools, temperature, max_tokens)`. O método público `generate()` já provê *retry* com *backoff* exponencial (decorado com `@retry_with_backoff`) para falhas transitórias (rate limits, timeouts), relançando imediatamente erros permanentes (autenticação, chave inválida). Os modelos de dados compartilhados são: `MessageRole` (um `Enum` do tipo `str`), `ToolCall`, `ChatMessage` e `ToolDefinition` (estes três últimos modelos Pydantic).

**Particularidades por provedor:**

- **Anthropic**: exige `max_tokens` (default `4096`); o `system` é enviado como parâmetro próprio (não no array de mensagens) e as mensagens são normalizadas para alternância estrita user/assistant.
- **Gemini**: `max_tokens` mapeia para `max_output_tokens`; *tool results* são enviados como `function_response` com `role="user"`; IDs de *tool call* são sintéticos (UUID), pois a API não os fornece.
- **OpenAI / Compatíveis / OpenRouter**: seguem o formato padrão de `tool_calls` da API OpenAI.

## 🧰 Ferramentas Disponíveis

O agente tem acesso a estas ferramentas (definidas no pacote `tools/` e expostas via `tools/__init__.py`). São **10 ferramentas** no total:

| Ferramenta | Descrição | Parâmetros |
|------------|-----------|------------|
| `list_project_files` | Lista arquivos/diretórios recursivamente (ignora `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.idea`, `.vscode`) | `path` (opcional, padrão: ".") |
| `read_file` | Lê o conteúdo de um arquivo (restrito ao diretório do projeto); suporta leitura de um intervalo de linhas via `start_line`/`end_line` (1-indexed, inclusivo) | `filename` (obrigatório), `start_line` (opcional), `end_line` (opcional) |
| `write_file` | Cria/sobrescreve um arquivo com conteúdo (restrito ao diretório do projeto; cria diretórios pais; *thread-safe*) | `filename`, `content` (ambos obrigatórios) |
| `patch_file` | **Edição cirúrgica de arquivos**: substitui um bloco de texto *exato e único* por um bloco de substituição (evita reescrever o arquivo inteiro); *thread-safe*. Falha se o bloco não for encontrado ou aparecer mais de uma vez | `filename`, `target_block`, `replacement_block` (todos obrigatórios) |
| `search_grep` | **Busca em arquivos**: procura uma string ou padrão *regex* recursivamente nos arquivos do workspace (somente `.py`, `.toml`, `.md`, `.txt`, `.json`, `.yaml`, `.yml`, `.ini`, `.env`, `.example`; limitado a 100 resultados) | `query` (obrigatório), `path` (opcional, padrão: "."), `is_regex` (opcional, padrão: `False`), `case_insensitive` (opcional, padrão: `True`) |
| `get_outline` | **Estrutura de código**: faz o *parse* (via `ast`) de um arquivo Python e retorna um *outline* de imports, classes, métodos e funções — útil para entender a estrutura sem ler o arquivo inteiro | `filename` (obrigatório, deve ser `.py`) |
| `calculate` | Avalia expressões matemáticas (apenas números e operadores básicos) | `expression` (obrigatório) |
| `load_skill` | **Contexto dinâmico**: carrega as diretrizes detalhadas de uma *skill* especializada (`.agents/skills`) no *system prompt* | `name` (obrigatório) |
| `unload_skill` | **Contexto dinâmico**: descarrega uma *skill* do *system prompt* para liberar espaço na janela de contexto | `name` (obrigatório) |
| `spawn_subagents_parallel` | **Orquestração multi-agente**: dispara vários subagentes especializados em paralelo para executar tarefas concorrentemente | `tasks` (obrigatório): lista de `{"role_description", "prompt"}` |

### Como as ferramentas são registradas

Não há decorators neste código. As ferramentas são expostas ao agente através de **duas estruturas de nível de módulo** (definidas em `tools/__init__.py`) que devem permanecer sincronizadas:

1. **`TOOLS_METADATA`** — uma `List[ToolDefinition]` (modelos Pydantic de `providers/`). É o *schema* enviado ao LLM para que ele conheça o `name`, `description` e o JSON-Schema `parameters` de cada ferramenta.
2. **`TOOLS_MAP`** — um `Dict[str, Callable]` mapeando cada `name` → sua função Python real. O loop do `Agent` procura `tool_name` em `tools_map` e chama `tools_map[tool_name](**tool_args)` dinamicamente.

> ⚠️ **Nota sobre `load_skill`/`unload_skill`**: embora apareçam em `TOOLS_METADATA` (para o modelo conhecê-las), elas **não** estão em `TOOLS_MAP`. O `Agent` as intercepta internamente e delega ao `ContextBuilder` (`load_skill`/`unload_skill`), em vez de executar uma função Python direta. Se um nome de ferramenta aparece nos metadados mas não no mapa (e não é uma skill), o agente retorna `"Tool '...' is not registered/available."`.

### 🔀 Orquestração Multi-agente (`spawn_subagents_parallel`)

Esta ferramenta permite que o agente principal divida uma tarefa grande em partes menores e as delega a **subagentes especializados** que rodam em paralelo (via `ThreadPoolExecutor`). Isso mantém o contexto do agente pai limpo e focado, enquanto o trabalho pesado é feito simultaneamente.

Como funciona internamente (`tools/multi_agent.py`):

1. O agente pai chama `spawn_subagents_parallel` com uma lista de tarefas.
2. Para cada tarefa, um `Agent` filho é criado reutilizando o **mesmo provedor ativo** (`set_active_provider`, definido em `tools/multi_agent.py` e chamado em `cli.py` antes de iniciar a sessão) e um `SYSTEM_PROMPT` estendido com a `role_description`.
3. Cada subagente recebe o conjunto de ferramentas de `TOOLS_MAP` **exceto** `spawn_subagents_parallel` (que é **excluída** para evitar loops aninhados infinitos) — ou seja, `list_project_files`, `read_file`, `write_file`, `patch_file`, `search_grep`, `get_outline` e `calculate` — e executa seu próprio loop de raciocínio com `max_steps=10`.
4. A execução é acompanhada **ao vivo** no terminal: o `CollectingAgentListener` imprime, em tempo real, cada passo de raciocínio, chamada de ferramenta e saída — usando uma **cor distinta por subagente** (ciano, magenta, amarelo, azul e verde, ciclando caso haja mais de 5 subagentes) e um prefixo `[Subagent: <role>]` que identifica o papel. Ao final, um bloco de resumo de cada subagente é impresso em sequência.
5. Ao final, a ferramenta retorna um **JSON resumindo a resposta final de cada subagente**, que o agente pai pode usar para compor a resposta definitiva.

```json
[
  {
    "role": "File Reader Specialist",
    "prompt": "Leia o main.py e resuma o que ele faz",
    "result": "O main.py apenas invoca run_cli()..."
  },
  {
    "role": "Document Structuring Expert",
    "prompt": "Proponha uma estrutura para o README",
    "result": "Sugiro seções de visão geral, arquitetura..."
  }
]
```

> ⚠️ A ferramenta `spawn_subagents_parallel` é **excluída** do conjunto de ferramentas dos subagentes, impedindo recursão infinita.

## 💡 Exemplos de Uso

### Exploração de Código
```bash
python main.py --prompt "Analise a estrutura do projeto e explique a arquitetura"
```

### Operações com Arquivos
```bash
python main.py --prompt "Crie um novo arquivo 'test.py' com uma função simples de hello world"
```

### Raciocínio Multi-passos
```bash
python main.py --prompt "Leia o main.py e crie um documento de resumo em SUMMARY.md"
```

### Uso de Skills Dinâmicas
```bash
python main.py --prompt "Use a skill 'debug' para investigar o erro no teste X e proponha a correção"
```

### Orquestração de Subagentes
```bash
python main.py --prompt "Divida a leitura dos arquivos agent.py, providers/__init__.py e tools/multi_agent.py entre 3 subagentes especializados e traga um resumo unificado de cada um."
```

### Usando Modelos Locais (Ollama)
```bash
# Inicie o Ollama primeiro: ollama serve
python main.py --provider ollama --model llama3.2 --prompt "Escreva um script Python que busca dados do clima"
```

## 🔧 Adicionando Novos Provedores

1. Crie uma nova classe no pacote `providers/` estendendo `BaseLLMProvider` (definida em `providers/base.py`).
2. Implemente o método `_generate()` (recebe `messages`, `tools`, `temperature`, `max_tokens` e retorna um `ChatMessage`). O método público `generate()` já provê *retry* com *backoff*.
3. Adicione o provedor à factory `get_provider()` em `providers/__init__.py`.

```python
# Em providers/meu_provedor.py
from providers.base import BaseLLMProvider, ChatMessage

class MeuProvedorCustom(BaseLLMProvider):
    def _generate(self, messages, tools=None, temperature=0.7, max_tokens=None):
        # Sua implementação aqui
        pass

# Em providers/__init__.py -> get_provider():
elif provider_name == "meu_custom":
    return MeuProvedorCustom(model_name=model_name, api_key=api_key, **kwargs)
```

## 🔧 Adicionando Novas Ferramentas

1. Implemente a função Python no módulo apropriado (`tools/io_tools.py`, `tools/math_tools.py` etc.).
2. Adicione um `ToolDefinition` correspondente em **`TOOLS_METADATA`** (em `tools/__init__.py`) com `name`, `description` e o JSON-Schema de `parameters`.
3. Mapeie o `name` para a função em **`TOOLS_MAP`** (no mesmo arquivo).

> ⚠️ `TOOLS_METADATA` e `TOOLS_MAP` devem permanecer sincronizados: todo nome em `TOOLS_METADATA` precisa de uma entrada em `TOOLS_MAP` (exceto `load_skill`/`unload_skill`, que são tratadas especialmente pelo `Agent` via `ContextBuilder`).

## 🔧 Adicionando Novas Skills e Regras

### Skills (`.agents/skills/<nome>/SKILL.md`)

1. Crie a pasta `skills/<nome>/` e dentro dela um `SKILL.md` com *frontmatter* YAML:

```markdown
---
name: minha_skill
description: Breve descrição do que a skill faz
keywords: ["palavra1", "palavra2"]
---

# Minha Skill

Corpo detalhado das diretrizes (carregado sob demanda via load_skill).
```

2. Opcionalmente, adicione uma pasta `references/` com documentos complementares.
3. A skill aparecerá automaticamente nos metadados do prompt; o agente a carrega com `load_skill("minha_skill")`.

### Regras (`.agents/rules/<nome>.md`)

1. Crie um arquivo `<nome>.md` em `rules/`.
2. Ele será **ativado automaticamente** e injetado no prompt a cada passo. Para desativá-lo em tempo de execução, o agente pode usar `unload_rule("<nome>")`.

## 📁 Estrutura do Projeto

```
.
├── .agents/              # Contexto dinâmico (skills e rules) — NÃO versionado o conteúdo sensível
│   ├── mcp/             # Configurações de MCP (chrome-devtools, playwrite)
│   ├── rules/           # Regras/restrições (ativadas por padrão): KNOWLEDGE, NO-SHORTCUTS,
│   │                   #   QUALITY_ENFORCEMENT, RESEARCH_FIRST, TIER1_PROHIBITIONS, TOKEN_OPTIMIZATION
│   └── skills/         # Skills especializadas (debug, refactor, search, sdd-planner,
│                       #   sdd-explorer, sdd-executor, sdd-review) — cada uma com SKILL.md
│                       #   (apenas as skills sdd-* possuem pasta references/ com documentos complementares)
├── .env                 # Variáveis de ambiente (chaves de API) — NÃO versionado (ver .gitignore)
├── .env.example         # Modelo para o .env (exemplo com OpenRouter)
├── .gitignore           # Ignora build, .venv e .env
├── .python-version      # Versão do Python (3.14)
├── README.md            # Este arquivo
├── agent.py             # Loop principal do agente e classe base AgentListener (métodos no-op)
├── cli.py               # CLI, parsing de argumentos e ConsoleAgentListener
├── main.py              # Ponto de entrada (chama run_cli)
├── context_builder.py   # Compilador dinâmico do system prompt (skills + rules)
├── pyproject.toml       # Configuração e dependências do projeto
├── providers/           # Pacote de abstração dos provedores de LLM
│   ├── __init__.py      # Expõe BaseLLMProvider, ChatMessage, MessageRole, ToolCall, ToolDefinition e a factory get_provider()
│   ├── base.py          # BaseLLMProvider (ABC), ChatMessage, MessageRole, ToolCall, ToolDefinition e retry_with_backoff
│   ├── openai.py        # OpenAIProvider, OpenAICompatibleProvider (Ollama/Groq/DeepSeek) e OpenRouterProvider
│   ├── gemini.py        # GeminiProvider
│   └── anthropic.py     # AnthropicProvider
├── tools/               # Pacote de ferramentas do agente
│   ├── __init__.py      # Expõe TOOLS_METADATA, TOOLS_MAP e set_active_provider
│   ├── io_tools.py      # Operações de arquivo e código (list_project_files, read_file, write_file, patch_file, search_grep, get_outline)
│   ├── math_tools.py    # Cálculo matemático (calculate)
│   └── multi_agent.py   # Orquestração de subagentes (spawn_subagents_parallel)
├── tests/               # Testes automatizados (pytest)
└── uv.lock              # Dependências travadas (lock)
```

## 🧪 Testes

O projeto possui uma suíte de testes automatizados com **pytest** (grupo de dependências `dev`). Os testes cobrem o loop do agente, as ferramentas, o `ContextBuilder` e a factory de provedores — sem exigir chamadas reais de API (exceto o *benchmark*, que é opcional).

| Arquivo | Tipo | O que cobre |
|---------|------|-------------|
| `tests/test_agent.py` | Mock | Loop ReAct do `Agent` (pensar → chamar ferramenta → resposta final) usando um `MockProvider`; também testa o *handover* de emergência (com e sem escrita de `checkpoint.json`) |
| `tests/test_context_builder.py` | Unitário | `ContextBuilder`: cache de skills (frontmatter) e rules, `load_skill`/`unload_skill`, `build_prompt` e interceptação de ferramentas pelo agente |
| `tests/test_io_tools.py` | Unitário | `read_file`, `write_file`, `list_project_files` e a restrição de segurança (acesso negado fora do workspace) |
| `tests/test_math_tools.py` | Unitário | `calculate` (adição, parênteses, divisão, caracteres inválidos, erro de sintaxe) |
| `tests/test_new_tools.py` | Unitário | `search_grep`, `patch_file` (sucesso, alvo não encontrado, alvo duplicado) e `get_outline` |
| `tests/test_providers.py` | Mock/Init | Factory `get_provider` (validação de nome inválido e inicialização de `openai`, `openai_compatible`, `openrouter`) |
| `tests/test_benchmark_real_calls.py` | **Real** | *Benchmark* com chamadas **reais** de LLM (single-agent e multi-agent); pulado automaticamente se nenhuma `OPENROUTER_API_KEY` válida estiver configurada |

Para executar os testes (requer `uv`):

```bash
# Instala as dependências de dev (inclui pytest)
uv sync

# Roda toda a suíte (o benchmark é pulado automaticamente sem chave)
uv run pytest

# Roda um arquivo específico
uv run pytest tests/test_math_tools.py

# Roda um teste específico por nome
uv run pytest tests/test_providers.py::test_get_provider_openai_initialization

# Verboso
uv run pytest -v
```

> ⚠️ Os testes de *benchmark* (`test_benchmark_real_calls.py`) fazem chamadas reais para a API e consomem créditos. Eles são ignorados automaticamente a menos que uma `OPENROUTER_API_KEY` válida esteja presente no ambiente/`.env`. O modelo padrão usado nesses testes é `tencent/hy3:free` (via `AGENT_MODEL`), mas pode ser sobrescrito pelas variáveis de ambiente.

### Cobertura

- **Coberto:** loop do agente (ReAct + handover), ferramentas de I/O e de código, `calculate`, `ContextBuilder` (skills/rules e interceptação), e a factory de provedores (`openai`, `openai_compatible`, `openrouter`).
- **Não coberto (lacunas):** provedores `GeminiProvider` e `AnthropicProvider` (branches da factory não testados isoladamente), `cli.py`/`run_cli()`, o `CollectingAgentListener` e o fluxo de subagentes de `multi_agent.py` (exercitados apenas indiretamente pelo benchmark real), e os métodos `_generate()` reais / `retry_with_backoff`.

## 📦 Dependências

O projeto (`pyproject.toml`) declara os seguintes metadados e dependências de runtime:

| Metadado | Valor |
|----------|-------|
| **Nome** | `agnostic-agent` |
| **Versão** | `0.1.0` |
| **Descrição** | `A provider-agnostic autonomous AI agent loop with parallel multi-agent orchestration and rich terminal interface` |
| **Python** | `>=3.14` |
| **Build system** | Não declarado (gerenciado via `uv`, ver `uv.lock`) |
| **Scripts/entry-points** | Nenhum registrado em `pyproject.toml` |
| **Dev/optional deps** | Grupo `[dependency-groups].dev` com `pytest>=9.1.1` |

**Dependências de runtime** (todas com restrição de versão mínima `>=`, sem limite superior):

- `anthropic>=0.116.0` — cliente da API da Anthropic (Claude)
- `google-genai>=2.10.0` — cliente da API Google Gemini / GenAI
- `openai>=2.44.0` — cliente da API OpenAI
- `pydantic>=2.13.4` — validação de dados / modelos de configuração
- `python-dotenv>=1.2.2` — carregamento de variáveis de ambiente do `.env`
- `rich>=15.0.0` — formatação/UI de terminal (painéis, markdown, syntax highlighting) usada pela CLI e pelos subagentes

> 📌 Observação: não há seção `[build-system]` ou `[project.scripts]` no `pyproject.toml`. O projeto é gerenciado com **`uv`** (há um `uv.lock` na raiz). Para expor um comando de console, adicione um bloco `[project.scripts]` (ex.: `agnostic-agent = "cli:main"`).

## 🔐 Notas de Segurança

- As ferramentas `read_file`, `write_file` e `patch_file` são restritas ao diretório do projeto (não conseguem acessar arquivos externos). A `get_outline` também valida o caminho e exige arquivos `.py`.
- Chaves de API devem ser armazenadas em `.env`, que **já está listado no `.gitignore`** e nunca deve ser commitado. Se você já versionou um `.env`, gere novas chaves e remova o arquivo do histórico (`git rm --cached .env` + filtro de histórico).
- A ferramenta `calculate` usa `eval()` com `__builtins__` desabilitado e uma lista restrita de caracteres — apenas números e operadores matemáticos básicos são permitidos.
- A escrita/edição de arquivos (`write_file` e `patch_file`) é protegida por um *lock* de thread (`threading.Lock`), garantindo segurança em execuções paralelas de subagentes.

## 📝 Licença

Licença MIT — sinta-se livre para usar e modificar em seus projetos.

## 🤝 Contribuindo

1. Faça um fork do repositório
2. Crie uma branch de feature
3. Faça suas alterações
4. Envie um pull request

---

**Construído com ❤️ para experimentação com agentes de IA autônomos**
