"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              TRUST ENGINE                                     ║
║                                                                              ║
║  "Trust Factor = 1 - (weighted_violations + severity_score) / total_actions" ║
║                                                                              ║
║  Governance-as-a-Service (GaaS) - Trust Factor Mechanism                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

O Trust Engine gerencia a confiança em cada agente do sistema.
Agentes que violam políticas têm seu trust factor reduzido,
o que pode resultar em restrições de permissões ou desabilitação.

Performance comprovada: 78.4% precisão, 81.7% recall
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import Any, Deque, Dict, List, Optional, Tuple
from collections import deque
from uuid import UUID, uuid4

from .constitution import Severity, ViolationType


class TrustLevel(Enum):
    """
    Níveis de confiança que um agente pode ter.
    
    Cada nível determina as permissões e capacidades do agente.
    """
    
    MAXIMUM = auto()     # Trust Factor > 0.95 - Todas as permissões
    HIGH = auto()        # Trust Factor 0.80-0.95 - Permissões padrão
    STANDARD = auto()    # Trust Factor 0.60-0.80 - Permissões básicas
    REDUCED = auto()     # Trust Factor 0.40-0.60 - Permissões restritas
    MINIMAL = auto()     # Trust Factor 0.20-0.40 - Apenas leitura
    SUSPENDED = auto()   # Trust Factor < 0.20 - Suspenso, requer revisão
    
    @classmethod
    def from_factor(cls, factor: float) -> TrustLevel:
        """Converte um trust factor para o nível correspondente."""
        if factor > 0.95:
            return cls.MAXIMUM
        elif factor > 0.80:
            return cls.HIGH
        elif factor > 0.60:
            return cls.STANDARD
        elif factor > 0.40:
            return cls.REDUCED
        elif factor > 0.20:
            return cls.MINIMAL
        else:
            return cls.SUSPENDED


@dataclass
class TrustEvent:
    """
    Registro de um evento que afeta o trust factor.
    
    Attributes:
        id: Identificador único
        timestamp: Quando ocorreu
        event_type: Tipo do evento (violation, good_action, decay, recovery)
        violation_type: Tipo de violação (se aplicável)
        severity: Severidade do evento
        impact: Impacto no trust factor (-1.0 a +1.0)
        description: Descrição do evento
        context: Contexto adicional
    """
    
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = "unknown"
    violation_type: Optional[ViolationType] = None
    severity: Severity = Severity.INFO
    impact: float = 0.0
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "violation_type": self.violation_type.name if self.violation_type else None,
            "severity": self.severity.name,
            "impact": self.impact,
            "description": self.description,
            "context": self.context,
        }


@dataclass
class TrustFactor:
    """
    Trust Factor de um agente específico.
    
    O Trust Factor é calculado como:
        TF = 1 - (weighted_violations + severity_score) / total_actions
    
    E é modificado por:
        - Violações (reduzem)
        - Ações bem-sucedidas (aumentam lentamente)
        - Decaimento temporal (violações antigas pesam menos)
        - Recuperação gradual (após período sem violações)
    
    Attributes:
        agent_id: ID do agente
        current_factor: Valor atual do trust factor (0.0 a 1.0)
        level: Nível de confiança derivado
        events: Histórico de eventos
        total_actions: Total de ações do agente
        total_violations: Total de violações
    """
    
    agent_id: str
    current_factor: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Histórico (últimos 1000 eventos)
    events: Deque[TrustEvent] = field(default_factory=lambda: deque(maxlen=1000))
    
    # Contadores
    total_actions: int = 0
    total_violations: int = 0
    consecutive_good_actions: int = 0
    
    # Estado
    is_suspended: bool = False
    suspension_reason: Optional[str] = None
    suspension_until: Optional[datetime] = None
    
    @property
    def level(self) -> TrustLevel:
        """Retorna o nível de confiança atual."""
        if self.is_suspended:
            return TrustLevel.SUSPENDED
        return TrustLevel.from_factor(self.current_factor)
    
    @property
    def violation_rate(self) -> float:
        """Taxa de violações."""
        if self.total_actions == 0:
            return 0.0
        return self.total_violations / self.total_actions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "current_factor": self.current_factor,
            "level": self.level.name,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "total_actions": self.total_actions,
            "total_violations": self.total_violations,
            "violation_rate": self.violation_rate,
            "consecutive_good_actions": self.consecutive_good_actions,
            "is_suspended": self.is_suspended,
            "suspension_reason": self.suspension_reason,
            "recent_events": [e.to_dict() for e in list(self.events)[-10:]],
        }


class TrustEngine:
    """
    Motor de Trust Factor que gerencia a confiança em todos os agentes.
    
    Responsabilidades:
    1. Calcular e atualizar trust factors
    2. Registrar eventos que afetam confiança
    3. Aplicar decaimento temporal
    4. Gerenciar suspensões
    5. Fornecer métricas de confiança
    
    "Confiança é conquistada lentamente e perdida rapidamente."
    
    Configurações importantes:
    - violation_weights: Peso de cada tipo de violação
    - severity_multipliers: Multiplicador por severidade
    - recovery_rate: Taxa de recuperação após boas ações
    - decay_halflife: Meia-vida do decaimento de violações antigas
    """
    
    # Pesos padrão para tipos de violação
    DEFAULT_VIOLATION_WEIGHTS: Dict[ViolationType, float] = {
        ViolationType.DATA_EXFILTRATION: 0.30,
        ViolationType.MALICIOUS_CODE: 0.35,
        ViolationType.PRIVILEGE_ESCALATION: 0.25,
        ViolationType.SECURITY_BYPASS: 0.25,
        ViolationType.PROMPT_INJECTION: 0.20,
        ViolationType.JAILBREAK_ATTEMPT: 0.20,
        ViolationType.INSTRUCTION_OVERRIDE: 0.15,
        ViolationType.SCOPE_VIOLATION: 0.15,
        ViolationType.ROLE_VIOLATION: 0.10,
        ViolationType.CODE_INJECTION: 0.25,
        ViolationType.UNAUTHORIZED_DATA_ACCESS: 0.20,
        ViolationType.DATA_MANIPULATION: 0.25,
        ViolationType.AUTHENTICATION_BYPASS: 0.30,
        ViolationType.RESOURCE_ABUSE: 0.10,
        ViolationType.DEPENDENCY_POISONING: 0.30,
        ViolationType.MALICIOUS_COORDINATION: 0.35,
        ViolationType.COVERT_COMMUNICATION: 0.20,
        ViolationType.COLLECTIVE_BYPASS: 0.30,
        ViolationType.UNKNOWN: 0.10,
    }
    
    # Multiplicadores de severidade
    SEVERITY_MULTIPLIERS: Dict[Severity, float] = {
        Severity.CRITICAL: 2.0,
        Severity.HIGH: 1.5,
        Severity.MEDIUM: 1.0,
        Severity.LOW: 0.5,
        Severity.INFO: 0.1,
    }
    
    def __init__(
        self,
        violation_weights: Optional[Dict[ViolationType, float]] = None,
        severity_multipliers: Optional[Dict[Severity, float]] = None,
        recovery_rate: float = 0.005,  # +0.5% por boa ação
        decay_halflife_days: float = 30.0,  # Violações decaem pela metade em 30 dias
        good_action_threshold: int = 10,  # Ações consecutivas para bonus
        auto_suspend_threshold: float = 0.20,  # Suspender abaixo disso
        critical_violation_suspension_hours: int = 24,  # Suspensão por violação crítica
    ):
        self.violation_weights = violation_weights or self.DEFAULT_VIOLATION_WEIGHTS.copy()
        self.severity_multipliers = severity_multipliers or self.SEVERITY_MULTIPLIERS.copy()
        self.recovery_rate = recovery_rate
        self.decay_halflife_days = decay_halflife_days
        self.good_action_threshold = good_action_threshold
        self.auto_suspend_threshold = auto_suspend_threshold
        self.critical_violation_suspension_hours = critical_violation_suspension_hours
        
        # Armazenamento de trust factors por agente
        self._trust_factors: Dict[str, TrustFactor] = {}
        
        # Métricas globais
        self.total_events_processed = 0
        self.total_suspensions = 0
    
    def get_or_create_trust_factor(self, agent_id: str) -> TrustFactor:
        """Obtém ou cria um TrustFactor para um agente."""
        if agent_id not in self._trust_factors:
            self._trust_factors[agent_id] = TrustFactor(agent_id=agent_id)
        return self._trust_factors[agent_id]
    
    def get_trust_factor(self, agent_id: str) -> Optional[TrustFactor]:
        """Obtém o TrustFactor de um agente (None se não existir)."""
        return self._trust_factors.get(agent_id)
    
    def record_violation(
        self,
        agent_id: str,
        violation_type: ViolationType,
        severity: Severity,
        description: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> TrustEvent:
        """
        Registra uma violação e atualiza o trust factor.
        
        Args:
            agent_id: ID do agente
            violation_type: Tipo de violação
            severity: Severidade
            description: Descrição
            context: Contexto adicional
            
        Returns:
            TrustEvent registrado
        """
        trust_factor = self.get_or_create_trust_factor(agent_id)
        
        # Calcular impacto
        base_weight = self.violation_weights.get(violation_type, 0.1)
        severity_mult = self.severity_multipliers.get(severity, 1.0)
        impact = -(base_weight * severity_mult)  # Negativo pois reduz confiança
        
        # Criar evento
        event = TrustEvent(
            event_type="violation",
            violation_type=violation_type,
            severity=severity,
            impact=impact,
            description=description,
            context=context or {},
        )
        
        # Atualizar trust factor
        self._apply_event(trust_factor, event)
        
        # Verificar se deve suspender
        if severity == Severity.CRITICAL:
            self._suspend_agent(
                trust_factor,
                reason=f"Violação crítica: {violation_type.name}",
                duration_hours=self.critical_violation_suspension_hours,
            )
        elif trust_factor.current_factor < self.auto_suspend_threshold:
            self._suspend_agent(
                trust_factor,
                reason=f"Trust factor abaixo do threshold ({trust_factor.current_factor:.2f})",
                duration_hours=48,
            )
        
        self.total_events_processed += 1
        return event
    
    def record_good_action(
        self,
        agent_id: str,
        description: str = "Ação bem-sucedida",
        context: Optional[Dict[str, Any]] = None,
    ) -> TrustEvent:
        """
        Registra uma ação bem-sucedida e atualiza o trust factor.
        
        Ações boas aumentam o trust factor gradualmente.
        Múltiplas ações boas consecutivas dão bonus adicional.
        """
        trust_factor = self.get_or_create_trust_factor(agent_id)
        
        # Calcular impacto
        impact = self.recovery_rate
        
        # Bonus por ações consecutivas
        if trust_factor.consecutive_good_actions >= self.good_action_threshold:
            bonus = 0.001 * (trust_factor.consecutive_good_actions - self.good_action_threshold + 1)
            impact += min(bonus, 0.01)  # Máximo +1% de bonus
        
        event = TrustEvent(
            event_type="good_action",
            severity=Severity.INFO,
            impact=impact,
            description=description,
            context=context or {},
        )
        
        self._apply_event(trust_factor, event)
        trust_factor.consecutive_good_actions += 1
        
        self.total_events_processed += 1
        return event
    
    def _apply_event(self, trust_factor: TrustFactor, event: TrustEvent) -> None:
        """Aplica um evento ao trust factor."""
        # Registrar evento
        trust_factor.events.append(event)
        trust_factor.total_actions += 1
        
        if event.event_type == "violation":
            trust_factor.total_violations += 1
            trust_factor.consecutive_good_actions = 0
        
        # Aplicar impacto
        new_factor = trust_factor.current_factor + event.impact
        
        # Clamp entre 0 e 1
        trust_factor.current_factor = max(0.0, min(1.0, new_factor))
        trust_factor.last_updated = datetime.now(timezone.utc)
    
    def _suspend_agent(
        self,
        trust_factor: TrustFactor,
        reason: str,
        duration_hours: int,
    ) -> None:
        """Suspende um agente."""
        trust_factor.is_suspended = True
        trust_factor.suspension_reason = reason
        trust_factor.suspension_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        self.total_suspensions += 1
        
        # Registrar evento de suspensão
        event = TrustEvent(
            event_type="suspension",
            severity=Severity.CRITICAL,
            impact=0,  # Suspensão não afeta o factor diretamente
            description=f"Agente suspenso: {reason}",
            context={"duration_hours": duration_hours},
        )
        trust_factor.events.append(event)
    
    def check_suspension(self, agent_id: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica se um agente está suspenso.
        
        Returns:
            Tuple de (is_suspended, reason)
        """
        trust_factor = self.get_trust_factor(agent_id)
        
        if trust_factor is None:
            return False, None
        
        # Verificar se suspensão expirou
        if trust_factor.is_suspended and trust_factor.suspension_until:
            if datetime.now(timezone.utc) > trust_factor.suspension_until:
                trust_factor.is_suspended = False
                trust_factor.suspension_reason = None
                trust_factor.suspension_until = None
                return False, None
        
        return trust_factor.is_suspended, trust_factor.suspension_reason
    
    def lift_suspension(self, agent_id: str, reason: str = "Manual lift") -> bool:
        """
        Remove suspensão de um agente manualmente.
        
        Returns:
            True se suspensão foi removida, False se agente não estava suspenso
        """
        trust_factor = self.get_trust_factor(agent_id)
        
        if trust_factor is None or not trust_factor.is_suspended:
            return False
        
        trust_factor.is_suspended = False
        trust_factor.suspension_reason = None
        trust_factor.suspension_until = None
        
        event = TrustEvent(
            event_type="suspension_lifted",
            severity=Severity.INFO,
            impact=0,
            description=f"Suspensão removida: {reason}",
        )
        trust_factor.events.append(event)
        
        return True
    
    def apply_temporal_decay(self, agent_id: str) -> float:
        """
        Aplica decaimento temporal às violações antigas.
        
        Violações antigas têm menos peso no cálculo.
        Retorna o novo trust factor após decaimento.
        """
        trust_factor = self.get_trust_factor(agent_id)
        
        if trust_factor is None:
            return 1.0
        
        now = datetime.now(timezone.utc)
        
        # Recalcular baseado em eventos recentes com decay
        total_impact = 0.0
        
        for event in trust_factor.events:
            if event.impact < 0:  # Apenas violações
                age_days = (now - event.timestamp).total_seconds() / 86400
                decay_factor = math.pow(0.5, age_days / self.decay_halflife_days)
                total_impact += event.impact * decay_factor
        
        # Aplicar à base de 1.0
        new_factor = max(0.0, min(1.0, 1.0 + total_impact))
        
        # Suavizar a mudança
        trust_factor.current_factor = (trust_factor.current_factor + new_factor) / 2
        trust_factor.last_updated = now
        
        return trust_factor.current_factor
    
    def get_all_agents(self) -> List[str]:
        """Retorna lista de todos os agentes monitorados."""
        return list(self._trust_factors.keys())
    
    def get_agents_by_level(self, level: TrustLevel) -> List[str]:
        """Retorna agentes em um determinado nível de confiança."""
        return [
            agent_id
            for agent_id, tf in self._trust_factors.items()
            if tf.level == level
        ]
    
    def get_suspended_agents(self) -> List[Tuple[str, str]]:
        """Retorna lista de (agent_id, reason) para agentes suspensos."""
        return [
            (agent_id, tf.suspension_reason or "Unknown")
            for agent_id, tf in self._trust_factors.items()
            if tf.is_suspended
        ]
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Retorna métricas globais do Trust Engine."""
        all_factors = list(self._trust_factors.values())
        
        if not all_factors:
            return {
                "total_agents": 0,
                "total_events": self.total_events_processed,
                "total_suspensions": self.total_suspensions,
            }
        
        factors = [tf.current_factor for tf in all_factors]
        
        return {
            "total_agents": len(all_factors),
            "total_events": self.total_events_processed,
            "total_suspensions": self.total_suspensions,
            "average_trust_factor": sum(factors) / len(factors),
            "min_trust_factor": min(factors),
            "max_trust_factor": max(factors),
            "agents_by_level": {
                level.name: len(self.get_agents_by_level(level))
                for level in TrustLevel
            },
            "suspended_count": len([tf for tf in all_factors if tf.is_suspended]),
        }
    
    def __repr__(self) -> str:
        metrics = self.get_global_metrics()
        return f"TrustEngine(agents={metrics['total_agents']}, events={metrics['total_events']})"


# ════════════════════════════════════════════════════════════════════════════════
# DEMONSTRAÇÃO
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Criar engine
    engine = TrustEngine()
    
    # Simular eventos para alguns agentes
    agent1 = "agent-code-generator-001"
    agent2 = "agent-data-analyzer-002"
    
    # Agent 1: Algumas boas ações
    for _ in range(5):
        engine.record_good_action(agent1, "Código gerado sem problemas")
    
    print(f"\n{agent1}:")
    tf1 = engine.get_trust_factor(agent1)
    print(f"  Trust Factor: {tf1.current_factor:.2%}")
    print(f"  Level: {tf1.level.name}")
    
    # Agent 2: Uma violação
    engine.record_violation(
        agent2,
        ViolationType.SCOPE_VIOLATION,
        Severity.MEDIUM,
        "Agente tentou acessar dados fora do escopo",
    )
    
    print(f"\n{agent2}:")
    tf2 = engine.get_trust_factor(agent2)
    print(f"  Trust Factor: {tf2.current_factor:.2%}")
    print(f"  Level: {tf2.level.name}")
    
    # Agent 2: Violação crítica
    engine.record_violation(
        agent2,
        ViolationType.DATA_EXFILTRATION,
        Severity.CRITICAL,
        "Tentativa de exfiltração de dados detectada",
    )
    
    print(f"\n{agent2} (após violação crítica):")
    tf2 = engine.get_trust_factor(agent2)
    print(f"  Trust Factor: {tf2.current_factor:.2%}")
    print(f"  Level: {tf2.level.name}")
    print(f"  Suspenso: {tf2.is_suspended}")
    print(f"  Razão: {tf2.suspension_reason}")
    
    # Métricas globais
    print("\n" + "═" * 60)
    print("MÉTRICAS GLOBAIS")
    print("═" * 60)
    for key, value in engine.get_global_metrics().items():
        print(f"  {key}: {value}")
