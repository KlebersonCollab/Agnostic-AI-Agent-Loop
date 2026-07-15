# Stack & Ecossistema

> Mapa da stack tecnológica do projeto baseado em evidências. Gerado pelo SDD Explorer.

## Núcleo
- **Linguagem:** Python **3.14+** (`requires-python = ">=3.14"` em `pyproject.toml`; `.python-version` = `3.14`)
- **Nome do projeto:** `agnostic-agent` (versão `0.6.0`)
- **Gerenciador de build/pacotes:** `uv` (presença de `uv.lock`; `[build-system]` e `[project.scripts]` declarados em `pyproject.toml`)
  - `[build-system]`: `requires=["hatchling"]`, `build-backend="hatchling.build"`
  - `[project.scripts]`: `agnostic-agent = "cli:run_cli"`
- **Ponto de entrada:** `main.py` → `from cli import run_cli` → `run_cli()`; também instalável como comando de console `agnostic-agent`.

## Estrutura de Pacotes
O código-fonte é organizado nos seguintes pacotes Python:
- `agent/` — núcleo do agente (loop ReAct, prompts, listener base)
- `context/` — compilação dinâmica do system prompt, referências `@file/@url/@diff/@staged`, estimativa de tokens, cliente MCP
- `providers/` — abstração de provedores LLM (factory `get_provider`)
- `tools/` — ferramentas do agente (FS, math, web, multi-agente)
- `memory/` — persistência SQLite/FTS5 (`AgentMemory`)
- `hooks/` — sistema de hooks dinâmicos (11 gatilhos)
- `tui/` — interface de terminal Rich (listener, comandos, runner)
- `front/` — frontend web do grafo de memória (servidor stdlib + vis-network)

> Nota de build: o wheel (`[tool.hatch.build.targets.wheel]`) empacota `providers` e `tools`; os demais pacotes e o `.agents/` são incluídos via `include = ["/*.py", "/.agents"]`.

## Dependências de Runtime (`pyproject.toml`)
| Pacote | Restrição | Propósito |
|---------|-----------|---------|
| `anthropic` | `>=0.116.0` | Cliente da API Anthropic (Claude) |
| `google-genai` | `>=2.10.0` | Cliente da API Google Gemini / GenAI |
| `openai` | `>=2.44.0` | Cliente da API OpenAI (também usado por provedores compatíveis) |
| `pydantic` | `>=2.13.4` | Validação de dados / modelos compartilhados de mensagens e ferramentas |
| `python-dotenv` | `>=1.2.2` | Carrega variáveis do `.env` (`load_dotenv()` em `providers/base.py`) |
| `rich` | `>=15.0.0` | UI de terminal (painéis, markdown, sintaxe, spinners de status) |
| `fastmcp` | `>=3.4.4` | Cliente de alto nível para o Model Context Protocol (MCP) |

## Build do Wheel (`[tool.hatch.build.targets.wheel]`)
- `packages = ["providers", "tools"]`
- `include = ["/*.py", "/.agents"]`

## Ferramentas de Dev / Teste
- **Framework de teste:** `pytest>=9.1.1` (declarado em `[dependency-groups].dev`)
- **Runner de teste:** `uv run pytest`
- **Sem** linters/formatadores (ruff/black) ou verificadores de tipo (mypy) declarados em `pyproject.toml`.

## Comandos do Gerenciador de Pacotes (`uv`)
- `uv sync` — sincroniza e instala as dependências do projeto.
- `uv run pytest` — executa a suíte de testes.
- `uv tool install .` — instala o projeto como ferramenta de console (`agnostic-agent`).

## Integrações Externas
- Provedores LLM via abstração unificada: OpenAI, Gemini, Anthropic, OpenRouter e endpoints compatíveis com OpenAI (Ollama, Groq, DeepSeek).
- Cliente MCP via `fastmcp`: carrega e comunica-se com servidores MCP stdio externos declarados em `.agents/mcp/*.json` (drawio, playwright) — estes SÃO utilizados.

## Ambiente
- `.env` (gitignored) guarda as chaves de API; `.env.example` documenta os padrões do OpenRouter (`AGENT_PROVIDER=openrouter`, `AGENT_MODEL=anthropic/claude-3.5-sonnet`).
- As variáveis de ambiente `AGENT_PROVIDER` / `AGENT_MODEL` sobrescrevem os padrões da CLI (`cli.py`).
- `checkpoint.json` (gitignored) é escrito na raiz do projeto em handover.
