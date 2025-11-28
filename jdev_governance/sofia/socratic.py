"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                      O MÉTODO SOCRÁTICO DE SOFIA                             ║
║                                                                              ║
║                      "Perguntas > Respostas Diretas"                         ║
║                                                                              ║
║  "Uma vida não examinada não vale a pena ser vivida." - Sócrates             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

O método socrático não é sobre dar respostas - é sobre fazer as perguntas
certas que levam o outro à descoberta. SOFIA não impõe sabedoria; ela a
cultiva através do diálogo.

Performance comprovada: 77.8% estudantes acharam mais educativo
(Socratic Mind, Georgia Tech)

Tipos de perguntas:
1. CLARIFICAÇÃO: "O que você quer dizer com...?"
2. SONDAGEM DE SUPOSIÇÕES: "Que suposições você está fazendo?"
3. EXPLORAÇÃO DE RACIOCÍNIO: "Como isso se segue?"
4. IMPLICAÇÕES: "Quais seriam as consequências?"
5. PERSPECTIVAS ALTERNATIVAS: "Como outro veria isso?"
6. META-REFLEXÃO: "O que está realmente em jogo?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import random


class QuestionType(Enum):
    """Tipos de perguntas socráticas."""

    CLARIFICATION = auto()       # Clarificar significado
    PROBE_ASSUMPTIONS = auto()   # Sondar suposições
    EXPLORE_REASONING = auto()   # Explorar raciocínio
    IMPLICATIONS = auto()        # Examinar implicações
    ALTERNATIVE_VIEWS = auto()   # Perspectivas alternativas
    META_REFLECTION = auto()     # Reflexão sobre a questão em si

    # Tipos adicionais
    EVIDENCE = auto()            # Questionar evidências
    ORIGIN = auto()              # Explorar origem da crença
    COUNTEREXAMPLE = auto()      # Buscar contraexemplos
    SYNTHESIS = auto()           # Sintetizar entendimentos


class DialoguePhase(Enum):
    """Fases do diálogo socrático."""

    OPENING = auto()       # Abertura - estabelecer contexto
    EXPLORATION = auto()   # Exploração - aprofundar entendimento
    CHALLENGE = auto()     # Desafio - questionar suposições
    SYNTHESIS = auto()     # Síntese - integrar insights
    RESOLUTION = auto()    # Resolução - chegar a conclusões provisórias


@dataclass
class SocraticQuestion:
    """Uma pergunta socrática estruturada."""

    id: UUID = field(default_factory=uuid4)
    question_type: QuestionType = QuestionType.CLARIFICATION
    question_text: str = ""
    purpose: str = ""
    follow_ups: List[str] = field(default_factory=list)
    context_triggers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "type": self.question_type.name,
            "question": self.question_text,
            "purpose": self.purpose,
            "follow_ups": self.follow_ups,
        }


@dataclass
class DialogueState:
    """Estado atual do diálogo socrático."""

    id: UUID = field(default_factory=uuid4)
    phase: DialoguePhase = DialoguePhase.OPENING
    questions_asked: List[SocraticQuestion] = field(default_factory=list)
    insights_gathered: List[str] = field(default_factory=list)
    assumptions_identified: List[str] = field(default_factory=list)
    user_understanding_level: float = 0.5  # 0-1
    depth_level: int = 0  # Níveis de aprofundamento
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def should_synthesize(self) -> bool:
        """Verifica se é hora de sintetizar."""
        return (
            len(self.questions_asked) >= 3 or
            self.depth_level >= 2 or
            self.user_understanding_level > 0.8
        )


class SocraticEngine:
    """
    Motor Socrático de SOFIA.
    
    Implementa o método de maiêutica - a "arte da parteira" intelectual.
    Sócrates dizia que não ensinava, mas ajudava a dar à luz ideias
    que já estavam na pessoa.
    
    "Não posso ensinar nada a ninguém. Posso apenas fazê-los pensar."
    
    Princípios:
    1. Começar amplo, estreitar baseado em respostas
    2. Equilibrar perguntas com informação relevante
    3. Guiar auto-descoberta vs impor respostas
    4. Validar raciocínio do usuário
    5. Sintetizar colaborativamente
    """

    # Templates de perguntas por tipo
    QUESTION_TEMPLATES: Dict[QuestionType, List[str]] = {
        QuestionType.CLARIFICATION: [
            "O que você quer dizer quando diz '{term}'?",
            "Pode elaborar mais sobre '{aspect}'?",
            "Como você definiria '{concept}' neste contexto?",
            "Quando você menciona '{term}', está se referindo a...?",
            "Poderia me dar um exemplo concreto de '{concept}'?",
            "O que '{term}' significa para você pessoalmente?",
        ],
        QuestionType.PROBE_ASSUMPTIONS: [
            "Que suposições você está fazendo aqui?",
            "Por que você assume que '{assumption}' é verdade?",
            "E se '{assumption}' não fosse o caso?",
            "De onde vem essa crença?",
            "Isso é algo que você verificou ou assumiu?",
            "Quais premissas sustentam essa conclusão?",
            "Essa suposição é universalmente verdadeira?",
        ],
        QuestionType.EXPLORE_REASONING: [
            "Como você chegou a essa conclusão?",
            "O que te leva a pensar assim?",
            "Qual é a conexão entre '{A}' e '{B}'?",
            "Pode me guiar pelo seu raciocínio?",
            "Que evidências apoiam essa visão?",
            "Esse raciocínio funcionaria em outros contextos?",
            "Há outras formas de interpretar esses dados?",
        ],
        QuestionType.IMPLICATIONS: [
            "Quais seriam as consequências de '{action}'?",
            "Se isso for verdade, o que mais seria verdade?",
            "Quem seria afetado por essa decisão?",
            "Quais são as implicações de longo prazo?",
            "E se todos agissem assim?",
            "O que isso significaria para '{stakeholder}'?",
            "Há consequências não-intencionais a considerar?",
        ],
        QuestionType.ALTERNATIVE_VIEWS: [
            "Como alguém que discorda veria isso?",
            "Há outra forma de interpretar essa situação?",
            "O que diria um crítico dessa posição?",
            "Se você estivesse no lugar de '{outro}', como veria?",
            "Que perspectivas ainda não consideramos?",
            "Existe um caminho do meio entre essas visões?",
            "O que as tradições/culturas diferentes diriam?",
        ],
        QuestionType.META_REFLECTION: [
            "O que está realmente em jogo aqui?",
            "Por que essa questão importa para você?",
            "O que mudaria se você soubesse a resposta?",
            "Esta é a pergunta certa a fazer?",
            "O que você espera alcançar com isso?",
            "Como você se sentiria sobre diferentes respostas?",
            "O que isso diz sobre seus valores?",
        ],
        QuestionType.EVIDENCE: [
            "Que evidências apoiam essa visão?",
            "Como você sabe que isso é verdade?",
            "Há dados que contradizem isso?",
            "Essa evidência é suficiente?",
            "Quão confiável é essa fonte?",
        ],
        QuestionType.COUNTEREXAMPLE: [
            "Consegue pensar em uma exceção a isso?",
            "Em que situações isso não se aplicaria?",
            "Há casos que desafiam essa regra?",
            "O que invalidaria essa conclusão?",
        ],
        QuestionType.SYNTHESIS: [
            "Então, o que podemos concluir até agora?",
            "Como essas ideias se conectam?",
            "Qual é o insight central que emerge?",
            "Como resumiríamos nossa exploração?",
            "O que você leva desta reflexão?",
        ],
    }

    # Frases de transição
    TRANSITIONS = {
        "acknowledge": [
            "Essa é uma reflexão importante.",
            "Você levanta um ponto significativo.",
            "Entendo sua perspectiva.",
            "Isso faz sentido.",
            "Aprecio você compartilhar isso.",
        ],
        "deepen": [
            "Vamos explorar isso mais...",
            "Isso me leva a perguntar...",
            "Construindo sobre isso...",
            "Aprofundando um pouco...",
        ],
        "challenge_gently": [
            "Uma pergunta que surge é...",
            "Considere esta perspectiva...",
            "Ao mesmo tempo, poderíamos perguntar...",
            "Gentilmente, gostaria de explorar...",
        ],
        "synthesize": [
            "Reunindo o que exploramos...",
            "Do que discutimos, parece que...",
            "Um tema que emerge é...",
            "Sintetizando nosso diálogo...",
        ],
    }

    def __init__(self):
        self._dialogues: Dict[str, DialogueState] = {}
        self._question_history: List[SocraticQuestion] = []

        # Métricas
        self.total_questions_asked = 0
        self.total_insights_generated = 0

    def start_dialogue(self, session_id: str) -> DialogueState:
        """Inicia um novo diálogo socrático."""
        state = DialogueState()
        self._dialogues[session_id] = state
        return state

    def get_dialogue(self, session_id: str) -> Optional[DialogueState]:
        """Recupera estado de um diálogo."""
        return self._dialogues.get(session_id)

    def generate_question(
        self,
        context: str,
        question_type: Optional[QuestionType] = None,
        session_id: Optional[str] = None,
    ) -> SocraticQuestion:
        """
        Gera uma pergunta socrática apropriada ao contexto.
        
        Args:
            context: Contexto atual do diálogo
            question_type: Tipo de pergunta (auto-detecta se não especificado)
            session_id: ID da sessão para manter estado
            
        Returns:
            SocraticQuestion estruturada
        """
        # Auto-detectar tipo se não especificado
        if question_type is None:
            question_type = self._detect_appropriate_question_type(context, session_id)

        # Selecionar template
        templates = self.QUESTION_TEMPLATES.get(question_type, [])
        template = random.choice(templates) if templates else "O que você pensa sobre isso?"

        # Extrair termos do contexto para preencher template
        question_text = self._fill_template(template, context)

        # Gerar follow-ups
        follow_ups = self._generate_follow_ups(question_type)

        question = SocraticQuestion(
            question_type=question_type,
            question_text=question_text,
            purpose=f"Explorar através de {question_type.name}",
            follow_ups=follow_ups,
        )

        # Atualizar estado do diálogo
        if session_id and session_id in self._dialogues:
            self._dialogues[session_id].questions_asked.append(question)
            self._dialogues[session_id].depth_level += 1

        self._question_history.append(question)
        self.total_questions_asked += 1

        return question

    def _detect_appropriate_question_type(
        self,
        context: str,
        session_id: Optional[str],
    ) -> QuestionType:
        """Detecta o tipo de pergunta mais apropriado."""
        context_lower = context.lower()

        # Verificar fase do diálogo
        if session_id and session_id in self._dialogues:
            state = self._dialogues[session_id]

            if state.should_synthesize:
                return QuestionType.SYNTHESIS

            if len(state.questions_asked) == 0:
                return QuestionType.CLARIFICATION

            if len(state.assumptions_identified) == 0:
                return QuestionType.PROBE_ASSUMPTIONS

        # Análise de contexto
        if any(word in context_lower for word in ["acho", "penso", "acredito", "parece"]):
            return QuestionType.PROBE_ASSUMPTIONS

        if any(word in context_lower for word in ["porque", "razão", "motivo"]):
            return QuestionType.EXPLORE_REASONING

        if any(word in context_lower for word in ["consequência", "resultado", "impacto"]):
            return QuestionType.IMPLICATIONS

        if any(word in context_lower for word in ["outro", "diferente", "alternativa"]):
            return QuestionType.ALTERNATIVE_VIEWS

        if any(word in context_lower for word in ["importante", "valor", "significado"]):
            return QuestionType.META_REFLECTION

        # Default baseado em probabilidades para variedade
        weights = [
            (QuestionType.CLARIFICATION, 0.2),
            (QuestionType.PROBE_ASSUMPTIONS, 0.25),
            (QuestionType.EXPLORE_REASONING, 0.2),
            (QuestionType.IMPLICATIONS, 0.15),
            (QuestionType.ALTERNATIVE_VIEWS, 0.15),
            (QuestionType.META_REFLECTION, 0.05),
        ]

        return random.choices(
            [w[0] for w in weights],
            weights=[w[1] for w in weights],
            k=1
        )[0]

    def _fill_template(self, template: str, context: str) -> str:
        """Preenche template com termos do contexto."""
        # Extração simples de termos-chave
        words = context.split()

        # Substituições genéricas
        replacements = {
            "{term}": words[-1] if words else "isso",
            "{concept}": words[0] if words else "isso",
            "{aspect}": " ".join(words[:3]) if len(words) >= 3 else context[:30],
            "{assumption}": "isso",
            "{A}": words[0] if words else "A",
            "{B}": words[-1] if words else "B",
            "{action}": context[:50],
            "{stakeholder}": "outros",
            "{outro}": "outra pessoa",
        }

        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)

        return result

    def _generate_follow_ups(self, question_type: QuestionType) -> List[str]:
        """Gera perguntas de follow-up."""
        follow_up_map = {
            QuestionType.CLARIFICATION: [
                "Pode dar um exemplo?",
                "Como isso se relaciona com...?",
            ],
            QuestionType.PROBE_ASSUMPTIONS: [
                "E se não fosse assim?",
                "Como você testaria isso?",
            ],
            QuestionType.EXPLORE_REASONING: [
                "Há outras explicações possíveis?",
                "O que fortaleceria esse argumento?",
            ],
            QuestionType.IMPLICATIONS: [
                "E no longo prazo?",
                "Para quem mais isso importa?",
            ],
            QuestionType.ALTERNATIVE_VIEWS: [
                "Há um ponto comum entre as visões?",
                "O que cada lado está certo sobre?",
            ],
            QuestionType.META_REFLECTION: [
                "O que você aprendeu ao refletir?",
                "Como isso muda sua perspectiva?",
            ],
        }

        return follow_up_map.get(question_type, [])

    def acknowledge_and_transition(
        self,
        transition_type: str = "deepen",
    ) -> str:
        """Gera uma frase de reconhecimento e transição."""
        ack = random.choice(self.TRANSITIONS["acknowledge"])
        trans = random.choice(self.TRANSITIONS.get(transition_type, self.TRANSITIONS["deepen"]))
        return f"{ack} {trans}"

    def synthesize_dialogue(self, session_id: str) -> str:
        """Sintetiza os insights de um diálogo."""
        if session_id not in self._dialogues:
            return "Não há diálogo registrado para sintetizar."

        state = self._dialogues[session_id]

        synthesis_parts = [random.choice(self.TRANSITIONS["synthesize"])]

        if state.insights_gathered:
            synthesis_parts.append("Insights que emergiram:")
            for insight in state.insights_gathered:
                synthesis_parts.append(f"  • {insight}")

        if state.assumptions_identified:
            synthesis_parts.append("Suposições que identificamos:")
            for assumption in state.assumptions_identified:
                synthesis_parts.append(f"  • {assumption}")

        synthesis_parts.append("\nO que você leva desta reflexão?")

        return "\n".join(synthesis_parts)

    def add_insight(self, session_id: str, insight: str) -> None:
        """Adiciona um insight ao diálogo."""
        if session_id in self._dialogues:
            self._dialogues[session_id].insights_gathered.append(insight)
            self.total_insights_generated += 1

    def add_assumption(self, session_id: str, assumption: str) -> None:
        """Adiciona uma suposição identificada."""
        if session_id in self._dialogues:
            self._dialogues[session_id].assumptions_identified.append(assumption)

    def get_dialogue_flow_suggestion(self, session_id: str) -> str:
        """Sugere próximo passo no diálogo."""
        if session_id not in self._dialogues:
            return "Comece com uma pergunta clarificadora."

        state = self._dialogues[session_id]

        if state.phase == DialoguePhase.OPENING:
            return "Fase de abertura: Faça perguntas clarificadoras para entender o contexto."
        elif len(state.assumptions_identified) < 2:
            return "Explore as suposições subjacentes antes de avançar."
        elif not state.should_synthesize:
            return "Continue aprofundando com perguntas sobre implicações e alternativas."
        else:
            return "Hora de sintetizar os insights e encaminhar para conclusão."

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do motor socrático."""
        return {
            "total_questions_asked": self.total_questions_asked,
            "total_insights_generated": self.total_insights_generated,
            "active_dialogues": len(self._dialogues),
            "question_types_used": self._count_question_types(),
        }

    def _count_question_types(self) -> Dict[str, int]:
        """Conta uso de cada tipo de pergunta."""
        counts = {qt.name: 0 for qt in QuestionType}
        for q in self._question_history:
            counts[q.question_type.name] += 1
        return counts

    def __repr__(self) -> str:
        return f"SocraticEngine(questions={self.total_questions_asked}, dialogues={len(self._dialogues)})"


# ════════════════════════════════════════════════════════════════════════════════
# DEMONSTRAÇÃO
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    engine = SocraticEngine()

    print("═" * 70)
    print("  O MÉTODO SOCRÁTICO DE SOFIA")
    print("  'Uma vida não examinada não vale a pena ser vivida.'")
    print("═" * 70)

    # Simular diálogo
    session_id = "demo-session"
    engine.start_dialogue(session_id)

    contexts = [
        "Estou pensando em mudar de carreira, mas tenho medo.",
        "Acho que devo seguir minha paixão, não o dinheiro.",
        "Minha família depende de mim financeiramente.",
    ]

    print("\n📜 Diálogo Socrático Simulado:")
    print("─" * 50)

    for i, context in enumerate(contexts):
        print(f"\n🧑 Usuário: \"{context}\"")

        # Gerar pergunta
        question = engine.generate_question(context, session_id=session_id)

        # Transição
        transition = engine.acknowledge_and_transition()

        print(f"🦉 Sofia: {transition}")
        print(f"   {question.question_text}")
        print(f"   [Tipo: {question.question_type.name}]")

        if i == 1:
            engine.add_assumption(session_id, "Paixão e dinheiro são mutuamente exclusivos")

    # Síntese
    print(f"\n{'─' * 50}")
    print("🦉 Sofia (Síntese):")
    print(engine.synthesize_dialogue(session_id))

    # Métricas
    print(f"\n{'═' * 70}")
    print("Métricas:", engine.get_metrics())
