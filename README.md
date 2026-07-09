# Agnostic AI Agent Loop

Um framework de agente de IA **autônomo e agnóstico a provedores**, capaz de executar agentes que raciocinam passo a passo e utilizam ferramentas para interagir com o sistema de arquivos, realizar cálculos e — de forma avançada — **orquestrar subagentes em paralelo**. Suporta múltiplos provedores de LLM (OpenAI, Gemini, Anthropic, OpenRouter, Ollama, Groq, DeepSeek etc.) através de uma única interface unificada.

> 💡 O projeto já vem configurado no `.env.example` para usar o **OpenRouter** com o modelo `anthropic/claude-3.5-sonnet`, mas qualquer provedor suportado pode ser utilizado via linha de comando ou variáveis de ambiente.

## 🎯 Visão Geral

Este projeto implementa um **loop de agente autônomo** que:

- **Raciocina passo a passo** antes de tomar ações (e explica o seu raciocínio).
- **Utiliza ferramentas** para listar/ler/escrever arquivos e calcular expressões matemáticas.
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
│  │  └─────────────┘    └──────┬──────┘    │ Subagents)│  │           │
│  │       AgentListener (ABC)  │          └──────────┘  │           │
│  └────────────────────────────┼──────────────────────────┘           │
│                                │                                      │
│              ┌─────────────────┼──────────────────┐                  │
│              ▼                 ▼                  ▼                  │
│         ┌─────────┐      ┌───────────┐       ┌──────────┐           │
│         │ OpenAI  │      │  Gemini   │       │Anthropic │  ...       │
│         └─────────┘      └───────────┘       └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

### Componentes Principais

| Arquivo / Pacote | Descrição |
|---------|-----------|
| `main.py` | Ponto de entrada; apenas invoca `run_cli()` de `cli.py` |
| `cli.py` | Parsing de argumentos de linha de comando (via `argparse`), `ConsoleAgentListener` (saída colorida) e orquestração da sessão |
| `agent.py` | Loop principal do agente (`Agent`), interface `AgentListener` e o `SYSTEM_PROMPT` |
| `providers/` | Pacote de abstração dos provedores de LLM: `base.py` (classe abstrata `BaseLLMProvider` + modelos Pydantic) e implementações (`openai.py`, `gemini.py`, `anthropic.py`); a factory `get_provider()` fica em `providers/__init__.py` |
| `tools/` | Pacote de ferramentas do agente, dividido em módulos: `io_tools.py` (ops. de arquivo), `math_tools.py` (cálculo) e `multi_agent.py` (orquestração de subagentes). O `__init__.py` expõe `TOOLS_METADATA`, `TOOLS_MAP` e `set_active_provider` |
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
| `--max-steps` | `int` | `75` | — | Número máximo de iterações/passos do loop do agente |

> ℹ️ O loop principal do agente chama o provedor com `temperature=0.2` (fixo) e `max_steps` definido pela flag `--max-steps` (padrão `75` na CLI; o construtor de `Agent` usa `15` caso nenhum valor seja passado).

### Fluxo de Execução

1. Faz o parsing dos argumentos via `argparse`.
2. Se `--prompt` estiver vazio, imprime um banner de boas-vindas e lê o prompt interativamente do stdin (trata `Ctrl+C`/`EOF` com elegância, encerrando).
3. Inicializa o provedor de IA via `get_provider(provider_name, model_name, api_key, base_url)`; em caso de falha, imprime erro e sai.
4. Registra o provedor para as ferramentas via `set_active_provider(provider)` (definido em `tools/multi_agent.py` e reexportado por `tools/__init__.py`).
5. Cria um `ConsoleAgentListener` (saída colorida no terminal) e um `Agent` com as ferramentas disponíveis e `max_steps`.
6. Executa o loop do agente com `agent.run(prompt)`.

## 🛠️ Provedores Suportados

A factory `get_provider()` (em `providers/__init__.py`) mapeia os nomes abaixo para as respectivas implementações no pacote `providers/`:

| Nome (`--provider`) | Implementação | Observações |
|---------------------|---------------|-------------|
| `openai` | `OpenAIProvider` | Usa `OPENAI_API_KEY` / `OPENAI_BASE_URL` |
| `gemini` | `GeminiProvider` | Usa `GEMINI_API_KEY` |
| `anthropic` | `AnthropicProvider` | Usa `ANTHROPIC_API_KEY` |
| `openrouter` | `OpenRouterProvider` | Usa `OPENROUTER_API_KEY`; `base_url` fixo em `https://openrouter.ai/api/v1` |
| `openai_compatible` | `OpenAICompatibleProvider` | Endpoint genérico compatível com a API OpenAI |
| `ollama` | `OpenAICompatibleProvider` | Alias; `base_url` padrão `http://localhost:11434/v1` |
| `groq` | `OpenAICompatibleProvider` | Alias |
| `deepseek` | `OpenAICompatibleProvider` | Alias |

> 🔌 Todos os provedores compatíveis com a API OpenAI (`OpenAICompatibleProvider`) aceitam `--base-url` e `--api-key` customizados, o que permite plugar qualquer endpoint OpenAI-like (incluindo servidores locais).

## 🧰 Ferramentas Disponíveis

O agente tem acesso a estas ferramentas (definidas no pacote `tools/` e expostas via `tools/__init__.py`):

| Ferramenta | Descrição | Parâmetros |
|------------|-----------|------------|
| `list_project_files` | Lista arquivos/diretórios recursivamente (ignora `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.idea`, `.vscode`) | `path` (opcional, padrão: ".") |
| `read_file` | Lê o conteúdo de um arquivo (restrito ao diretório do projeto); suporta leitura de um intervalo de linhas via `start_line`/`end_line` (1-indexed, inclusivo) | `filename` (obrigatório), `start_line` (opcional), `end_line` (opcional) |
| `write_file` | Cria/sobrescreve um arquivo com conteúdo (restrito ao diretório do projeto; cria diretórios pais; *thread-safe*) | `filename`, `content` (ambos obrigatórios) |
| `calculate` | Avalia expressões matemáticas (apenas números e operadores básicos) | `expression` (obrigatório) |
| `spawn_subagents_parallel` | **Orquestração multi-agente**: dispara vários subagentes especializados em paralelo para executar tarefas concorrentemente | `tasks` (obrigatório): lista de `{"role_description", "prompt"}` |

### Como as ferramentas são registradas

Não há decorators neste código. As ferramentas são expostas ao agente através de **duas estruturas de nível de módulo** (definidas em `tools/__init__.py`) que devem permanecer sincronizadas:

1. **`TOOLS_METADATA`** — uma `List[ToolDefinition]` (modelos Pydantic de `providers/`). É o *schema* enviado ao LLM para que ele conheça o `name`, `description` e o JSON-Schema `parameters` de cada ferramenta.
2. **`TOOLS_MAP`** — um `Dict[str, Callable]` mapeando cada `name` → sua função Python real. O loop do `Agent` procura `tool_name` em `tools_map` e chama `tools_map[tool_name](**tool_args)` dinamicamente.

Se um nome de ferramenta aparece nos metadados mas não no mapa, o agente retorna `"Tool '...' is not registered/available."`.

### 🔀 Orquestração Multi-agente (`spawn_subagents_parallel`)

Esta ferramenta permite que o agente principal divida uma tarefa grande em partes menores e as delega a **subagentes especializados** que rodam em paralelo (via `ThreadPoolExecutor`). Isso mantém o contexto do agente pai limpo e focado, enquanto o trabalho pesado é feito simultaneamente.

Como funciona internamente (`tools/multi_agent.py`):

1. O agente pai chama `spawn_subagents_parallel` com uma lista de tarefas.
2. Para cada tarefa, um `Agent` filho é criado reutilizando o **mesmo provedor ativo** (`set_active_provider`, definido em `tools/multi_agent.py` e chamado em `cli.py` antes de iniciar a sessão) e um `SYSTEM_PROMPT` estendido com a `role_description`.
3. Cada subagente recebe um subconjunto de ferramentas (todas, exceto `spawn_subagents_parallel`, evitando loops aninhados infinitos) e executa seu próprio loop de raciocínio com `max_steps=10`.
4. A execução é acompanhada **ao vivo** no terminal: o `CollectingAgentListener` imprime, em tempo real, cada passo de raciocínio, chamada de ferramenta e saída — usando uma **cor distinta por subagente** (ciano, magenta, amarelo, azul, verde, em ciclo) e um prefixo `[Subagent: <role>]` que identifica o papel. Ao final, um bloco de resumo de cada subagente é impresso em sequência.
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

## 📁 Estrutura do Projeto

```
.
├── .env                 # Variáveis de ambiente (chaves de API) — NÃO versionado (ver .gitignore)
├── .env.example         # Modelo para o .env (exemplo com OpenRouter)
├── .gitignore           # Ignora build, .venv e .env
├── .python-version      # Versão do Python (3.14)
├── README.md            # Este arquivo
├── agent.py             # Loop principal do agente e interface AgentListener
├── cli.py               # CLI, parsing de argumentos e ConsoleAgentListener
├── main.py              # Ponto de entrada (chama run_cli)
├── pyproject.toml       # Configuração e dependências do projeto
├── providers/           # Pacote de abstração dos provedores de LLM
│   ├── __init__.py      # Expõe BaseLLMProvider, ChatMessage, MessageRole, ToolDefinition e a factory get_provider()
│   ├── base.py          # BaseLLMProvider (ABC), ChatMessage, MessageRole, ToolCall, ToolDefinition e retry_with_backoff
│   ├── openai.py        # OpenAIProvider, OpenAICompatibleProvider (Ollama/Groq/DeepSeek) e OpenRouterProvider
│   ├── gemini.py        # GeminiProvider
│   └── anthropic.py     # AnthropicProvider
├── tools/               # Pacote de ferramentas do agente
│   ├── __init__.py      # Expõe TOOLS_METADATA, TOOLS_MAP e set_active_provider
│   ├── io_tools.py      # Operações de arquivo (list_project_files, read_file, write_file)
│   ├── math_tools.py    # Cálculo matemático (calculate)
│   └── multi_agent.py   # Orquestração de subagentes (spawn_subagents_parallel)
├── tests/               # Testes automatizados (pytest)
└── uv.lock              # Dependências travadas (lock)
```

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

- As ferramentas `read_file` e `write_file` são restritas ao diretório do projeto (não conseguem acessar arquivos externos).
- Chaves de API devem ser armazenadas em `.env`, que **já está listado no `.gitignore`** e nunca deve ser commitado. Se você já versionou um `.env`, gere novas chaves e remova o arquivo do histórico (`git rm --cached .env` + filtro de histórico).
- A ferramenta `calculate` usa `eval()` com `__builtins__` desabilitado e uma lista restrita de caracteres — apenas números e operadores matemáticos básicos são permitidos.
- A escrita de arquivos (`write_file`) é protegida por um *lock* de thread (`threading.Lock`), garantindo segurança em execuções paralelas de subagentes.

## 📝 Licença

Licença MIT — sinta-se livre para usar e modificar em seus projetos.

## 🤝 Contribuindo

1. Faque um fork do repositório
2. Crie uma branch de feature
3. Faça suas alterações
4. Envie um pull request

---

**Construído com ❤️ para experimentação com agentes de IA autônomos**
