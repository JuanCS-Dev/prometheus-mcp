"""
Intent Detection - Detecta automaticamente qual agent usar.

Baseado em keywords e padrões na mensagem do usuário.
"""

import re
from typing import Optional, Tuple


class IntentDetector:
    """Detecta intenção do usuário para rotear para agent correto."""
    
    def __init__(self):
        # Keywords por agent
        self.intent_patterns = {
            "planner": {
                "keywords": [
                    "plan", "plano", "planeje", "planning", "planear",
                    "dominar", "estratégia", "strategy", "roadmap",
                    "objetivos", "goals", "metas", "como fazer",
                    "passo a passo", "etapas", "fases"
                ],
                "patterns": [
                    r"como (posso|fazer|criar|desenvolver)",
                    r"qual (o|a) (melhor )?(forma|jeito|maneira)",
                    r"vamos (criar|fazer|planejar)",
                    r"preciso (criar|fazer|planejar)",
                ]
            },
            "architect": {
                "keywords": [
                    "arquitetura", "architecture", "design", "desenhar",
                    "estrutura", "structure", "sistema", "system",
                    "microservices", "api", "database", "banco de dados",
                    "escalabilidade", "scalability"
                ],
                "patterns": [
                    r"como (estruturar|organizar|arquitetar)",
                    r"qual arquitetura",
                    r"design de sistema",
                ]
            },
            "refactor": {
                "keywords": [
                    "refactor", "refatorar", "melhorar", "improve",
                    "otimizar", "optimize", "limpar", "clean",
                    "reescrever", "rewrite"
                ],
                "patterns": [
                    r"como melhorar (este|esse|o|a)",
                    r"refatora(r|ção)",
                    r"pode melhorar",
                ]
            },
            "test": {
                "keywords": [
                    "test", "teste", "testes", "testing",
                    "unit test", "integration test", "e2e",
                    "coverage", "cobertura", "pytest", "jest"
                ],
                "patterns": [
                    r"criar testes",
                    r"testar (este|esse|o|a)",
                    r"unit test",
                ]
            },
            "reviewer": {
                "keywords": [
                    "review", "revisar", "revisão", "analise", "análise",
                    "code review", "feedback", "melhorias",
                    "bugs", "problemas", "issues", "crítica", "avalie", "avaliação"
                ],
                "patterns": [
                    r"(faz|faça|fazer) (um |o )?review",
                    r"revisa(r|ção)",
                    r"analisa(r|análise)",
                    r"o que (está|esta) errado",
                    r"tem (bug|problema|erro)",
                    r"avali(a|e|ar|ação)",
                ]
            },
            "docs": {
                "keywords": [
                    "documentar", "document", "documentação", "documentation",
                    "readme", "doc", "docs", "explicar", "explain",
                    "comentários", "comments"
                ],
                "patterns": [
                    r"documenta(r|ção)",
                    r"criar (readme|doc)",
                    r"explica(r|ção)",
                ]
            },
            "explorer": {
                "keywords": [
                    "explorar", "explore", "navegar", "navigate",
                    "procurar", "search", "encontrar", "find",
                    "onde está", "where is", "mostrar", "show"
                ],
                "patterns": [
                    r"onde (está|fica|tem)",
                    r"mostra(r|me)",
                    r"encontra(r|me)",
                ]
            },
            "performance": {
                "keywords": [
                    "performance", "performar", "otimizar", "optimize",
                    "rápido", "velocidade", "speed", "lento", "slow",
                    "benchmark", "profile", "profiling"
                ],
                "patterns": [
                    r"otimiza(r|ção)",
                    r"melhorar performance",
                    r"mais rápido",
                    r"(está|ta) lento",
                ]
            },
            "security": {
                "keywords": [
                    "segurança", "security", "vulnerabilidade", "vulnerability",
                    "hack", "exploit", "ataque", "attack",
                    "sql injection", "xss", "csrf", "proteção", "protection"
                ],
                "patterns": [
                    r"vulnerabilidad(e|es)",
                    r"falha de segurança",
                    r"security (issue|flaw|bug)",
                    r"pode ser hackeado",
                ]
            }
        }
    
    def detect(self, message: str) -> Optional[str]:
        """
        Detecta qual agent deve ser usado baseado na mensagem.
        
        Returns:
            Nome do agent ou None se não detectar nada específico.
        """
        message_lower = message.lower()
        
        # Score por agent
        scores = {}
        
        for agent, patterns in self.intent_patterns.items():
            score = 0
            
            # Check keywords
            for keyword in patterns["keywords"]:
                if keyword in message_lower:
                    score += 2
            
            # Check regex patterns
            for pattern in patterns["patterns"]:
                if re.search(pattern, message_lower):
                    score += 5  # Patterns valem mais
            
            if score > 0:
                scores[agent] = score
        
        # Retorna agent com maior score
        if scores:
            best_agent = max(scores, key=scores.get)
            best_score = scores[best_agent]
            
            # Apenas retorna se score for significativo
            if best_score >= 3:
                return best_agent
        
        return None
    
    def should_use_agent(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica se deve usar um agent e qual.
        
        Returns:
            (should_use, agent_name)
        """
        agent = self.detect(message)
        return (agent is not None, agent)
