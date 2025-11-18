# 📁 Estrutura do Projeto QWEN-DEV-CLI

> Organização semântica e profissional do repositório

## �� Visão Geral

```
qwen-dev-cli/
├── 📦 qwen_dev_cli/        # Código-fonte principal
├── 🧪 tests/               # Suite de testes
├── 📚 docs/                # Documentação
├── 📝 examples/            # Exemplos de uso
├── ⚡ benchmarks/          # Testes de performance
├── 🔧 scripts/             # Scripts utilitários
└── ⚙️  Configurações        # Arquivos de config na raiz
```

---

## 📦 Código-Fonte (`qwen_dev_cli/`)

### Core Business Logic
```
core/
├── llm.py          # Cliente LLM (HuggingFace + Ollama)
├── mcp.py          # Integração MCP Filesystem
├── context.py      # Gerenciamento de contexto
└── config.py       # Configurações centralizadas
```

### Integrações Externas
```
integration/
├── parser.py       # Parser de comandos shell
└── workflow.py     # Orquestração de workflows
```

### Ferramentas MCP
```
tools/
├── shell.py        # Execução de comandos
└── terminal.py     # Utilitários de terminal
```

### Interfaces
```
├── cli.py          # Interface CLI (Typer)
├── shell.py        # Shell interativo
└── ui.py           # Interface Web (Gradio)
```

---

## 🧪 Testes (`tests/`)

### Cobertura de Testes: 90%+

```
tests/
├── test_context.py                 # Testes de contexto
├── test_conversation.py            # Sistema de conversação
├── test_edge_cases.py              # Casos extremos
├── test_functional.py              # Testes funcionais
├── test_integration_complete.py    # Integração completa
├── test_llm.py                     # Cliente LLM
├── test_llm_resilience.py          # Resiliência LLM
├── test_mcp.py                     # MCP Server
├── test_metrics_defense.py         # Métricas de defesa
├── test_parser.py                  # Parser de comandos
├── test_phase2_integration.py      # Integração Fase 2
├── test_recovery.py                # Sistema de recuperação
├── test_terminal_tools.py          # Ferramentas de terminal
├── test_tools.py                   # Tools MCP
├── test_workflow.py                # Orquestração
├── validate_project.py             # Validação de projeto
└── validate_shell.py               # Validação de shell
```

**Total:** 237+ casos de teste

---

## 📚 Documentação (`docs/`)

### Planejamento (`docs/planning/`)
```
MASTER_PLAN.md                  # Roadmap completo do projeto
DAILY_LOG.md                    # Diário de desenvolvimento
PLATFORM_INTEGRATION_PLAN.md    # Plano de integração
MASTER_PLAN.v3.0.backup.md      # Backup de versões
MASTER_PLAN.v3.0.old.md
```

### Relatórios (`docs/reports/`)
```
VALIDATION_REPORT.md                # Relatório de validação
AUDIT_REPORT.md                     # Auditoria técnica
PARSER_IMPLEMENTATION_REPORT.md     # Implementação do parser
LLM_CLIENT_IMPLEMENTATION_REPORT.md # Implementação LLM
WORKFLOW_ORCHESTRATION_SUMMARY.md   # Orquestração
FINAL_VALIDATION_SUMMARY.md         # Validação final
CONSTITUTIONAL_VALIDATION.md        # Validação constitucional
CONSTITUTIONAL_ADHERENCE.md         # Aderência constitucional
BRUTAL_REALITY.md                   # Análise crítica
EDGE_CASE_RESULTS.md                # Resultados de edge cases
EDGE_CASE_BUGS_FOUND.md             # Bugs encontrados
```

### Pesquisa (`docs/research/`)
```
PHASE_2_RESEARCH_PARSER_SHELL_INTEGRATION.md
PHASE_2_2_INTEGRATION_RESEARCH.md
PHASE_3_2_WORKFLOW_RESEARCH.md
```

### Documentação Técnica Existente
```
blaxel_api_complete.md      # API Blaxel (completa)
blaxel_api_research.md      # Pesquisa API Blaxel
blaxel_final_discovery.md   # Descobertas finais
blaxel_research.md          # Pesquisa geral
sambanova_research.md       # Pesquisa SambaNova
day6_complete.md            # Dia 6 completo
validation_report.md        # Relatório de validação
```

---

## 📝 Exemplos (`examples/`)

```
example_parser_usage.py     # Exemplo de uso do parser
```

---

## ⚡ Benchmarks (`benchmarks/`)

```
benchmark_llm.py            # Benchmarks de LLM
```

---

## 🔧 Scripts (`scripts/`)

Scripts utilitários para desenvolvimento e deployment.

---

## ⚙️  Configurações (Raiz)

```
pyproject.toml      # Configuração Poetry + Python
requirements.txt    # Dependências Python
pytest.ini          # Configuração de testes
.gitignore          # Arquivos ignorados pelo Git
.env.example        # Template de variáveis de ambiente
README.md           # Documentação principal
CHANGELOG.md        # Histórico de mudanças
PROJECT_STRUCTURE.md # Este arquivo
```

---

## 🎨 Princípios de Organização

### ✅ Separação de Responsabilidades
- **Código** vs **Testes** vs **Documentação**
- Cada categoria em seu próprio diretório

### ✅ Nomenclatura Semântica
- Diretórios com nomes claros e descritivos
- Agrupamento por função, não por tipo de arquivo

### ✅ Documentação Categorizada
- **Planning**: Roadmap e planejamento
- **Reports**: Relatórios de status e auditorias
- **Research**: Pesquisa técnica e POCs

### ✅ Raiz Limpa
- Apenas arquivos de configuração essenciais
- README e CHANGELOG visíveis
- Estrutura clara para novos contribuidores

---

## 📊 Estatísticas do Projeto

| Categoria | Quantidade |
|-----------|------------|
| Módulos Python | 35 |
| Testes | 237+ |
| Documentos | 25+ |
| Linhas de Código | 15,000+ |
| Test Cases | 237 |

---

## 🚀 Navegação Rápida

```bash
# Ver código principal
cd qwen_dev_cli/

# Rodar testes
cd tests/
pytest -v

# Ler documentação
cd docs/

# Ver exemplos
cd examples/

# Rodar benchmarks
cd benchmarks/
python benchmark_llm.py
```

---

**Organização realizada em:** 2025-11-18
**Status:** ✅ Completo e validado
