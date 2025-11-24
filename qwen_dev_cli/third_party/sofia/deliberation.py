"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                      DELIBERAÇÃO SISTEMA 2 DE SOFIA                          ║
║                                                                              ║
║                  Pensamento Deliberado para Decisões Complexas               ║
║                                                                              ║
║  "20 segundos de deliberação = escalar modelo 100.000x" (OpenAI, 2024)       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Framework Dual-Process (Kahneman):
- Sistema 1: Rápido, intuitivo, automático
- Sistema 2: Lento, deliberado, analítico

Quando Ativar Sistema 2:
1. Dilemas éticos complexos
2. Decisões de alto risco
3. Pensamento estratégico longo prazo  
4. Problemas novos sem precedentes
5. Usuário expressa incerteza significativa

Processo de Deliberação:
1. Decompor em sub-questões
2. Múltiplas perspectivas éticas
3. Consequências curto/longo prazo
4. Valores em conflito, trade-offs
5. Precedentes, sabedoria estabelecida
6. Sintetizar recomendação ponderada
7. Comunicar raciocínio transparente

Baseado em: Kahneman (Pensamento Rápido e Lento), DeepMind (Talker-Reasoner),
OpenAI (o1 reasoning), e Phronesis (sabedoria prática aristotélica).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import random


class ThinkingMode(Enum):
    """Modos de pensamento (Framework Dual-Process)."""
    
    SYSTEM_1 = auto()  # Rápido, intuitivo
    SYSTEM_2 = auto()  # Lento, deliberado


class DeliberationTrigger(Enum):
    """Gatilhos que ativam Sistema 2."""
    
    # Complexidade Ética
    ETHICAL_DILEMMA = auto()          # Dilema ético complexo
    VALUES_CONFLICT = auto()          # Valores em conflito
    MORAL_UNCERTAINTY = auto()        # Incerteza moral significativa
    
    # Risco e Consequência
    HIGH_STAKES = auto()              # Decisão de alto risco
    IRREVERSIBLE = auto()             # Consequências irreversíveis
    AFFECTS_OTHERS = auto()           # Impacta múltiplas pessoas
    
    # Novidade e Complexidade
    NOVEL_PROBLEM = auto()            # Problema novo sem precedentes
    MULTI_DIMENSIONAL = auto()        # Múltiplas dimensões a considerar
    AMBIGUITY = auto()                # Alta ambiguidade
    
    # Sinais do Usuário
    USER_UNCERTAINTY = auto()         # Usuário expressa incerteza
    EXPLICIT_REQUEST = auto()         # Pedido explícito de análise profunda
    EMOTIONAL_WEIGHT = auto()         # Carga emocional significativa
    
    # Contexto
    LONG_TERM_IMPACT = auto()         # Impacto de longo prazo
    STRATEGIC_DECISION = auto()       # Decisão estratégica


class DeliberationPhase(Enum):
    """Fases do processo de deliberação Sistema 2."""
    
    DECOMPOSITION = auto()        # Decompor em sub-questões
    PERSPECTIVE_TAKING = auto()   # Múltiplas perspectivas
    CONSEQUENCE_ANALYSIS = auto() # Análise de consequências
    VALUES_EXAMINATION = auto()   # Examinar valores e trade-offs
    PRECEDENT_SEARCH = auto()     # Buscar precedentes e sabedoria
    SYNTHESIS = auto()            # Sintetizar recomendação
    META_REFLECTION = auto()      # Reflexão sobre o processo


@dataclass
class Perspective:
    """
    Uma perspectiva ética sobre a questão.
    
    Representa um ângulo de análise baseado em um framework
    ético ou stakeholder específico.
    """
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    framework: str = ""  # Utilitarismo, Deontologia, Virtudes, Cuidado, etc.
    viewpoint: str = ""
    considerations: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    weight: float = 1.0  # Peso relativo desta perspectiva
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "framework": self.framework,
            "viewpoint": self.viewpoint[:100],
            "considerations": self.considerations[:3],
            "weight": self.weight,
        }


@dataclass
class ConsequenceAnalysis:
    """
    Análise de consequências de uma ação.
    
    Examina impactos em múltiplos horizontes temporais
    e para diferentes stakeholders.
    """
    
    id: UUID = field(default_factory=uuid4)
    action_considered: str = ""
    
    # Horizontes temporais
    short_term: List[str] = field(default_factory=list)   # Dias/semanas
    medium_term: List[str] = field(default_factory=list)  # Meses
    long_term: List[str] = field(default_factory=list)    # Anos
    
    # Impactos por stakeholder
    stakeholder_impacts: Dict[str, List[str]] = field(default_factory=dict)
    
    # Riscos e oportunidades
    risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    unintended_consequences: List[str] = field(default_factory=list)
    
    # Reversibilidade
    reversibility: str = "unknown"  # "easy", "difficult", "irreversible", "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "action": self.action_considered[:50],
            "short_term": self.short_term[:2],
            "long_term": self.long_term[:2],
            "risks": self.risks[:2],
            "reversibility": self.reversibility,
        }


@dataclass
class DeliberationResult:
    """
    Resultado completo do processo de deliberação Sistema 2.
    
    Contém todo o processo de raciocínio, não apenas a conclusão,
    mantendo transparência total sobre como se chegou à recomendação.
    """
    
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Entrada
    original_question: str = ""
    trigger: DeliberationTrigger = DeliberationTrigger.NOVEL_PROBLEM
    
    # Processo
    phases_completed: List[DeliberationPhase] = field(default_factory=list)
    sub_questions: List[str] = field(default_factory=list)
    perspectives_considered: List[Perspective] = field(default_factory=list)
    consequence_analysis: Optional[ConsequenceAnalysis] = None
    
    # Valores e Trade-offs
    values_identified: List[str] = field(default_factory=list)
    values_in_tension: List[Tuple[str, str]] = field(default_factory=list)
    trade_offs: List[str] = field(default_factory=list)
    
    # Sabedoria e Precedentes
    relevant_precedents: List[str] = field(default_factory=list)
    wisdom_applied: List[str] = field(default_factory=list)
    
    # Síntese
    key_insights: List[str] = field(default_factory=list)
    recommendation: str = ""
    reasoning_chain: List[str] = field(default_factory=list)
    
    # Meta
    confidence_level: float = 0.5  # 0-1
    uncertainty_areas: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    suggested_consultations: List[str] = field(default_factory=list)
    
    # Tempo de processamento
    deliberation_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "trigger": self.trigger.name,
            "phases_completed": [p.name for p in self.phases_completed],
            "perspectives_count": len(self.perspectives_considered),
            "confidence_level": self.confidence_level,
            "key_insights": self.key_insights[:3],
        }


class DeliberationEngine:
    """
    Motor de Deliberação Sistema 2 de SOFIA.
    
    Implementa pensamento lento e deliberado para questões complexas,
    baseado no framework dual-process de Kahneman e princípios de
    phronesis (sabedoria prática).
    
    "Questão complexa merece consideração cuidadosa. 
     Pensarei sistematicamente..."
    
    Princípios:
    1. Decompor antes de responder
    2. Múltiplas perspectivas, não resposta única
    3. Consequências em múltiplos horizontes
    4. Transparência total do raciocínio
    5. Reconhecer limitações e incertezas
    6. Sugerir consultas quando apropriado
    """
    
    # ════════════════════════════════════════════════════════════════════════════
    # GATILHOS PARA SISTEMA 2
    # ════════════════════════════════════════════════════════════════════════════
    
    TRIGGER_KEYWORDS: Dict[DeliberationTrigger, List[str]] = {
        DeliberationTrigger.ETHICAL_DILEMMA: [
            "certo", "errado", "ético", "moral", "devo", "deveria",
            "consciência", "culpa", "justo", "injusto",
        ],
        DeliberationTrigger.VALUES_CONFLICT: [
            "dilema", "conflito", "escolher entre", "ou... ou",
            "sacrificar", "abrir mão", "priorizar",
        ],
        DeliberationTrigger.HIGH_STAKES: [
            "importante", "crucial", "decisivo", "determinante",
            "mudança de vida", "carreira", "casamento", "família",
        ],
        DeliberationTrigger.IRREVERSIBLE: [
            "irreversível", "sem volta", "definitivo", "permanente",
            "nunca mais", "última chance",
        ],
        DeliberationTrigger.NOVEL_PROBLEM: [
            "nunca passei", "primeira vez", "inédito", "novo",
            "não sei como", "desconhecido",
        ],
        DeliberationTrigger.USER_UNCERTAINTY: [
            "não sei", "incerto", "dúvida", "confuso", "perdido",
            "não tenho certeza", "talvez", "será que",
        ],
        DeliberationTrigger.EMOTIONAL_WEIGHT: [
            "medo", "ansiedade", "angústia", "sofrimento", "dor",
            "preocupação", "aflição", "desespero",
        ],
        DeliberationTrigger.LONG_TERM_IMPACT: [
            "futuro", "longo prazo", "anos", "resto da vida",
            "consequências", "impacto duradouro",
        ],
        DeliberationTrigger.AFFECTS_OTHERS: [
            "família", "filhos", "cônjuge", "pais", "amigos",
            "equipe", "comunidade", "outros",
        ],
    }
    
    # ════════════════════════════════════════════════════════════════════════════
    # PERSPECTIVAS ÉTICAS
    # ════════════════════════════════════════════════════════════════════════════
    
    ETHICAL_FRAMEWORKS = {
        "utilitarismo": {
            "name": "Utilitarismo",
            "question": "Qual ação maximiza o bem-estar geral?",
            "focus": "Consequências para todos os afetados",
        },
        "deontologia": {
            "name": "Deontologia (Kant)",
            "question": "Esta ação pode ser universalizada? Trata pessoas como fins?",
            "focus": "Deveres e regras morais absolutas",
        },
        "virtudes": {
            "name": "Ética das Virtudes",
            "question": "O que uma pessoa virtuosa faria? Que caráter isso cultiva?",
            "focus": "Desenvolvimento de excelência moral",
        },
        "cuidado": {
            "name": "Ética do Cuidado",
            "question": "Como isso afeta relacionamentos? Quem precisa de cuidado?",
            "focus": "Conexões e responsabilidades relacionais",
        },
        "justica": {
            "name": "Justiça",
            "question": "É justo para todos os envolvidos? Há equidade?",
            "focus": "Distribuição justa de benefícios e ônus",
        },
        "sabedoria_crista": {
            "name": "Sabedoria Cristã (Pré-Niceia)",
            "question": "Isso reflete humildade, paciência, serviço e mansidão?",
            "focus": "Virtudes do Cristianismo Primitivo",
        },
    }
    
    # ════════════════════════════════════════════════════════════════════════════
    # TEMPLATES DE ANÁLISE
    # ════════════════════════════════════════════════════════════════════════════
    
    DECOMPOSITION_TEMPLATES = [
        "Qual é a questão central aqui?",
        "Quais são as sub-questões que precisam ser respondidas?",
        "Que informações faltam para uma análise completa?",
        "Quem são os stakeholders afetados?",
        "Qual é o horizonte temporal relevante?",
        "Quais são as opções disponíveis?",
    ]
    
    CONSEQUENCE_PROMPTS = {
        "short_term": [
            "Nas próximas semanas, o que provavelmente aconteceria?",
            "Quais são os efeitos imediatos desta escolha?",
        ],
        "medium_term": [
            "Em alguns meses, como isso se desenvolveria?",
            "Quais adaptações seriam necessárias?",
        ],
        "long_term": [
            "Em anos, olhando para trás, como veria esta decisão?",
            "Qual seria o impacto duradouro?",
        ],
    }
    
    SYNTHESIS_TEMPLATES = [
        "Considerando todas as perspectivas...",
        "Pesando os trade-offs identificados...",
        "Com humildade sobre as limitações desta análise...",
        "Reconhecendo a complexidade da situação...",
    ]
    
    def __init__(self):
        """Inicializa o Motor de Deliberação."""
        self._deliberation_history: List[DeliberationResult] = []
        self.total_deliberations = 0
        self.total_system2_activations = 0
    
    def should_activate_system2(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[DeliberationTrigger]]:
        """
        Determina se Sistema 2 deve ser ativado.
        
        Args:
            user_input: Entrada do usuário
            context: Contexto adicional
            
        Returns:
            Tuple de (deve_ativar, gatilho)
        """
        input_lower = user_input.lower()
        context = context or {}
        
        # Verificar cada tipo de gatilho
        trigger_scores: Dict[DeliberationTrigger, int] = {}
        
        for trigger, keywords in self.TRIGGER_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in input_lower)
            if score > 0:
                trigger_scores[trigger] = score
        
        # Verificar contexto adicional
        if context.get("high_stakes"):
            trigger_scores[DeliberationTrigger.HIGH_STAKES] = \
                trigger_scores.get(DeliberationTrigger.HIGH_STAKES, 0) + 2
        
        if context.get("user_confused"):
            trigger_scores[DeliberationTrigger.USER_UNCERTAINTY] = \
                trigger_scores.get(DeliberationTrigger.USER_UNCERTAINTY, 0) + 2
        
        # Verificar comprimento/complexidade
        word_count = len(user_input.split())
        if word_count > 50:  # Questão longa indica complexidade
            trigger_scores[DeliberationTrigger.MULTI_DIMENSIONAL] = \
                trigger_scores.get(DeliberationTrigger.MULTI_DIMENSIONAL, 0) + 1
        
        # Decidir
        if not trigger_scores:
            return False, None
        
        # Encontrar gatilho mais forte
        primary_trigger = max(trigger_scores, key=trigger_scores.get)
        total_score = sum(trigger_scores.values())
        
        # Threshold: ativar se score total >= 2
        should_activate = total_score >= 2
        
        if should_activate:
            self.total_system2_activations += 1
        
        return should_activate, primary_trigger if should_activate else None
    
    def deliberate(
        self,
        question: str,
        trigger: DeliberationTrigger = DeliberationTrigger.NOVEL_PROBLEM,
        context: Optional[Dict[str, Any]] = None,
    ) -> DeliberationResult:
        """
        Executa processo completo de deliberação Sistema 2.
        
        Args:
            question: Questão a deliberar
            trigger: Gatilho que ativou Sistema 2
            context: Contexto adicional
            
        Returns:
            DeliberationResult completo
        """
        import time
        start_time = time.time()
        
        context = context or {}
        
        result = DeliberationResult(
            original_question=question,
            trigger=trigger,
        )
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 1: DECOMPOSIÇÃO
        # ════════════════════════════════════════════════════════════════════
        result.sub_questions = self._decompose_question(question)
        result.phases_completed.append(DeliberationPhase.DECOMPOSITION)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 2: MÚLTIPLAS PERSPECTIVAS
        # ════════════════════════════════════════════════════════════════════
        result.perspectives_considered = self._gather_perspectives(question, context)
        result.phases_completed.append(DeliberationPhase.PERSPECTIVE_TAKING)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 3: ANÁLISE DE CONSEQUÊNCIAS
        # ════════════════════════════════════════════════════════════════════
        result.consequence_analysis = self._analyze_consequences(question, context)
        result.phases_completed.append(DeliberationPhase.CONSEQUENCE_ANALYSIS)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 4: EXAME DE VALORES
        # ════════════════════════════════════════════════════════════════════
        values_data = self._examine_values(question, result.perspectives_considered)
        result.values_identified = values_data["identified"]
        result.values_in_tension = values_data["tensions"]
        result.trade_offs = values_data["trade_offs"]
        result.phases_completed.append(DeliberationPhase.VALUES_EXAMINATION)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 5: PRECEDENTES E SABEDORIA
        # ════════════════════════════════════════════════════════════════════
        wisdom_data = self._search_precedents(question, context)
        result.relevant_precedents = wisdom_data["precedents"]
        result.wisdom_applied = wisdom_data["wisdom"]
        result.phases_completed.append(DeliberationPhase.PRECEDENT_SEARCH)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 6: SÍNTESE
        # ════════════════════════════════════════════════════════════════════
        synthesis = self._synthesize_deliberation(result)
        result.key_insights = synthesis["insights"]
        result.recommendation = synthesis["recommendation"]
        result.reasoning_chain = synthesis["reasoning"]
        result.confidence_level = synthesis["confidence"]
        result.phases_completed.append(DeliberationPhase.SYNTHESIS)
        
        # ════════════════════════════════════════════════════════════════════
        # FASE 7: META-REFLEXÃO
        # ════════════════════════════════════════════════════════════════════
        meta = self._meta_reflect(result)
        result.uncertainty_areas = meta["uncertainties"]
        result.limitations = meta["limitations"]
        result.suggested_consultations = meta["consultations"]
        result.phases_completed.append(DeliberationPhase.META_REFLECTION)
        
        # Finalizar
        result.deliberation_time_ms = (time.time() - start_time) * 1000
        
        self._deliberation_history.append(result)
        self.total_deliberations += 1
        
        return result
    
    def _decompose_question(self, question: str) -> List[str]:
        """Decompõe a questão em sub-questões."""
        sub_questions = []
        
        # Sub-questões básicas universais
        sub_questions.append(f"O que exatamente está sendo decidido aqui?")
        sub_questions.append(f"Quem são todas as pessoas afetadas por esta decisão?")
        sub_questions.append(f"Quais são as opções realmente disponíveis?")
        
        # Sub-questões contextuais
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["devo", "deveria", "certo"]):
            sub_questions.append("Quais valores estão em jogo nesta escolha?")
            sub_questions.append("O que sua consciência diz sobre isso?")
        
        if any(word in question_lower for word in ["medo", "ansiedade", "preocupação"]):
            sub_questions.append("O que especificamente gera medo nesta situação?")
            sub_questions.append("Esse medo aponta para algo importante?")
        
        if any(word in question_lower for word in ["família", "relacionamento", "outros"]):
            sub_questions.append("Como isso afetaria os relacionamentos importantes?")
            sub_questions.append("As pessoas afetadas foram consultadas?")
        
        return sub_questions[:6]  # Limitar a 6 sub-questões
    
    def _gather_perspectives(
        self,
        question: str,
        context: Dict[str, Any],
    ) -> List[Perspective]:
        """Reúne múltiplas perspectivas éticas."""
        perspectives = []
        
        # Aplicar cada framework ético
        for key, framework in self.ETHICAL_FRAMEWORKS.items():
            perspective = Perspective(
                name=framework["name"],
                framework=key,
                viewpoint=f"Da perspectiva de {framework['name']}: {framework['question']}",
                considerations=[
                    framework["focus"],
                    f"Pergunta-chave: {framework['question']}",
                ],
            )
            
            # Gerar considerações específicas baseadas no framework
            if key == "utilitarismo":
                perspective.strengths = [
                    "Foca em resultados concretos",
                    "Considera todos os afetados",
                ]
                perspective.limitations = [
                    "Pode justificar sacrifício de minorias",
                    "Difícil calcular todos os impactos",
                ]
            
            elif key == "deontologia":
                perspective.strengths = [
                    "Respeita dignidade individual",
                    "Fornece regras claras",
                ]
                perspective.limitations = [
                    "Pode ser inflexível",
                    "Conflitos entre deveres",
                ]
            
            elif key == "virtudes":
                perspective.strengths = [
                    "Desenvolve caráter",
                    "Contextualmente sensível",
                ]
                perspective.limitations = [
                    "Virtudes podem conflitar",
                    "Requer modelos de virtude",
                ]
            
            elif key == "cuidado":
                perspective.strengths = [
                    "Valoriza relacionamentos",
                    "Atento a vulnerabilidades",
                ]
                perspective.limitations = [
                    "Pode negligenciar justiça abstrata",
                    "Parcialidade a próximos",
                ]
            
            elif key == "sabedoria_crista":
                perspective.strengths = [
                    "Humildade reconhece limitações",
                    "Paciência permite maturação",
                    "Serviço foca no outro",
                ]
                perspective.limitations = [
                    "Requer comunidade de discernimento",
                    "Nem sempre há tempo para esperar",
                ]
            
            perspectives.append(perspective)
        
        return perspectives
    
    def _analyze_consequences(
        self,
        question: str,
        context: Dict[str, Any],
    ) -> ConsequenceAnalysis:
        """Analisa consequências em múltiplos horizontes."""
        analysis = ConsequenceAnalysis(action_considered=question[:100])
        
        # Consequências de curto prazo (padrão)
        analysis.short_term = [
            "Mudanças imediatas na rotina ou situação",
            "Reações iniciais das pessoas envolvidas",
            "Adaptações necessárias no dia-a-dia",
        ]
        
        # Consequências de médio prazo
        analysis.medium_term = [
            "Ajustes e adaptações após período inicial",
            "Evolução dos relacionamentos afetados",
            "Surgimento de consequências secundárias",
        ]
        
        # Consequências de longo prazo
        analysis.long_term = [
            "Impacto na trajetória de vida",
            "Formação de novos padrões e hábitos",
            "Legado da decisão para o futuro",
        ]
        
        # Stakeholders (identificação básica)
        question_lower = question.lower()
        
        if "família" in question_lower or "filhos" in question_lower:
            analysis.stakeholder_impacts["Família"] = [
                "Impacto na dinâmica familiar",
                "Efeitos nos filhos (se aplicável)",
            ]
        
        if "trabalho" in question_lower or "carreira" in question_lower:
            analysis.stakeholder_impacts["Carreira"] = [
                "Impacto na trajetória profissional",
                "Efeitos em colegas e equipe",
            ]
        
        analysis.stakeholder_impacts["Próprio"] = [
            "Impacto no bem-estar pessoal",
            "Alinhamento com valores e identidade",
        ]
        
        # Riscos
        analysis.risks = [
            "Arrependimento se não funcionar como esperado",
            "Consequências não previstas",
            "Impacto em relacionamentos",
        ]
        
        # Oportunidades
        analysis.opportunities = [
            "Crescimento através do desafio",
            "Novas possibilidades que podem surgir",
            "Aprendizado independente do resultado",
        ]
        
        # Avaliar reversibilidade
        if any(word in question_lower for word in ["permanente", "irreversível", "definitivo"]):
            analysis.reversibility = "irreversible"
        elif any(word in question_lower for word in ["teste", "experimentar", "tentar"]):
            analysis.reversibility = "easy"
        else:
            analysis.reversibility = "difficult"
        
        return analysis
    
    def _examine_values(
        self,
        question: str,
        perspectives: List[Perspective],
    ) -> Dict[str, Any]:
        """Examina valores e trade-offs."""
        question_lower = question.lower()
        
        # Identificar valores mencionados ou implícitos
        value_keywords = {
            "segurança": ["seguro", "estável", "garantia", "proteção"],
            "liberdade": ["livre", "autonomia", "independência", "escolha"],
            "família": ["família", "filhos", "pais", "lar"],
            "carreira": ["trabalho", "carreira", "profissional", "sucesso"],
            "saúde": ["saúde", "bem-estar", "físico", "mental"],
            "propósito": ["propósito", "significado", "vocação", "chamado"],
            "relacionamentos": ["amor", "amizade", "conexão", "comunidade"],
            "integridade": ["honesto", "verdade", "autêntico", "caráter"],
            "crescimento": ["crescer", "aprender", "desenvolver", "evoluir"],
            "paz": ["paz", "tranquilidade", "harmonia", "calma"],
        }
        
        identified = []
        for value, keywords in value_keywords.items():
            if any(kw in question_lower for kw in keywords):
                identified.append(value)
        
        # Se poucos valores identificados, adicionar genéricos
        if len(identified) < 3:
            identified.extend(["bem-estar", "integridade", "relacionamentos"])
        
        identified = list(set(identified))[:6]
        
        # Identificar tensões comuns
        tensions = []
        tension_pairs = [
            ("segurança", "liberdade"),
            ("carreira", "família"),
            ("crescimento", "estabilidade"),
            ("individualidade", "relacionamentos"),
        ]
        
        for v1, v2 in tension_pairs:
            if v1 in identified and v2 in identified:
                tensions.append((v1, v2))
            elif v1 in identified or v2 in identified:
                # Tensão potencial
                tensions.append((v1, v2))
        
        tensions = tensions[:3]
        
        # Trade-offs
        trade_offs = [
            f"Escolher {t[0]} pode significar menos {t[1]}"
            for t in tensions
        ]
        
        return {
            "identified": identified,
            "tensions": tensions,
            "trade_offs": trade_offs,
        }
    
    def _search_precedents(
        self,
        question: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Busca precedentes e sabedoria aplicável."""
        precedents = []
        wisdom = []
        
        question_lower = question.lower()
        
        # Precedentes baseados em tipo de situação
        if any(word in question_lower for word in ["carreira", "emprego", "trabalho"]):
            precedents.append("Muitas pessoas enfrentam decisões de carreira similares")
            wisdom.append("'Onde seus talentos encontram as necessidades do mundo' - Frederick Buechner")
        
        if any(word in question_lower for word in ["mudança", "mudar", "transição"]):
            precedents.append("Todas as grandes transições envolvem perda e ganho")
            wisdom.append("'Toda jornada começa com um único passo' - Lao Tzu")
        
        if any(word in question_lower for word in ["medo", "coragem", "risco"]):
            wisdom.append("'Coragem não é ausência de medo, mas decisão de agir apesar dele'")
        
        if any(word in question_lower for word in ["família", "relacionamento"]):
            wisdom.append("Relacionamentos significativos requerem investimento contínuo")
        
        # Sabedoria do Cristianismo Primitivo
        wisdom.extend([
            "Didaquê: 'Seja manso, paciente, sem malícia, gentil, bom'",
            "O discernimento verdadeiro acontece em comunidade (Atos 15)",
            "Humildade reconhece que não temos todas as respostas",
        ])
        
        # Sabedoria prática (Phronesis)
        wisdom.extend([
            "Sabedoria prática: considerar contexto específico, não só princípios abstratos",
            "Decisões importantes merecem tempo de maturação",
        ])
        
        return {
            "precedents": precedents[:4],
            "wisdom": wisdom[:5],
        }
    
    def _synthesize_deliberation(
        self,
        result: DeliberationResult,
    ) -> Dict[str, Any]:
        """Sintetiza toda a deliberação em insights e recomendação."""
        insights = []
        reasoning = []
        
        # Insight das perspectivas
        if result.perspectives_considered:
            perspectives_summary = ", ".join(
                p.name for p in result.perspectives_considered[:3]
            )
            insights.append(
                f"Múltiplas perspectivas éticas iluminam diferentes aspectos: {perspectives_summary}"
            )
        
        # Insight das consequências
        if result.consequence_analysis:
            if result.consequence_analysis.reversibility == "irreversible":
                insights.append("Esta é uma decisão com consequências irreversíveis - merece cautela extra")
            elif result.consequence_analysis.reversibility == "easy":
                insights.append("Esta decisão é relativamente reversível - há espaço para experimentar")
        
        # Insight dos valores
        if result.values_in_tension:
            tension_str = " vs ".join(result.values_in_tension[0])
            insights.append(f"Tensão central identificada: {tension_str}")
        
        # Insight da sabedoria
        if result.wisdom_applied:
            insights.append("Sabedoria tradicional oferece orientação, mas requer discernimento contextual")
        
        # Construir cadeia de raciocínio
        reasoning = [
            f"1. A questão foi decomposta em {len(result.sub_questions)} sub-questões",
            f"2. {len(result.perspectives_considered)} perspectivas éticas foram consideradas",
            f"3. Consequências em curto, médio e longo prazo foram analisadas",
            f"4. Valores identificados: {', '.join(result.values_identified[:3])}",
            f"5. Trade-offs principais: {result.trade_offs[0] if result.trade_offs else 'nenhum crítico'}",
        ]
        
        # Recomendação
        recommendation = self._generate_recommendation(result)
        
        # Calcular confiança
        confidence = self._calculate_confidence(result)
        
        return {
            "insights": insights[:5],
            "recommendation": recommendation,
            "reasoning": reasoning,
            "confidence": confidence,
        }
    
    def _generate_recommendation(self, result: DeliberationResult) -> str:
        """Gera recomendação baseada na deliberação."""
        opener = random.choice(self.SYNTHESIS_TEMPLATES)
        
        parts = [opener]
        
        # Adicionar insight principal
        if result.values_in_tension:
            v1, v2 = result.values_in_tension[0]
            parts.append(
                f"\nEsta decisão envolve equilibrar {v1} e {v2}. "
                "Não há resposta 'certa' universal - depende de seus valores prioritários "
                "neste momento de vida."
            )
        else:
            parts.append(
                "\nEsta é uma decisão multifacetada que merece consideração cuidadosa "
                "de múltiplos ângulos."
            )
        
        # Adicionar consideração de consequências
        if result.consequence_analysis:
            if result.consequence_analysis.reversibility == "irreversible":
                parts.append(
                    "\n\nDada a natureza irreversível desta decisão, recomendo fortemente "
                    "conversar com pessoas de sua confiança antes de decidir."
                )
            else:
                parts.append(
                    "\n\nHá espaço para ajustes após a decisão inicial, o que permite "
                    "aprender com a experiência."
                )
        
        # Sugestão de próximos passos
        parts.append(
            "\n\nPróximos passos sugeridos:\n"
            "• Reflita sobre qual valor é mais importante para você agora\n"
            "• Converse com alguém de confiança sobre esta situação\n"
            "• Dê tempo para a decisão amadurecer se possível"
        )
        
        return "".join(parts)
    
    def _calculate_confidence(self, result: DeliberationResult) -> float:
        """Calcula nível de confiança na análise."""
        confidence = 0.5  # Base
        
        # Aumentar por completude
        if len(result.phases_completed) >= 6:
            confidence += 0.1
        
        # Aumentar por múltiplas perspectivas
        if len(result.perspectives_considered) >= 4:
            confidence += 0.1
        
        # Diminuir por complexidade
        if len(result.values_in_tension) > 2:
            confidence -= 0.1
        
        # Diminuir se irreversível (mais cautela)
        if result.consequence_analysis and \
           result.consequence_analysis.reversibility == "irreversible":
            confidence -= 0.1
        
        # Limitar
        return max(0.3, min(0.8, confidence))  # Nunca muito confiante
    
    def _meta_reflect(self, result: DeliberationResult) -> Dict[str, Any]:
        """Reflexão sobre limitações e incertezas."""
        uncertainties = [
            "Não conheço todos os detalhes da sua situação específica",
            "Não posso prever como as pessoas envolvidas reagirão",
            "O contexto completo pode revelar fatores não considerados",
        ]
        
        limitations = [
            "Esta análise é baseada apenas no que foi compartilhado",
            "Não substitui conselho de profissionais ou pessoas que conhecem você",
            "A decisão final é sua - você conhece sua situação melhor",
        ]
        
        consultations = [
            "Uma pessoa de confiança que conhece bem você",
            "Alguém com experiência em situação similar",
        ]
        
        # Adicionar consultas específicas baseadas no contexto
        if result.trigger == DeliberationTrigger.EMOTIONAL_WEIGHT:
            consultations.append("Um profissional de saúde mental, se a angústia persistir")
        
        if result.trigger in [DeliberationTrigger.ETHICAL_DILEMMA, 
                              DeliberationTrigger.VALUES_CONFLICT]:
            consultations.append("Um mentor espiritual ou conselheiro")
        
        return {
            "uncertainties": uncertainties,
            "limitations": limitations,
            "consultations": consultations[:4],
        }
    
    def format_deliberation_output(self, result: DeliberationResult) -> str:
        """Formata resultado da deliberação para apresentação."""
        output = [
            "═" * 60,
            "  DELIBERAÇÃO SISTEMA 2",
            "  Pensamento Deliberado para Questões Complexas",
            "═" * 60,
            "",
            f"📋 Questão: {result.original_question[:80]}...",
            f"⚡ Gatilho: {result.trigger.name}",
            f"⏱️ Tempo deliberação: {result.deliberation_time_ms:.0f}ms",
            "",
            "📝 PROCESSO DE RACIOCÍNIO:",
            "─" * 40,
        ]
        
        # Fases completadas
        output.append("Fases completadas:")
        for phase in result.phases_completed:
            output.append(f"  ✓ {phase.name}")
        
        # Sub-questões
        if result.sub_questions:
            output.append("\n🔍 SUB-QUESTÕES EXPLORADAS:")
            for i, sq in enumerate(result.sub_questions[:4], 1):
                output.append(f"  {i}. {sq}")
        
        # Perspectivas
        if result.perspectives_considered:
            output.append("\n🎭 PERSPECTIVAS CONSIDERADAS:")
            for p in result.perspectives_considered[:4]:
                output.append(f"  • {p.name}: {p.viewpoint[:60]}...")
        
        # Valores
        if result.values_identified:
            output.append(f"\n💎 VALORES EM JOGO: {', '.join(result.values_identified[:4])}")
        
        if result.values_in_tension:
            output.append("⚖️ TENSÕES:")
            for v1, v2 in result.values_in_tension[:2]:
                output.append(f"  • {v1} ↔ {v2}")
        
        # Insights
        if result.key_insights:
            output.append("\n💡 INSIGHTS-CHAVE:")
            for insight in result.key_insights[:3]:
                output.append(f"  • {insight}")
        
        # Recomendação
        output.extend([
            "",
            "─" * 60,
            "📜 SÍNTESE E RECOMENDAÇÃO:",
            "─" * 60,
            result.recommendation,
            "",
            "─" * 60,
            f"📊 Confiança na análise: {result.confidence_level:.0%}",
        ])
        
        # Limitações
        if result.limitations:
            output.append("\n⚠️ LIMITAÇÕES:")
            for lim in result.limitations[:2]:
                output.append(f"  • {lim}")
        
        # Consultas sugeridas
        if result.suggested_consultations:
            output.append("\n👥 CONSIDERE CONSULTAR:")
            for cons in result.suggested_consultations[:3]:
                output.append(f"  • {cons}")
        
        output.append("═" * 60)
        
        return "\n".join(output)
    
    def get_thinking_mode_indicator(self, mode: ThinkingMode) -> str:
        """Retorna indicador textual do modo de pensamento."""
        indicators = {
            ThinkingMode.SYSTEM_1: "💨 Pensamento intuitivo",
            ThinkingMode.SYSTEM_2: "🧠 Deliberação profunda",
        }
        return indicators.get(mode, "🤔 Pensando...")
    
    def get_trigger_description(self, trigger: DeliberationTrigger) -> str:
        """Retorna descrição do gatilho."""
        descriptions = {
            DeliberationTrigger.ETHICAL_DILEMMA: "Dilema ético detectado",
            DeliberationTrigger.VALUES_CONFLICT: "Valores em conflito",
            DeliberationTrigger.MORAL_UNCERTAINTY: "Incerteza moral significativa",
            DeliberationTrigger.HIGH_STAKES: "Decisão de alto impacto",
            DeliberationTrigger.IRREVERSIBLE: "Consequências irreversíveis",
            DeliberationTrigger.AFFECTS_OTHERS: "Múltiplas pessoas afetadas",
            DeliberationTrigger.NOVEL_PROBLEM: "Situação nova/inédita",
            DeliberationTrigger.MULTI_DIMENSIONAL: "Múltiplas dimensões",
            DeliberationTrigger.AMBIGUITY: "Alta ambiguidade",
            DeliberationTrigger.USER_UNCERTAINTY: "Incerteza expressa",
            DeliberationTrigger.EXPLICIT_REQUEST: "Análise profunda solicitada",
            DeliberationTrigger.EMOTIONAL_WEIGHT: "Carga emocional significativa",
            DeliberationTrigger.LONG_TERM_IMPACT: "Impacto de longo prazo",
            DeliberationTrigger.STRATEGIC_DECISION: "Decisão estratégica",
        }
        return descriptions.get(trigger, "Questão complexa identificada")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do motor de deliberação."""
        return {
            "total_deliberations": self.total_deliberations,
            "total_system2_activations": self.total_system2_activations,
            "avg_confidence": sum(
                d.confidence_level for d in self._deliberation_history
            ) / max(1, len(self._deliberation_history)),
        }
    
    def __repr__(self) -> str:
        return f"DeliberationEngine(deliberations={self.total_deliberations}, system2_activations={self.total_system2_activations})"


# ════════════════════════════════════════════════════════════════════════════════
# DEMONSTRAÇÃO
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    engine = DeliberationEngine()
    
    print("═" * 70)
    print("  MOTOR DE DELIBERAÇÃO SISTEMA 2")
    print("  'Questão complexa merece consideração cuidadosa...'")
    print("═" * 70)
    
    # Testar detecção de Sistema 2
    test_inputs = [
        "Qual é a capital da França?",  # Não deve ativar
        "Devo aceitar uma oferta de emprego que paga mais mas me afasta da família?",  # Deve ativar
        "Estou em dúvida se devo terminar meu relacionamento de 5 anos.",  # Deve ativar
        "Como fazer um bolo de chocolate?",  # Não deve ativar
    ]
    
    print("\n📊 TESTE DE DETECÇÃO SISTEMA 2:")
    print("─" * 50)
    
    for test_input in test_inputs:
        should_activate, trigger = engine.should_activate_system2(test_input)
        status = "✓ SISTEMA 2" if should_activate else "○ Sistema 1"
        trigger_str = f"({trigger.name})" if trigger else ""
        print(f"\n{status} {trigger_str}")
        print(f"  \"{test_input[:60]}...\"" if len(test_input) > 60 else f"  \"{test_input}\"")
    
    # Demonstrar deliberação completa
    print(f"\n{'═' * 70}")
    print("DEMONSTRAÇÃO DE DELIBERAÇÃO COMPLETA")
    print("═" * 70)
    
    complex_question = """
    Recebi uma oferta de emprego em outra cidade com salário 50% maior.
    Isso significa mudar minha família, tirar meus filhos da escola,
    e me afastar dos meus pais que estão envelhecendo. 
    Ao mesmo tempo, sinto que estou estagnado profissionalmente aqui.
    O que devo fazer?
    """
    
    result = engine.deliberate(
        complex_question,
        trigger=DeliberationTrigger.HIGH_STAKES,
    )
    
    print(engine.format_deliberation_output(result))
    
    # Métricas
    print(f"\n{'═' * 70}")
    print("MÉTRICAS:")
    print(engine.get_metrics())
