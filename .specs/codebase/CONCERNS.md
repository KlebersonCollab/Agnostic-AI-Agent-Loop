# Riscos Críticos e Preocupações

> Seção mais importante para o protocolo Safety Valve. Cada preocupação cita evidência de arquivo. Gerado pelo SDD Explorer.

## Débito Técnico
1. **~~Sincronização manual de duplo registro~~ — RESOLVIDO** — `tools/__init__.py` antes exigia editar manualmente `TOOLS_METADATA` e `TOOLS_MAP`. Agora define uma única lista `REGISTERED_TOOLS` de tuplas `(ToolDefinition, handler)`; `TOOLS_METADATA` e `TOOLS_MAP` são derivados dela, e a validação em tempo de importação levanta `ImportError` em caso de nomes duplicados ou handlers não chamáveis. *Risco: eliminado para adição de ferramentas.*
2. **`AgentListener` é uma classe comum, não um ABC** — `agent/listener.py`. Subclasses podem esquecer sobrescritas obrigatórias; não há imposição. Documentado como intencional (README), mas ainda é um risco latente de contrato.
3. **~~Sem `[build-system]` / `[project.scripts]`~~ — RESOLVIDO** — `pyproject.toml` POSSUI `[build-system]` com `requires=["hatchling"]` e `[project.scripts]` com `agnostic-agent = "cli:run_cli"`. O projeto agora é pip-installável como comando de console. *Risco: eliminado.*
4. **~~Configs MCP não utilizadas~~ — RESOLVIDO** — `.agents/mcp/drawio.json` e `.agents/mcp/playwrite.json` SÃO carregados e usados pelo `MCPManager` (`context/mcp.py`) em tempo de execução via `load_mcp`. (Observação: o arquivo chama-se `playwrite.json`, mas o nome do servidor interno é `playwright` — inconsistência menor de nomenclatura, não config morta.)

## Áreas Frágeis / Lacunas de Teste
1. **`GeminiProvider` & `AnthropicProvider` não testados em isolamento** — `tests/test_providers.py` cobre apenas os ramos `openai`, `openai_compatible`, `openrouter` de `get_provider`. A lógica `_generate()` para Gemini/Anthropic (normalização de mensagens, síntese de tool-call) não tem cobertura unitária. *Evidência: README seção "Não coberto"; `tests/test_providers.py`.*
2. **`cli.py` / `run_cli()` parcialmente coberto** — argument parsing, detecção/resumo de checkpoint e bootstrap do provider ainda são exercitados apenas manualmente ou via benchmark real; porém o comportamento `/loop` agora é coberto por `tests/test_cli_loop.py`. *Evidência: README gaps de cobertura; `tests/test_cli_loop.py`.*
3. **Fluxo de `multi_agent.py` parcialmente coberto** — `spawn_subagents_parallel`, `CollectingAgentListener` e o loop de subagentes ainda rodam apenas via `test_benchmark_real_calls.py` (API real, auto-skip); porém o fluxo async agora é coberto por `tests/test_async_delegation.py` e o toolset do orquestrador por `tests/test_agent_orchestrator.py`. *Evidência: README gaps de cobertura; `tests/test_async_delegation.py`, `tests/test_agent_orchestrator.py`.*
4. **`retry_with_backoff` não testado** — a classificação permanente-vs-transiente e o timing de backoff em `providers/base.py` não têm teste direto. *Risco: comportamento de retry pode regredir silenciosamente.*
5. **Parser de frontmatter do `ContextBuilder` é hand-rolled** — `context/builder.py:_parse_frontmatter` faz splitting ingênuo por linha; YAML aninhado ou valores com aspas contendo `:` podem ser mal interpretados. Nenhuma biblioteca YAML é usada. *Risco: médio para metadados complexos de skill.*

### Cobertos recentemente (notar como cobertos)
- **Sistema de hooks** — coberto por `tests/test_hooks.py` (11 triggers).
- **Grafo de memória JSONL** — coberto por `tests/test_memory_graph.py`.
- **Execução concorrente de ferramentas** — coberta por `tests/test_concurrent_tool_execution.py`.
- **Context builder / references / breakdown** — cobertos por `tests/test_context_builder.py`, `tests/test_context_references.py`, `tests/test_context_breakdown.py`.
- **Delegação async** — coberta por `tests/test_async_delegation.py`.
- **Orquestrador** — coberto por `tests/test_agent_orchestrator.py`.
- **Loop do CLI** — coberto por `tests/test_cli_loop.py`.

## Segurança & Performance
1. **`calculate` usa `eval`** — `tools/math_tools.py`. Mitigado por whitelist de caracteres + `__builtins__=None`, mas `eval` continua sendo um primitivo sensível; aceitável dada a allowlist estrita.
2. **Guarda de path-traversal baseada em `commonpath`** — `io_tools.py:_is_safe_path` usa `os.path.commonpath` (o caminho resolvido deve estar sob o cwd). Casos de borda com symlinks ou `..` ainda são possíveis. *Risco: baixo-médio.*
3. **`search_grep` limita a 100 resultados** — `io_tools.py:search_grep` trunca a saída; codebases grandes podem esconder matches além do limite. Aceitável para controle de tamanho de contexto.
4. **Compartilhamento de contexto entre subagentes** — `spawn_subagents_parallel` reutiliza o único provider ativo entre threads (`tools/multi_agent.py`). Os clients dos SDKs (OpenAI/Gemini/Anthropic) são geralmente thread-safe, mas uso concorrente de tokens / rate limits não é gerenciado. *Risco: médio com muitos subagentes paralelos.*
5. **`checkpoint.json` escrito na raiz do projeto** — `agent/core.py` escreve o histórico completo de conversa em `checkpoint.json` (gitignored). Se o gitignore estiver mal configurado, o histórico (potencialmente sensível) pode ser commitado. *Risco: baixo (gitignored).*
6. **Concorrência do banco de memória** — `AgentMemory` (`memory/core.py`) usa um `threading.RLock` de nível de classe compartilhado por todas as instâncias, com `rollback()` em falhas de escrita e PRAGMA `journal_mode=WAL` (ver `memory/schema.py`); escritas concorrentes de subagentes são serializadas com segurança. *Risco: baixo.*

## Caminhos Obrigatórios (não modificar sem revisão)
- `tools/__init__.py` — `REGISTERED_TOOLS` registro single-source + validação em tempo de importação; derivação de `TOOLS_METADATA`/`TOOLS_MAP`.
- `agent/core.py` — loop ReAct, interceptação de ferramentas, handover checkpoint.
- `providers/base.py` — contrato `BaseLLMProvider` + `retry_with_backoff`.
- `context/builder.py` — compilação dinâmica de prompt (afeta toda chamada LLM).
