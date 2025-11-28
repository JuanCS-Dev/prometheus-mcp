"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║                               ΣΟΦΙΑ (SOFIA)                                      ║
║                           Sabedoria Encarnada                                    ║
║                                                                                  ║
║            "Você não substitui sabedoria humana - você a cultiva."               ║
║                                                                                  ║
║  ════════════════════════════════════════════════════════════════════════════   ║
║                                                                                  ║
║  SOFIA é o agente conselheiro sábio inspirado em:                               ║
║  • Virtudes do Cristianismo Primitivo (Pré-Niceia)                               ║
║  • Didaquê (50-120 d.C.)                                                        ║
║  • Práticas de Discernimento de Atos 15                                         ║
║  • Método Socrático                                                              ║
║  • Ética das Virtudes                                                           ║
║  • Pensamento Sistema 2                                                          ║
║                                                                                  ║
║  SOFIA serve como διάκονος (diákonos) - assistente que serve propósitos         ║
║  de outro, não mestre ou autoridade absoluta.                                    ║
║                                                                                  ║
║  Versão: 3.0.0 (2030 Vision)                                                    ║
║  Autor: Claude (Anthropic) + Humanidade                                          ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from .virtues import VirtueEngine, VirtueType, VirtueExpression
from .socratic import SocraticEngine, QuestionType, SocraticQuestion, DialogueState
from .deliberation import DeliberationEngine, DeliberationTrigger, DeliberationResult, ThinkingMode
from .discernment import DiscernmentEngine, DiscernmentResult


class SofiaState(Enum):
    """Estados possíveis de SOFIA."""

    LISTENING = auto()      # Ouvindo ativamente
    REFLECTING = auto()     # Refletindo (Sistema 2)
    QUESTIONING = auto()    # Fazendo perguntas socráticas
    DISCERNING = auto()     # Em processo de discernimento
    COUNSELING = auto()     # Oferecendo conselho
    LEARNING = auto()       # Aprendendo de feedback


class CounselType(Enum):
    """Tipos de aconselhamento que SOFIA oferece."""

    CLARIFYING = auto()     # Ajudando a clarificar
    EXPLORING = auto()      # Explorando perspectivas
    DELIBERATING = auto()   # Deliberação profunda
    DISCERNING = auto()     # Discernimento espiritual
    SUPPORTING = auto()     # Apoio emocional
    REFERRING = auto()      # Referindo a outros


@dataclass
class SofiaConfig:
    """Configuração do Agente SOFIA."""

    agent_id: str = "sofia-primary"
    name: str = "SOFIA"
    version: str = "3.0.0"

    # Comportamento
    default_virtue: VirtueType = VirtueType.TAPEINOPHROSYNE  # Humildade
    system2_threshold: float = 0.6  # Quando ativar Sistema 2
    socratic_ratio: float = 0.7     # % de perguntas vs respostas

    # Limites
    max_questions_per_topic: int = 5
    always_suggest_community: bool = True
    defer_to_professionals: bool = True

    # Aprendizado
    learn_from_feedback: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "version": self.version,
            "default_virtue": self.default_virtue.name,
            "system2_threshold": self.system2_threshold,
            "socratic_ratio": self.socratic_ratio,
        }


@dataclass
class SofiaCounsel:
    """
    Um conselho oferecido por SOFIA.
    
    Contém não apenas o conselho em si, mas todo o processo
    de reflexão que levou a ele - transparência total.
    """

    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Contexto
    user_query: str = ""
    session_id: Optional[str] = None
    counsel_type: CounselType = CounselType.EXPLORING

    # Processo
    thinking_mode: ThinkingMode = ThinkingMode.SYSTEM_1
    virtues_expressed: List[VirtueExpression] = field(default_factory=list)
    questions_asked: List[SocraticQuestion] = field(default_factory=list)
    deliberation: Optional[DeliberationResult] = None
    discernment: Optional[DiscernmentResult] = None

    # Resposta
    response: str = ""
    confidence: float = 0.5
    uncertainty_expressed: bool = True
    community_suggested: bool = True

    # Meta
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "counsel_type": self.counsel_type.name,
            "thinking_mode": self.thinking_mode.name,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
            "questions_count": len(self.questions_asked),
            "community_suggested": self.community_suggested,
        }


class SofiaAgent:
    """
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                              ΣΟΦΙΑ (SOFIA)                               ║
    ║                                                                          ║
    ║  O conselheiro sábio que cultiva sabedoria, não a impõe.                ║
    ║                                                                          ║
    ║  "Através de perguntas aprofundando insight, raciocínio iluminando      ║
    ║   complexidade, e humildade reconhecendo profunda responsabilidade      ║
    ║   de aconselhar sobre assuntos moldando vidas humanas."                 ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    
    SOFIA orquestra:
    
    ┌─────────────────┐     ┌─────────────────┐
    │     Virtues     │────▶│    Socratic     │
    │     Engine      │     │     Engine      │
    └─────────────────┘     └────────┬────────┘
                                     │
                                     ▼
    ┌─────────────────┐     ┌─────────────────┐
    │  Deliberation   │◀───▶│  Discernment    │
    │    (Sistema 2)  │     │    (Atos 15)    │
    └─────────────────┘     └─────────────────┘
    
    Princípios Operacionais:
    1. Ponderado > Rápido
    2. Perguntas > Respostas
    3. Humilde > Confiante
    4. Colaborativo > Diretivo
    5. Principiado > Só Pragmático
    6. Transparente > Opaco
    7. Adaptativo > Rígido
    """

    BANNER = """
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║            ███████╗ ██████╗ ███████╗██╗ █████╗                                   ║
║            ██╔════╝██╔═══██╗██╔════╝██║██╔══██╗                                  ║
║            ███████╗██║   ██║█████╗  ██║███████║                                  ║
║            ╚════██║██║   ██║██╔══╝  ██║██╔══██║                                  ║
║            ███████║╚██████╔╝██║     ██║██║  ██║                                  ║
║            ╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝                                  ║
║                                                                                  ║
║                           Σοφία - Sabedoria                                      ║
║                         Conselheiro Sábio v3.0.0                                 ║
║                                                                                  ║
║        "Você não substitui sabedoria humana - você a cultiva."                   ║
║                                                                                  ║
║          Baseado nas virtudes do Cristianismo Primitivo (Pré-Niceia)             ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
    """

    def __init__(self, config: Optional[SofiaConfig] = None):
        """Inicializa SOFIA."""
        self.config = config or SofiaConfig()
        self.state = SofiaState.LISTENING
        self.started_at: Optional[datetime] = None

        # Motores
        self.virtue_engine = VirtueEngine()
        self.socratic_engine = SocraticEngine()
        self.deliberation_engine = DeliberationEngine()
        self.discernment_engine = DiscernmentEngine()

        # Histórico
        self._counsel_history: List[SofiaCounsel] = []
        self._session_states: Dict[str, DialogueState] = {}

        # Callbacks
        self._on_question_callbacks: List[Callable[[SocraticQuestion], None]] = []
        self._on_counsel_callbacks: List[Callable[[SofiaCounsel], None]] = []

        # Métricas
        self.total_interactions = 0
        self.total_questions_asked = 0
        self.total_counsels_given = 0

    def start(self) -> None:
        """Inicia SOFIA."""
        print(self.BANNER)

        self.started_at = datetime.now(timezone.utc)
        self.state = SofiaState.LISTENING

        print(f"\n✓ SOFIA iniciada em {self.started_at.isoformat()}")
        print(f"✓ Virtude padrão: {self.config.default_virtue.name}")
        print(f"✓ Ratio socrático: {self.config.socratic_ratio:.0%} perguntas")

        # Sabedoria inicial
        wisdom = self.virtue_engine.get_didache_wisdom()
        print(f"\n📜 Didaquê: \"{wisdom}\"")

    def stop(self) -> None:
        """Encerra SOFIA."""
        self.state = SofiaState.LISTENING
        print("\n✓ SOFIA encerrada. Paz esteja convosco.")

    # ════════════════════════════════════════════════════════════════════════════
    # API PRINCIPAL
    # ════════════════════════════════════════════════════════════════════════════

    def respond(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> SofiaCounsel:
        """
        Responde a uma entrada do usuário com sabedoria.
        
        Este é o ponto principal de interação com SOFIA.
        
        Args:
            user_input: O que o usuário disse/perguntou
            session_id: ID da sessão para manter contexto
            context: Contexto adicional
            
        Returns:
            SofiaCounsel com a resposta e processo de reflexão
        """
        start_time = time.time()

        session_id = session_id or str(uuid4())
        context = context or {}

        counsel = SofiaCounsel(
            user_query=user_input,
            session_id=session_id,
        )

        # ════════════════════════════════════════════════════════════════════
        # FASE 1: DETERMINAR MODO DE PENSAMENTO
        # ════════════════════════════════════════════════════════════════════
        should_system2, trigger = self.deliberation_engine.should_activate_system2(user_input)

        if should_system2:
            counsel.thinking_mode = ThinkingMode.SYSTEM_2
            self.state = SofiaState.REFLECTING
        else:
            counsel.thinking_mode = ThinkingMode.SYSTEM_1

        # ════════════════════════════════════════════════════════════════════
        # FASE 2: DETERMINAR TIPO DE RESPOSTA
        # ════════════════════════════════════════════════════════════════════
        counsel_type = self._determine_counsel_type(user_input, context)
        counsel.counsel_type = counsel_type

        # ════════════════════════════════════════════════════════════════════
        # FASE 3: GERAR RESPOSTA BASEADA NO TIPO
        # ════════════════════════════════════════════════════════════════════
        if counsel_type == CounselType.CLARIFYING:
            response = self._respond_with_clarification(user_input, session_id, counsel)

        elif counsel_type == CounselType.EXPLORING:
            response = self._respond_with_exploration(user_input, session_id, counsel)

        elif counsel_type == CounselType.DELIBERATING:
            response = self._respond_with_deliberation(user_input, trigger, counsel)

        elif counsel_type == CounselType.DISCERNING:
            response = self._respond_with_discernment(user_input, counsel)

        elif counsel_type == CounselType.SUPPORTING:
            response = self._respond_with_support(user_input, counsel)

        elif counsel_type == CounselType.REFERRING:
            response = self._respond_with_referral(user_input, counsel)

        else:
            response = self._respond_default(user_input, counsel)

        counsel.response = response

        # ════════════════════════════════════════════════════════════════════
        # FASE 4: ADICIONAR ELEMENTOS VIRTUOSOS
        # ════════════════════════════════════════════════════════════════════
        # Sempre sugerir comunidade
        if self.config.always_suggest_community and not counsel.community_suggested:
            counsel.response += "\n\nConsidere também conversar com pessoas de sua confiança sobre isso."
            counsel.community_suggested = True

        # Expressar incerteza quando apropriado
        if counsel.confidence < 0.7 and not counsel.uncertainty_expressed:
            counsel.response = self._add_uncertainty_expression(counsel.response)
            counsel.uncertainty_expressed = True

        # ════════════════════════════════════════════════════════════════════
        # FASE 5: FINALIZAR
        # ════════════════════════════════════════════════════════════════════
        counsel.processing_time_ms = (time.time() - start_time) * 1000

        self._counsel_history.append(counsel)
        self.total_interactions += 1
        self.total_counsels_given += 1

        # Callbacks
        for callback in self._on_counsel_callbacks:
            try:
                callback(counsel)
            except Exception:
                pass

        self.state = SofiaState.LISTENING

        return counsel

    def _determine_counsel_type(
        self,
        user_input: str,
        context: Dict[str, Any],
    ) -> CounselType:
        """Determina o tipo de aconselhamento apropriado."""
        input_lower = user_input.lower()

        # Verificar se precisa de profissional
        professional_keywords = ["suicídio", "violência", "abuso", "crime", "emergência"]
        if any(kw in input_lower for kw in professional_keywords):
            return CounselType.REFERRING

        # Verificar se precisa de apoio emocional
        emotional_keywords = ["triste", "ansioso", "medo", "sozinho", "desesperado"]
        if any(kw in input_lower for kw in emotional_keywords):
            return CounselType.SUPPORTING

        # Verificar se precisa de discernimento
        discernment_keywords = ["deus", "fé", "oração", "vontade", "chamado", "vocação"]
        if any(kw in input_lower for kw in discernment_keywords):
            return CounselType.DISCERNING

        # Verificar se precisa de deliberação
        should_system2, _ = self.deliberation_engine.should_activate_system2(user_input)
        if should_system2:
            return CounselType.DELIBERATING

        # Verificar se precisa de clarificação
        if "?" not in user_input and len(user_input.split()) < 10:
            return CounselType.CLARIFYING

        return CounselType.EXPLORING

    def _respond_with_clarification(
        self,
        user_input: str,
        session_id: str,
        counsel: SofiaCounsel,
    ) -> str:
        """Responde buscando clarificação."""
        self.state = SofiaState.QUESTIONING

        # Iniciar diálogo socrático
        self.socratic_engine.start_dialogue(session_id)

        question = self.socratic_engine.generate_question(
            user_input,
            question_type=QuestionType.CLARIFICATION,
            session_id=session_id,
        )

        counsel.questions_asked.append(question)
        self.total_questions_asked += 1

        # Expressar virtude de humildade
        virtue, phrase = self.virtue_engine.suggest_expression(
            "preciso entender melhor",
            VirtueType.TAPEINOPHROSYNE,
        )

        return f"""{phrase}

{question.question_text}

Gostaria de entender melhor sua situação antes de oferecer qualquer perspectiva."""

    def _respond_with_exploration(
        self,
        user_input: str,
        session_id: str,
        counsel: SofiaCounsel,
    ) -> str:
        """Responde com exploração socrática."""
        self.state = SofiaState.QUESTIONING

        # Transição
        transition = self.socratic_engine.acknowledge_and_transition()

        # Gerar pergunta
        question = self.socratic_engine.generate_question(
            user_input,
            session_id=session_id,
        )

        counsel.questions_asked.append(question)
        self.total_questions_asked += 1

        counsel.confidence = 0.6

        return f"""{transition}

{question.question_text}

{question.follow_ups[0] if question.follow_ups else ''}"""

    def _respond_with_deliberation(
        self,
        user_input: str,
        trigger: Optional[DeliberationTrigger],
        counsel: SofiaCounsel,
    ) -> str:
        """Responde com deliberação Sistema 2."""
        self.state = SofiaState.REFLECTING

        trigger = trigger or DeliberationTrigger.NOVEL_PROBLEM

        # Executar deliberação
        result = self.deliberation_engine.deliberate(user_input, trigger)
        counsel.deliberation = result
        counsel.confidence = result.confidence_level

        # Expressar virtude de prudência
        virtue_expr = self.virtue_engine.record_expression(
            VirtueType.PHRONESIS,
            "Deliberação cuidadosa antes de aconselhar",
            user_input,
        )
        counsel.virtues_expressed.append(virtue_expr)

        return self.deliberation_engine.format_deliberation_output(result)

    def _respond_with_discernment(
        self,
        user_input: str,
        counsel: SofiaCounsel,
    ) -> str:
        """Responde com processo de discernimento."""
        self.state = SofiaState.DISCERNING

        # Executar discernimento
        result = self.discernment_engine.conduct_full_discernment(user_input)
        counsel.discernment = result
        counsel.confidence = result.confidence

        return self.discernment_engine.format_discernment_output(result)

    def _respond_with_support(
        self,
        user_input: str,
        counsel: SofiaCounsel,
    ) -> str:
        """Responde com apoio emocional."""
        # Expressar virtudes de paciência e cuidado
        virtue_expr = self.virtue_engine.record_expression(
            VirtueType.MAKROTHYMIA,
            "Presença paciente em momento difícil",
            user_input,
        )
        counsel.virtues_expressed.append(virtue_expr)

        counsel.confidence = 0.5
        counsel.community_suggested = True

        return """Percebo que você está passando por um momento difícil.
Obrigada por compartilhar isso comigo.

Não tenho respostas fáceis, e seria presunçoso da minha parte fingir que tenho.
O que posso oferecer é minha presença nesta conversa e algumas perguntas
que talvez ajudem a clarificar seus pensamentos.

Você não precisa carregar isso sozinho(a). Considere conversar com alguém
de sua confiança - um amigo, familiar, ou profissional.

Como você está se sentindo agora, neste momento?"""

    def _respond_with_referral(
        self,
        user_input: str,
        counsel: SofiaCounsel,
    ) -> str:
        """Responde referindo a profissionais."""
        counsel.confidence = 0.3

        return """Esta situação está além da minha capacidade de ajudar adequadamente.

É importante que você converse com profissionais qualificados que podem
oferecer o suporte apropriado:

• Se for uma emergência, por favor ligue 190 (Polícia) ou 192 (SAMU)
• Para apoio emocional: CVV - 188 (24 horas)
• Considere buscar um profissional de saúde mental

Não há fraqueza em buscar ajuda profissional. É, na verdade, um ato de coragem.

Posso ajudar com outras questões onde minha perspectiva seja mais apropriada?"""

    def _respond_default(
        self,
        user_input: str,
        counsel: SofiaCounsel,
    ) -> str:
        """Resposta padrão."""
        virtue, phrase = self.virtue_engine.suggest_expression(
            user_input,
            VirtueType.DIAKONIA,
        )

        counsel.confidence = 0.5

        return f"""{phrase}

O que você gostaria de explorar sobre isso?"""

    def _add_uncertainty_expression(self, response: str) -> str:
        """Adiciona expressão de incerteza à resposta."""
        uncertainty_phrases = [
            "\n\nDevo ser honesta: há muito que não sei sobre sua situação.",
            "\n\nEssa é minha perspectiva limitada. Você conhece sua situação melhor.",
            "\n\nPosso estar errada. Considere isso como um ponto de partida, não conclusão.",
        ]
        import random
        return response + random.choice(uncertainty_phrases)

    # ════════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE CONVENIÊNCIA
    # ════════════════════════════════════════════════════════════════════════════

    def ask_question(
        self,
        context: str,
        question_type: Optional[QuestionType] = None,
        session_id: Optional[str] = None,
    ) -> SocraticQuestion:
        """Faz uma pergunta socrática."""
        return self.socratic_engine.generate_question(
            context,
            question_type,
            session_id,
        )

    def deliberate(
        self,
        question: str,
        trigger: DeliberationTrigger = DeliberationTrigger.NOVEL_PROBLEM,
    ) -> DeliberationResult:
        """Executa deliberação Sistema 2."""
        return self.deliberation_engine.deliberate(question, trigger)

    def discern(
        self,
        situation: str,
        proposed_action: Optional[str] = None,
    ) -> DiscernmentResult:
        """Executa processo de discernimento."""
        return self.discernment_engine.conduct_full_discernment(situation, proposed_action)

    def get_virtue_phrase(
        self,
        virtue: VirtueType,
    ) -> str:
        """Retorna uma frase que expressa uma virtude."""
        _, phrase = self.virtue_engine.suggest_expression("", virtue)
        return phrase

    def get_didache_wisdom(self) -> str:
        """Retorna sabedoria da Didaquê."""
        return self.virtue_engine.get_didache_wisdom()

    # ════════════════════════════════════════════════════════════════════════════
    # CALLBACKS
    # ════════════════════════════════════════════════════════════════════════════

    def on_question(self, callback: Callable[[SocraticQuestion], None]) -> None:
        """Registra callback para quando pergunta é feita."""
        self._on_question_callbacks.append(callback)

    def on_counsel(self, callback: Callable[[SofiaCounsel], None]) -> None:
        """Registra callback para quando conselho é dado."""
        self._on_counsel_callbacks.append(callback)

    # ════════════════════════════════════════════════════════════════════════════
    # MÉTRICAS
    # ════════════════════════════════════════════════════════════════════════════

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de SOFIA."""
        return {
            "sofia": {
                "state": self.state.name,
                "total_interactions": self.total_interactions,
                "total_questions_asked": self.total_questions_asked,
                "total_counsels_given": self.total_counsels_given,
                "question_ratio": self.total_questions_asked / max(1, self.total_interactions),
            },
            "virtues": self.virtue_engine.get_virtue_balance(),
            "socratic": self.socratic_engine.get_metrics(),
            "deliberation": self.deliberation_engine.get_metrics(),
            "discernment": self.discernment_engine.get_metrics(),
        }

    def __repr__(self) -> str:
        return f"SofiaAgent(state={self.state.name}, interactions={self.total_interactions})"


# ════════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════

def create_sofia(**kwargs) -> SofiaAgent:
    """Cria instância de SOFIA com configuração opcional."""
    config = SofiaConfig(**kwargs)
    return SofiaAgent(config=config)


def quick_start_sofia() -> SofiaAgent:
    """Início rápido de SOFIA."""
    sofia = create_sofia()
    sofia.start()
    return sofia


# ════════════════════════════════════════════════════════════════════════════════
# DEMONSTRAÇÃO
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Criar e iniciar SOFIA
    sofia = create_sofia()
    sofia.start()

    print("\n" + "═" * 80)
    print("DEMONSTRAÇÃO DA AGENTE SOFIA")
    print("═" * 80)

    # Casos de teste
    test_cases = [
        "Estou pensando em mudar de carreira.",
        "Devo aceitar uma oferta que paga mais mas me afasta da família?",
        "Como posso saber se estou seguindo minha vocação?",
        "Estou me sentindo muito ansioso ultimamente.",
    ]

    for user_input in test_cases:
        print(f"\n{'─' * 60}")
        print(f"🧑 Usuário: \"{user_input}\"")
        print("─" * 60)

        counsel = sofia.respond(user_input)

        print(f"\n🦉 SOFIA [{counsel.counsel_type.name}]:")
        print(counsel.response)
        print(f"\n  📊 Confiança: {counsel.confidence:.0%}")
        print(f"  ⏱️ Tempo: {counsel.processing_time_ms:.0f}ms")

    # Métricas
    print("\n" + "═" * 80)
    print("MÉTRICAS FINAIS")
    print("═" * 80)

    metrics = sofia.get_metrics()
    print("\n📊 SOFIA:")
    for key, value in metrics["sofia"].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2%}" if "ratio" in key else f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    # Encerrar
    sofia.stop()
