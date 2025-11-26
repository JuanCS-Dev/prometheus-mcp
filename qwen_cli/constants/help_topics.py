"""
Help system content for JuanCS Dev-Code.

Interactive help with navigable topics.
"""

HELP_MAIN = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]              [bold white]JuanCS Dev-Code[/bold white] — [dim]Ajuda Interativa[/dim]           [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]Navegue pelos tópicos:[/bold yellow]

  [cyan]/help commands[/cyan]    Comandos do sistema
  [cyan]/help agents[/cyan]      Agentes especializados (13)
  [cyan]/help tools[/cyan]       Ferramentas disponíveis (33+)
  [cyan]/help keys[/cyan]        Atalhos de teclado
  [cyan]/help tips[/cyan]        Dicas de uso

[dim]─────────────────────────────────────────────────────────────[/dim]

[bold green]Início Rápido:[/bold green]

  • Digite naturalmente para conversar com a IA
  • Use [cyan]/[/cyan] para comandos e agentes
  • [cyan]Tab[/cyan] autocompleta, [cyan]↑↓[/cyan] navega histórico

[dim]Digite[/dim] [cyan]/help <tópico>[/cyan] [dim]para detalhes ou apenas converse![/dim]
"""

HELP_COMMANDS = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                    [bold white]Comandos do Sistema[/bold white]                    [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]Navegação[/bold yellow]
  [cyan]/help[/cyan] [dim].............[/dim] Esta ajuda interativa
  [cyan]/clear[/cyan] [dim]............[/dim] Limpa a tela
  [cyan]/quit[/cyan] [cyan]/exit[/cyan] [dim].....[/dim] Sai da aplicação
  [cyan]/status[/cyan] [dim]...........[/dim] Status do sistema

[bold yellow]Execução[/bold yellow]
  [cyan]/run[/cyan] [white]<cmd>[/white] [dim]........[/dim] Executa comando bash
  [cyan]/read[/cyan] [white]<file>[/white] [dim].....[/dim] Lê arquivo com syntax highlight

[bold yellow]Descoberta[/bold yellow]
  [cyan]/tools[/cyan] [dim]............[/dim] Lista ferramentas por categoria
  [cyan]/agents[/cyan] [dim]...........[/dim] Lista agentes disponíveis
  [cyan]/palette[/cyan] [white]<q>[/white] [dim].....[/dim] Busca fuzzy em comandos
  [cyan]/history[/cyan] [white][q][/white] [dim].....[/dim] Busca no histórico

[bold yellow]Contexto[/bold yellow]
  [cyan]/context[/cyan] [dim]..........[/dim] Mostra contexto da conversa
  [cyan]/context-clear[/cyan] [dim]....[/dim] Limpa o contexto

[dim]← /help[/dim]
"""

HELP_AGENTS = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                 [bold white]Agentes Especializados[/bold white]                    [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]Planejamento (v6.1)[/bold yellow]
  [cyan]/plan[/cyan] [white]<objetivo>[/white] [dim]......[/dim] GOAP planning, decompõe tarefas
  [cyan]/plan multi[/cyan] [white]<obj>[/white] [dim]....[/dim] Gera 3 planos alternativos (risk/reward)
  [cyan]/plan clarify[/cyan] [white]<obj>[/white] [dim]..[/dim] Faz perguntas antes de planejar
  [cyan]/plan explore[/cyan] [white]<obj>[/white] [dim]..[/dim] Análise read-only (sem modificar)
  [cyan]/architect[/cyan] [white]<spec>[/white] [dim]....[/dim] Análise de arquitetura

[bold yellow]Código[/bold yellow]
  [cyan]/execute[/cyan] [white]<tarefa>[/white] [dim]....[/dim] Executa código com sandbox
  [cyan]/explore[/cyan] [white]<query>[/white] [dim].....[/dim] Busca na codebase
  [cyan]/refactor[/cyan] [white]<tarefa>[/white] [dim]...[/dim] Melhora código existente

[bold yellow]Qualidade[/bold yellow]
  [cyan]/review[/cyan] [white][arquivo][/white] [dim]....[/dim] Code review detalhado
  [cyan]/test[/cyan] [white][path][/white] [dim].........[/dim] Gera testes automatizados
  [cyan]/security[/cyan] [white][arquivo][/white] [dim]..[/dim] Análise OWASP de segurança

[bold yellow]Docs & Perf[/bold yellow]
  [cyan]/docs[/cyan] [white][arquivo][/white] [dim].......[/dim] Gera documentação
  [cyan]/perf[/cyan] [white][arquivo][/white] [dim].......[/dim] Profiling e otimização

[bold yellow]Infra[/bold yellow]
  [cyan]/devops[/cyan] [white]<tarefa>[/white] [dim].....[/dim] Docker, CI/CD, K8s

[bold yellow]Dados[/bold yellow]
  [cyan]/data[/cyan] [white]<tarefa>[/white] [dim].......[/dim] Otimização e análise de banco de dados

[bold yellow]Governança & Counsel[/bold yellow]
  [cyan]/justica[/cyan] [white]<ação>[/white] [dim].....[/dim] Avaliação constitucional
  [cyan]/sofia[/cyan] [white]<query>[/white] [dim].......[/dim] Conselho ético e sabedoria

[dim]← /help[/dim]
"""

HELP_TOOLS = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                   [bold white]Ferramentas (33+)[/bold white]                       [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]📁 Arquivos[/bold yellow]
  [cyan]read_file[/cyan]  [cyan]write_file[/cyan]  [cyan]edit_file[/cyan]  [cyan]delete_file[/cyan]
  [cyan]list_directory[/cyan]  [cyan]move_file[/cyan]  [cyan]copy_file[/cyan]  [cyan]create_directory[/cyan]

[bold yellow]💻 Terminal[/bold yellow]
  [cyan]cd[/cyan]  [cyan]ls[/cyan]  [cyan]pwd[/cyan]  [cyan]mkdir[/cyan]  [cyan]rm[/cyan]  [cyan]cp[/cyan]  [cyan]mv[/cyan]  [cyan]touch[/cyan]  [cyan]cat[/cyan]

[bold yellow]⚡ Execução[/bold yellow]
  [cyan]bash_command[/cyan] [dim]— comando com timeout e validação[/dim]

[bold yellow]🔍 Busca[/bold yellow]
  [cyan]search_files[/cyan]  [cyan]get_directory_tree[/cyan]

[bold yellow]📊 Git[/bold yellow]
  [cyan]git_status[/cyan]  [cyan]git_diff[/cyan]

[bold yellow]🌐 Web[/bold yellow]
  [cyan]web_search[/cyan]  [cyan]fetch_url[/cyan]  [cyan]download_file[/cyan]  [cyan]http_request[/cyan]

[dim]A LLM invoca ferramentas automaticamente quando necessário.[/dim]

[dim]← /help    /tools para lista completa[/dim]
"""

HELP_KEYS = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                   [bold white]Atalhos de Teclado[/bold white]                      [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]Navegação[/bold yellow]
  [cyan]↑[/cyan] [cyan]↓[/cyan] [dim]...............[/dim] Histórico de comandos
  [cyan]Tab[/cyan] [dim]................[/dim] Aceita autocomplete
  [cyan]Escape[/cyan] [dim].............[/dim] Fecha autocomplete

[bold yellow]Controle[/bold yellow]
  [cyan]Ctrl+C[/cyan] [dim].............[/dim] Sai da aplicação
  [cyan]Ctrl+L[/cyan] [dim].............[/dim] Limpa a tela
  [cyan]Ctrl+P[/cyan] [dim].............[/dim] Mostra ajuda
  [cyan]Enter[/cyan] [dim]..............[/dim] Envia comando/mensagem

[bold yellow]Autocomplete[/bold yellow]
  [dim]Digite[/dim] [cyan]/[/cyan] [dim]para ver comandos[/dim]
  [dim]Digite parte do nome para filtrar[/dim]
  [cyan]↑[/cyan] [cyan]↓[/cyan] [dim]seleciona,[/dim] [cyan]Tab[/cyan] [dim]confirma[/dim]

[dim]← /help[/dim]
"""

HELP_TIPS = """
[bold cyan]╭─────────────────────────────────────────────────────────────╮[/bold cyan]
[bold cyan]│[/bold cyan]                      [bold white]Dicas de Uso[/bold white]                         [bold cyan]│[/bold cyan]
[bold cyan]╰─────────────────────────────────────────────────────────────╯[/bold cyan]

[bold yellow]💬 Chat Natural[/bold yellow]
  Apenas digite sua pergunta. O contexto é mantido.
  [dim]> Como faço um servidor HTTP em Python?[/dim]
  [dim]> Agora adicione autenticação[/dim]

[bold yellow]📝 Criar Arquivos[/bold yellow]
  Peça para criar — a IA usa [cyan]write_file[/cyan] automaticamente.
  [dim]> Crie um hello.py que imprime Hello World[/dim]
  [dim]> Crie um Dockerfile para Flask[/dim]

[bold yellow]🔄 Fluxo Recomendado[/bold yellow]
  [cyan]1.[/cyan] [white]/explore[/white] [dim]— entenda a codebase[/dim]
  [cyan]2.[/cyan] [white]/architect[/white] [dim]— planeje a solução[/dim]
  [cyan]3.[/cyan] [white]/plan[/white] [dim]— decomponha em tarefas[/dim]
  [cyan]4.[/cyan] [white]/execute[/white] [dim]— implemente[/dim]
  [cyan]5.[/cyan] [white]/review[/white] [dim]— valide qualidade[/dim]
  [cyan]6.[/cyan] [white]/test[/white] [dim]— adicione testes[/dim]

[bold yellow]⚡ Produtividade[/bold yellow]
  • Use [cyan]/palette[/cyan] para buscar comandos rapidamente
  • [cyan]Tab[/cyan] acelera muito com autocomplete
  • Histórico persiste entre sessões

[dim]← /help[/dim]
"""

# Map for help subcommands
HELP_TOPICS = {
    "": HELP_MAIN,
    "commands": HELP_COMMANDS,
    "command": HELP_COMMANDS,
    "cmd": HELP_COMMANDS,
    "agents": HELP_AGENTS,
    "agent": HELP_AGENTS,
    "tools": HELP_TOOLS,
    "tool": HELP_TOOLS,
    "keys": HELP_KEYS,
    "key": HELP_KEYS,
    "keyboard": HELP_KEYS,
    "shortcuts": HELP_KEYS,
    "tips": HELP_TIPS,
    "tip": HELP_TIPS,
    "dicas": HELP_TIPS,
}

# Legacy compatibility
HELP_TEXT = HELP_MAIN
