# Agnostic AI Agent Loop

Um framework de agente de IA **autônomo e agnóstico a provedores**, capaz de executar agentes que raciocinam passo a passo e utilizam ferramentas para interagir com o sistema de arquivos e realizar cálculos. Suporta múltiplos provedores de LLM (OpenAI, Gemini, Anthropic, OpenRouter, Ollama, Groq, DeepSeek etc.) através de uma única interface unificada.

> 💡 O projeto já vem configurado no `.env.example` para usar o **OpenRouter** com o modelo `anthropic/claude-3.5-sonnet`, mas qualquer provedor suportado pode ser utilizado via linha de comando ou variáveis de ambiente.

## 🎯 Visão Geral

Este projeto implementa um **loop de agente autônomo** que:

- **Raciocina passo a passo** antes de tomar ações (e explica o seu raciocínio).
- **Utiliza ferramentas** para listar/ler/escrever arquivos e calcular expressões matemáticas.
- **Suporta múltiplos provedores de LLM** por meio de uma camada de abstração unificada (`BaseLLMProvider` + factory `get_provider`).
- **É executado localmente**, com controle total sobre o ambiente de execução.
- Possui uma **interface de observação** (`AgentListener`) que desacopla a lógica do agente da apresentação (terminal, web, GUI etc.).

## 🏗️ Arquitetura

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
│  │  │   Loop      │    │  Factory    │    │(FS/Calc) │  │           │
│  │  └─────────────┘    └──────┬──────┘    └──────────┘  │           │
│  │       AgentListener (ABC)  │                          │           │
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

| Arquivo | Descrição |
|---------|-----------|
| `main.py` | Ponto de entrada; apenas invoca `run_cli()` de `cli.py` |
| `cli.py` | Parsing de argumentos de linha de comando, `ConsoleAgentListener` (saída colorida) e orquestração da sessão |
| `agent.py` | Loop principal do agente (`Agent`), interface `AgentListener` e o `SYSTEM_PROMPT` |
| `ai_provider.py` | Classe base abstrata `BaseLLMProvider` + implementações para os provedores de LLM e a factory `get_provider()` |
| `tools.py` | Definições de ferramentas (`TOOLS_METADATA`, `TOOLS_MAP`) e funções (listar, ler, escrever arquivos; calcular) |
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

# Usando uv (recomendado)
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

### Opções de Linha de Comando

| Opção | Descrição | Padrão |
|-------|-----------|--------|
| `--provider` | Provedor de LLM: `openai`, `gemini`, `anthropic`, `openrouter`, `openai_compatible` (ollama, groq, deepseek) | `gemini` (ou `AGENT_PROVIDER`) |
| `--model` | Nome do modelo | `gemini-2.5-flash` (ou `AGENT_MODEL`) |
| `--api-key` | Chave de API (opcional, recorre às variáveis de ambiente) | - |
| `--base-url` | URL base customizada para endpoints compatíveis com OpenAI | - |
| `--prompt` | Tarefa para o agente (modo interativo se omitido) | - |
| `--max-steps` | Número máximo de passos de raciocínio | `10` |

### Variáveis de Ambiente

Além das chaves de API, o arquivo `.env` (ou o ambiente) pode definir:

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `AGENT_PROVIDER` | Provedor padrão usado quando `--provider` não é informado | `gemini` |
| `AGENT_MODEL` | Modelo padrão usado quando `--model` não é informado | `gemini-2.5-flash` |
| `OPENAI_API_KEY` | Chave da OpenAI | - |
| `GEMINI_API_KEY` | Chave do Gemini | - |
| `ANTHROPIC_API_KEY` | Chave da Anthropic | - |
| `OPENROUTER_API_KEY` | Chave do OpenRouter | - |
| `OPENAI_BASE_URL` | URL base para provedores compatíveis com OpenAI | - |

## 🛠️ Provedores Suportados

A factory `get_provider()` mapeia os nomes abaixo para as respectivas implementações em `ai_provider.py`:

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

## 🧰 Ferramentas Disponíveis

O agente tem acesso a estas ferramentas (definidas em `tools.py`):

| Ferramenta | Descrição | Parâmetros |
|------------|-----------|------------|
| `list_project_files` | Lista arquivos/diretórios recursivamente (ignora `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.idea`, `.vscode`) | `path` (opcional, padrão: ".") |
| `read_file` | Lê o conteúdo de um arquivo (restrito ao diretório do projeto) | `filename` (obrigatório) |
| `write_file` | Cria/sobrescreve um arquivo com conteúdo (restrito ao diretório do projeto; cria diretórios pais) | `filename`, `content` (ambos obrigatórios) |
| `calculate` | Avalia expressões matemáticas (apenas números e operadores básicos) | `expression` (obrigatório) |

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

### Usando Modelos Locais (Ollama)
```bash
# Inicie o Ollama primeiro: ollama serve
python main.py --provider ollama --model llama3.2 --prompt "Escreva um script Python que busca dados do clima"
```

## 🔧 Adicionando Novos Provedores

1. Crie uma nova classe em `ai_provider.py` estendendo `BaseLLMProvider`.
2. Implemente o método `generate()` (recebe `messages`, `tools`, `temperature`, `max_tokens` e retorna um `ChatMessage`).
3. Adicione o provedor à factory `get_provider()`.

```python
class MeuProvedorCustom(BaseLLMProvider):
    def generate(self, messages, tools=None, temperature=0.7, max_tokens=None):
        # Sua implementação aqui
        pass

# Em get_provider():
elif provider_name == "meu_custom":
    return MeuProvedorCustom(model_name=model_name, api_key=api_key, **kwargs)
```

## 📁 Estrutura do Projeto

```
.
├── .env                 # Variáveis de ambiente (chaves de API) — não versionado
├── .env.example         # Modelo para o .env (exemplo com OpenRouter)
├── .gitignore
├── .python-version      # Versão do Python (3.14)
├── README.md            # Este arquivo
├── ai_provider.py       # Abstrações e implementações dos provedores de LLM
├── agent.py             # Loop principal do agente e interface AgentListener
├── cli.py               # CLI, parsing de argumentos e ConsoleAgentListener
├── main.py              # Ponto de entrada (chama run_cli)
├── pyproject.toml       # Configuração e dependências do projeto
├── tools.py             # Ferramentas do agente (ops. de arquivo, cálculo)
└── uv.lock              # Dependências travadas (lock)
```

## 📦 Dependências

- `anthropic>=0.116.0`
- `google-genai>=2.10.0`
- `openai>=2.44.0`
- `pydantic>=2.13.4`
- `python-dotenv>=1.2.2`

## 🔐 Notas de Segurança

- As ferramentas `read_file` e `write_file` são restritas ao diretório do projeto (não conseguem acessar arquivos externos).
- Chaves de API devem ser armazenadas em `.env` (nunca commitadas no git — veja `.gitignore`).
- A ferramenta `calculate` usa `eval()` com `__builtins__` desabilitado e uma lista restrita de caracteres — apenas números e operadores matemáticos básicos são permitidos.

## 📝 Licença

Licença MIT — sinta-se livre para usar e modificar em seus projetos.

## 🤝 Contribuindo

1. Faça um fork do repositório
2. Crie uma branch de feature
3. Faça suas alterações
4. Envie um pull request

---

**Construído com ❤️ para experimentação com agentes de IA autônomos**
