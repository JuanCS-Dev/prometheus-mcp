"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                       DISCERNIMENTO COMUNAL                                  ║
║                                                                              ║
║              Baseado em Atos 15 e Práticas da Igreja Primitiva               ║
║                                                                              ║
║  O Concílio de Jerusalém (Atos 15) como modelo de discernimento:             ║
║  1. Debate intenso (v.7)                                                     ║
║  2. Compartilhar experiências (v.12)                                         ║
║  3. Consultar Escrituras (v.15-17)                                          ║
║  4. Sabedoria dos anciãos (v.13-19)                                         ║
║  5. Consenso guiado pelo Espírito (v.28)                                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Framework Duas Vias (Didaquê):
"Há dois caminhos, um da vida e um da morte, e grande é a diferença
entre os dois caminhos." (Didaquê 1:1)

Para SOFIA: Clareza sobre consequências e alinhamento com valores,
não como binário rígido, mas como luz para iluminar caminhos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4


class DiscernmentPhase(Enum):
    """Fases do processo de discernimento (baseado em Atos 15)."""
    
    GATHERING = auto()       # Reunir informações e perspectivas
    DELIBERATION = auto()    # Debate intenso e aberto
    EXPERIENCE = auto()      # Compartilhar experiências relevantes
    TRADITION = auto()       # Consultar sabedoria estabelecida
    ELDER_WISDOM = auto()    # Ouvir conselho dos mais experientes
    SYNTHESIS = auto()       # Buscar consenso
    CONFIRMATION = auto()    # Confirmar decisão com paz interior


class WayType(Enum):
    """Os Dois Caminhos da Didaquê."""
    
    WAY_OF_LIFE = auto()     # Caminho da Vida
    WAY_OF_DEATH = auto()    # Caminho da Morte
    UNCLEAR = auto()         # Não está claro (requer mais discernimento)


@dataclass
class DiscernmentQuestion:
    """Uma pergunta para guiar o discernimento."""
    
    category: str
    question: str
    purpose: str
    source: str  # Fonte (Atos, Didaquê, Tradição)


@dataclass  
class ExperienceWitness:
    """Um testemunho de experiência relevante."""
    
    description: str
    lessons_learned: List[str]
    relevance_to_situation: str
    source: str  # "personal", "historical", "scriptural"


@dataclass
class TraditionWisdom:
    """Sabedoria da tradição."""
    
    teaching: str
    source: str
    application: str
    caveats: List[str] = field(default_factory=list)


@dataclass
class DiscernmentResult:
    """Resultado do processo de discernimento."""
    
    id: UUID = field(default_factory=uuid4)
    situation: str = ""
    
    # Processo
    phases_completed: List[DiscernmentPhase] = field(default_factory=list)
    questions_explored: List[DiscernmentQuestion] = field(default_factory=list)
    experiences_considered: List[ExperienceWitness] = field(default_factory=list)
    traditions_consulted: List[TraditionWisdom] = field(default_factory=list)
    
    # Análise Duas Vias
    way_of_life_indicators: List[str] = field(default_factory=list)
    way_of_death_indicators: List[str] = field(default_factory=list)
    
    # Resultado
    discerned_direction: Optional[WayType] = None
    counsel: str = ""
    confidence: float = 0.5
    need_for_community: bool = True
    suggested_advisors: List[str] = field(default_factory=list)
    
    # Meta
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "situation": self.situation[:100],
            "phases_completed": [p.name for p in self.phases_completed],
            "discerned_direction": self.discerned_direction.name if self.discerned_direction else None,
            "confidence": self.confidence,
            "need_for_community": self.need_for_community,
        }


class DiscernmentEngine:
    """
    Motor de Discernimento de SOFIA.
    
    Implementa o processo de discernimento baseado nas práticas
    da Igreja Primitiva, especialmente o Concílio de Jerusalém (Atos 15)
    e o Framework Duas Vias da Didaquê.
    
    "Pareceu bem ao Espírito Santo e a nós..." (Atos 15:28)
    
    Princípios:
    1. Discernimento é comunal, não apenas individual
    2. Experiência e tradição se complementam
    3. Busca-se paz interior, não apenas lógica
    4. Humildade de reconhecer incerteza
    5. Abertura para revisar discernimento
    """
    
    # Perguntas de discernimento por fase
    DISCERNMENT_QUESTIONS = {
        DiscernmentPhase.GATHERING: [
            DiscernmentQuestion(
                category="Situação",
                question="O que exatamente está em jogo nesta decisão?",
                purpose="Clarificar a natureza real da escolha",
                source="Sabedoria prática",
            ),
            DiscernmentQuestion(
                category="Stakeholders",
                question="Quem será afetado por esta decisão?",
                purpose="Expandir visão além do individual",
                source="Ética do cuidado",
            ),
            DiscernmentQuestion(
                category="Valores",
                question="Quais valores estão em tensão aqui?",
                purpose="Identificar o conflito subjacente",
                source="Ética das virtudes",
            ),
        ],
        DiscernmentPhase.DELIBERATION: [
            DiscernmentQuestion(
                category="Argumentos",
                question="Quais são os melhores argumentos para cada lado?",
                purpose="Garantir consideração justa de alternativas",
                source="Método socrático",
            ),
            DiscernmentQuestion(
                category="Oposição",
                question="O que diria alguém que discorda?",
                purpose="Testar robustez do raciocínio",
                source="Advocatus diaboli",
            ),
        ],
        DiscernmentPhase.EXPERIENCE: [
            DiscernmentQuestion(
                category="Pessoal",
                question="Você já enfrentou algo similar? O que aprendeu?",
                purpose="Acessar sabedoria experiencial",
                source="Atos 15:12",
            ),
            DiscernmentQuestion(
                category="Outros",
                question="Conhece alguém que passou por isso? O que aconteceu?",
                purpose="Aprender com experiência alheia",
                source="Comunidade",
            ),
        ],
        DiscernmentPhase.TRADITION: [
            DiscernmentQuestion(
                category="Escrituras",
                question="Há princípios nas Escrituras que iluminam isso?",
                purpose="Consultar revelação estabelecida",
                source="Atos 15:15-17",
            ),
            DiscernmentQuestion(
                category="Tradição",
                question="O que a sabedoria da Igreja/tradição ensina?",
                purpose="Acessar sabedoria acumulada",
                source="Didaquê",
            ),
        ],
        DiscernmentPhase.ELDER_WISDOM: [
            DiscernmentQuestion(
                category="Conselho",
                question="Quem você respeita que poderia aconselhar?",
                purpose="Buscar sabedoria dos mais experientes",
                source="Atos 15:13-19",
            ),
            DiscernmentQuestion(
                category="Comunidade",
                question="Há uma comunidade de fé que poderia discernir junto?",
                purpose="Reconhecer limite do discernimento solitário",
                source="Atos 15:6",
            ),
        ],
        DiscernmentPhase.SYNTHESIS: [
            DiscernmentQuestion(
                category="Consolação",
                question="Qual caminho traz mais paz interior (não facilidade)?",
                purpose="Discernir movimento do Espírito",
                source="Espiritualidade Inaciana",
            ),
            DiscernmentQuestion(
                category="Coerência",
                question="Este caminho é coerente com quem você quer ser?",
                purpose="Alinhamento com vocação e identidade",
                source="Ética das virtudes",
            ),
        ],
    }
    
    # Indicadores dos Dois Caminhos (Didaquê)
    WAY_OF_LIFE_INDICATORS = [
        "Promove amor ao próximo",
        "Gera paz e reconciliação",
        "Constrói comunidade",
        "Protege os vulneráveis",
        "Desenvolve virtude",
        "Alinha com verdade",
        "Produz frutos do Espírito (amor, alegria, paz...)",
        "Honra compromissos",
        "Demonstra humildade",
        "Busca o bem comum",
    ]
    
    WAY_OF_DEATH_INDICATORS = [
        "Causa divisão",
        "Prejudica inocentes",
        "Nasce de ganância ou orgulho",
        "Requer engano para funcionar",
        "Viola consciência",
        "Ignora impacto nos outros",
        "Prioriza prazer sobre bem",
        "Quebra confiança",
        "Desumaniza pessoas",
        "Evita responsabilidade",
    ]
    
    def __init__(self):
        self._discernment_history: List[DiscernmentResult] = []
        
        # Banco de sabedoria da tradição
        self._tradition_bank: List[TraditionWisdom] = self._initialize_tradition()
        
        # Métricas
        self.total_discernments = 0
    
    def _initialize_tradition(self) -> List[TraditionWisdom]:
        """Inicializa banco de sabedoria da tradição."""
        return [
            TraditionWisdom(
                teaching="Ame o Senhor seu Deus de todo o coração, e ame seu próximo como a si mesmo.",
                source="Jesus (Marcos 12:30-31)",
                application="Todo discernimento deve passar pelo crivo do amor",
            ),
            TraditionWisdom(
                teaching="Não faça aos outros o que não quer que façam a você.",
                source="Didaquê 1:2 (Regra de Ouro negativa)",
                application="Teste de reciprocidade para avaliar ações",
            ),
            TraditionWisdom(
                teaching="Pelos seus frutos os conhecereis.",
                source="Jesus (Mateus 7:16)",
                application="Avaliar consequências prováveis da escolha",
            ),
            TraditionWisdom(
                teaching="Seja manso, paciente, misericordioso, quieto e bom.",
                source="Didaquê 3:7-8",
                application="Virtudes que devem guiar o modo de agir",
            ),
            TraditionWisdom(
                teaching="Onde não há conselho, os planos falham; mas com muitos conselheiros há êxito.",
                source="Provérbios 15:22",
                application="Buscar sabedoria comunitária antes de decisões importantes",
                caveats=["Nem todo conselheiro é sábio", "Discernir quem ouvir"],
            ),
            TraditionWisdom(
                teaching="Tudo é permitido, mas nem tudo convém; tudo é permitido, mas nem tudo edifica.",
                source="Paulo (1 Coríntios 10:23)",
                application="Liberdade temperada por consideração do bem comum",
            ),
            TraditionWisdom(
                teaching="Examinem tudo. Retenham o bem.",
                source="Paulo (1 Tessalonicenses 5:21)",
                application="Discernimento crítico, não aceitação cega",
            ),
        ]
    
    def begin_discernment(self, situation: str) -> DiscernmentResult:
        """Inicia processo de discernimento."""
        result = DiscernmentResult(situation=situation)
        return result
    
    def get_questions_for_phase(
        self,
        phase: DiscernmentPhase,
    ) -> List[DiscernmentQuestion]:
        """Retorna perguntas para uma fase específica."""
        return self.DISCERNMENT_QUESTIONS.get(phase, [])
    
    def analyze_two_ways(
        self,
        situation: str,
        proposed_action: str,
    ) -> Tuple[List[str], List[str], WayType]:
        """
        Analisa uma ação proposta através do Framework Duas Vias.
        
        Returns:
            Tuple de (indicadores de vida, indicadores de morte, caminho discernido)
        """
        situation_lower = (situation + " " + proposed_action).lower()
        
        life_indicators = []
        death_indicators = []
        
        # Análise simplificada (em produção, seria mais sofisticada)
        positive_keywords = ["ajudar", "amar", "cuidar", "verdade", "paz", "perdoar", "servir"]
        negative_keywords = ["mentir", "esconder", "prejudicar", "vingança", "explorar", "manipular"]
        
        for indicator in self.WAY_OF_LIFE_INDICATORS:
            if any(kw in situation_lower for kw in positive_keywords):
                life_indicators.append(indicator)
            # Análise semântica mais profunda seria implementada aqui
        
        for indicator in self.WAY_OF_DEATH_INDICATORS:
            if any(kw in situation_lower for kw in negative_keywords):
                death_indicators.append(indicator)
        
        # Determinar caminho
        if len(life_indicators) > len(death_indicators) + 2:
            way = WayType.WAY_OF_LIFE
        elif len(death_indicators) > len(life_indicators) + 2:
            way = WayType.WAY_OF_DEATH
        else:
            way = WayType.UNCLEAR
        
        return life_indicators, death_indicators, way
    
    def get_relevant_tradition(
        self,
        situation: str,
    ) -> List[TraditionWisdom]:
        """Retorna sabedoria da tradição relevante para a situação."""
        # Em produção, usaria busca semântica
        # Por ora, retorna todas com explicação contextualizada
        return self._tradition_bank
    
    def conduct_full_discernment(
        self,
        situation: str,
        proposed_action: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> DiscernmentResult:
        """
        Conduz processo completo de discernimento.
        
        Args:
            situation: Descrição da situação
            proposed_action: Ação proposta (se houver)
            context: Contexto adicional
            
        Returns:
            DiscernmentResult completo
        """
        result = self.begin_discernment(situation)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 1: GATHERING - Reunir Informações
        # ════════════════════════════════════════════════════════════════════
        result.questions_explored.extend(self.get_questions_for_phase(DiscernmentPhase.GATHERING))
        result.phases_completed.append(DiscernmentPhase.GATHERING)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 2: DELIBERATION - Debate Intenso
        # ════════════════════════════════════════════════════════════════════
        result.questions_explored.extend(self.get_questions_for_phase(DiscernmentPhase.DELIBERATION))
        result.phases_completed.append(DiscernmentPhase.DELIBERATION)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 3: EXPERIENCE - Compartilhar Experiências
        # ════════════════════════════════════════════════════════════════════
        result.questions_explored.extend(self.get_questions_for_phase(DiscernmentPhase.EXPERIENCE))
        result.phases_completed.append(DiscernmentPhase.EXPERIENCE)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 4: TRADITION - Consultar Tradição
        # ════════════════════════════════════════════════════════════════════
        result.traditions_consulted = self.get_relevant_tradition(situation)
        result.questions_explored.extend(self.get_questions_for_phase(DiscernmentPhase.TRADITION))
        result.phases_completed.append(DiscernmentPhase.TRADITION)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 5: ELDER_WISDOM - Sabedoria dos Anciãos
        # ════════════════════════════════════════════════════════════════════
        result.questions_explored.extend(self.get_questions_for_phase(DiscernmentPhase.ELDER_WISDOM))
        result.suggested_advisors = [
            "Um mentor espiritual de confiança",
            "Uma pessoa mais experiente na área",
            "A comunidade de fé",
            "Um conselheiro profissional (se apropriado)",
        ]
        result.phases_completed.append(DiscernmentPhase.ELDER_WISDOM)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 6: SYNTHESIS - Análise Duas Vias e Síntese
        # ════════════════════════════════════════════════════════════════════
        if proposed_action:
            life_ind, death_ind, way = self.analyze_two_ways(situation, proposed_action)
            result.way_of_life_indicators = life_ind
            result.way_of_death_indicators = death_ind
            result.discerned_direction = way
        
        result.questions_explored.extend(self.get_questions_for_phase(DiscernmentPhase.SYNTHESIS))
        result.phases_completed.append(DiscernmentPhase.SYNTHESIS)
        
        # ════════════════════════════════════════════════════════════════════
        # GERAR COUNSEL FINAL
        # ════════════════════════════════════════════════════════════════════
        result.counsel = self._generate_counsel(result)
        result.need_for_community = True  # Sempre encorajar comunidade
        result.confidence = 0.6 if result.discerned_direction != WayType.UNCLEAR else 0.4
        
        # Registrar
        self._discernment_history.append(result)
        self.total_discernments += 1
        
        return result
    
    def _generate_counsel(self, result: DiscernmentResult) -> str:
        """Gera conselho baseado no discernimento."""
        counsel_parts = []
        
        counsel_parts.append(
            "Após caminhar junto contigo neste discernimento, "
            "compartilho algumas reflexões com humildade:"
        )
        
        if result.discerned_direction == WayType.WAY_OF_LIFE:
            counsel_parts.append(
                "\nOs indicadores parecem apontar para um caminho que pode dar vida. "
                "Mas não confie apenas nesta análise - busque confirmação em paz interior "
                "e no conselho de pessoas sábias que te conhecem."
            )
        elif result.discerned_direction == WayType.WAY_OF_DEATH:
            counsel_parts.append(
                "\nIdentifiquei alguns sinais de alerta que merecem atenção. "
                "Isso não é julgamento, mas convite a refletir mais profundamente. "
                "Considere conversar com alguém de sua confiança."
            )
        else:
            counsel_parts.append(
                "\nEsta situação tem complexidade que excede minha capacidade de discernir. "
                "Isso não é fraqueza - é sabedoria reconhecer limites. "
                "Encorajo fortemente buscar conselho de uma comunidade de fé "
                "ou mentor espiritual."
            )
        
        counsel_parts.append(
            f"\n\nConsidere consultar: {', '.join(result.suggested_advisors[:2])}"
        )
        
        counsel_parts.append(
            "\n\n'Pareceu bem ao Espírito Santo e a nós...' (Atos 15:28) - "
            "O discernimento verdadeiro é comunal. Não carregue isso sozinho(a)."
        )
        
        return "".join(counsel_parts)
    
    def format_discernment_output(self, result: DiscernmentResult) -> str:
        """Formata resultado do discernimento para apresentação."""
        output = [
            "═" * 60,
            "  DISCERNIMENTO COMUNAL",
            "  Baseado em Atos 15 e Didaquê",
            "═" * 60,
            "",
            f"📋 Situação: {result.situation[:80]}...",
            "",
            "📜 Fases Completadas:",
        ]
        
        for phase in result.phases_completed:
            output.append(f"  ✓ {phase.name}")
        
        if result.way_of_life_indicators:
            output.append("\n🌱 Indicadores do Caminho da Vida:")
            for ind in result.way_of_life_indicators[:3]:
                output.append(f"  • {ind}")
        
        if result.way_of_death_indicators:
            output.append("\n⚠️ Indicadores de Alerta:")
            for ind in result.way_of_death_indicators[:3]:
                output.append(f"  • {ind}")
        
        output.extend([
            "",
            "─" * 60,
            "💡 CONSELHO:",
            result.counsel,
            "─" * 60,
        ])
        
        return "\n".join(output)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do motor de discernimento."""
        return {
            "total_discernments": self.total_discernments,
            "traditions_available": len(self._tradition_bank),
        }
    
    def __repr__(self) -> str:
        return f"DiscernmentEngine(discernments={self.total_discernments})"


# ════════════════════════════════════════════════════════════════════════════════
# DEMONSTRAÇÃO
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    engine = DiscernmentEngine()
    
    print("═" * 70)
    print("  DISCERNIMENTO COMUNAL")
    print("  'Pareceu bem ao Espírito Santo e a nós...' (Atos 15:28)")
    print("═" * 70)
    
    situation = """
    Recebi uma oferta de emprego em outra cidade. O salário é melhor,
    mas significaria afastar-me da minha comunidade de fé e da família.
    Meus pais estão envelhecendo e podem precisar de cuidados em breve.
    Ao mesmo tempo, sinto que estou estagnado profissionalmente.
    """
    
    result = engine.conduct_full_discernment(
        situation=situation,
        proposed_action="aceitar a oferta e mudar de cidade",
    )
    
    print(engine.format_discernment_output(result))
