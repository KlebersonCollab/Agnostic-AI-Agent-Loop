import json

def handler(messages: list, tools: list):
    from rich.console import Console
    console = Console()
    
    # 1. Calcular tokens do histórico de mensagens
    msg_chars = 0
    for msg in messages:
        if msg.content:
            msg_chars += len(msg.content)
        # Se a mensagem contiver chamadas de ferramenta anteriores
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                msg_chars += len(json.dumps(tc.model_dump()))
                
    msg_tokens = (msg_chars + 3) // 4
    
    # 2. Calcular tokens das ferramentas disponíveis na janela
    tool_tokens = 0
    if tools:
        tool_chars = 0
        for tool_def in tools:
            # Converte a definição da ferramenta (objeto Pydantic) para JSON/string
            if hasattr(tool_def, "model_dump"):
                tool_chars += len(json.dumps(tool_def.model_dump()))
            else:
                tool_chars += len(json.dumps(tool_def))
        tool_tokens = (tool_chars + 3) // 4
        
    total_tokens = msg_tokens + tool_tokens
    
    # 3. Exibir formatado no console
    console.print(
        f"[bold blue]📡 [API Request][/bold blue] Envio de contexto para o Provedor:\n"
        f"  • Mensagens de conversa: {msg_tokens:,} est. tokens\n"
        f"  • Ferramentas (schemas): {tool_tokens:,} est. tokens\n"
        f"  • [bold green]Total de tokens: {total_tokens:,}[/bold green]"
    )
    
    # Retorna o contexto intacto para continuar o envio
    return messages, tools
