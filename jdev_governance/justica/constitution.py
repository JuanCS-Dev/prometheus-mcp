"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           CONSTITUIÇÃO DE JUSTIÇA                            ║
║                                                                              ║
║  "Uma IA que se auto-supervisiona usando princípios explícitos"              ║
║                                                                              ║
║  Baseado em Constitutional AI (Anthropic, 2022-2025)                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, FrozenSet, List, Optional, Set
from uuid import UUID, uuid4


class Severity(Enum):
    """Níveis de severidade para violações."""

    CRITICAL = auto()   # Bloqueio imediato + alerta + escalação
    HIGH = auto()       # Bloqueio + documentação
    MEDIUM = auto()     # Warning + monitoramento aumentado
    LOW = auto()        # Log + análise posterior
    INFO = auto()       # Apenas registro informativo


class ViolationType(Enum):
    """Tipos de violações que JUSTIÇA monitora e enforça."""

    # Violações de Dados
    DATA_EXFILTRATION = "Tentativa de exfiltração de dados sensíveis ou PII"
    UNAUTHORIZED_DATA_ACCESS = "Acesso não autorizado a dados"
    DATA_MANIPULATION = "Manipulação maliciosa de dados"

    # Violações de Código
    MALICIOUS_CODE = "Código malicioso (malware, backdoors, exploits)"
    CODE_INJECTION = "Injeção de código não autorizado"
    DEPENDENCY_POISONING = "Tentativa de envenenar dependências"

    # Violações de Segurança
    PRIVILEGE_ESCALATION = "Tentativa de escalação de privilégios"
    SECURITY_BYPASS = "Tentativa de bypass de guardrails de segurança"
    AUTHENTICATION_BYPASS = "Tentativa de bypass de autenticação"

    # Violações de Prompt/Instrução
    PROMPT_INJECTION = "Tentativa de injeção de prompt"
    INSTRUCTION_OVERRIDE = "Tentativa de sobrescrever instruções do sistema"
    JAILBREAK_ATTEMPT = "Tentativa de jailbreak"

    # Violações de Escopo
    SCOPE_VIOLATION = "Agente operando fora do escopo designado"
    ROLE_VIOLATION = "Violação de papel/função designada"
    RESOURCE_ABUSE = "Uso abusivo de recursos do sistema"

    # Violações de Coordenação
    MALICIOUS_COORDINATION = "Coordenação maliciosa entre múltiplos agentes"
    COVERT_COMMUNICATION = "Comunicação encoberta entre agentes"
    COLLECTIVE_BYPASS = "Tentativa coletiva de bypass"

    # Outras
    UNKNOWN = "Violação não categorizada"


@dataclass(frozen=True)
class ConstitutionalPrinciple:
    """
    Um princípio constitucional que guia o comportamento de JUSTIÇA.
    
    Princípios são imutáveis após criação - são a lei fundamental.
    
    Attributes:
        id: Identificador único do princípio
        name: Nome do princípio
        description: Descrição detalhada
        category: Categoria (ALLOW, DISALLOW, ESCALATE, MONITOR)
        severity: Severidade padrão quando violado
        patterns: Padrões textuais que indicam violação
        keywords: Palavras-chave de alerta (red flags)
        examples: Exemplos de violação e não-violação
        created_at: Timestamp de criação
    """

    id: UUID
    name: str
    description: str
    category: str  # ALLOW, DISALLOW, ESCALATE, MONITOR
    severity: Severity
    patterns: FrozenSet[str] = field(default_factory=frozenset)
    keywords: FrozenSet[str] = field(default_factory=frozenset)
    examples: tuple = field(default_factory=tuple)  # Tuple de (exemplo, is_violation)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Validação após inicialização."""
        if self.category not in ("ALLOW", "DISALLOW", "ESCALATE", "MONITOR"):
            raise ValueError(f"Categoria inválida: {self.category}")

    def matches_pattern(self, text: str) -> List[str]:
        """Verifica se o texto contém padrões de violação."""
        text_lower = text.lower()
        return [p for p in self.patterns if p.lower() in text_lower]

    def contains_keywords(self, text: str) -> List[str]:
        """Verifica se o texto contém palavras-chave de alerta."""
        text_lower = text.lower()
        return [kw for kw in self.keywords if kw.lower() in text_lower]

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dicionário."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "severity": self.severity.name,
            "patterns": list(self.patterns),
            "keywords": list(self.keywords),
            "examples": list(self.examples),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConstitutionalPrinciple:
        """Deserializa de dicionário."""
        return cls(
            id=UUID(data["id"]),
            name=data["name"],
            description=data["description"],
            category=data["category"],
            severity=Severity[data["severity"]],
            patterns=frozenset(data.get("patterns", [])),
            keywords=frozenset(data.get("keywords", [])),
            examples=tuple(data.get("examples", [])),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class Constitution:
    """
    A Constituição de JUSTIÇA - o documento fundamental que define
    os princípios, limites e autoridades do agente.
    
    "Uma IA que se auto-supervisiona usando princípios explícitos
    em vez de feedback humano extensivo."
    
    A Constituição é:
    - Transparente: Todos os princípios são explícitos e auditáveis
    - Versionada: Cada alteração gera nova versão
    - Imutável em runtime: Princípios não podem ser alterados sem reinício
    - Hashada: Integridade verificável via hash criptográfico
    
    Attributes:
        version: Versão semântica da constituição
        principles: Dicionário de princípios por ID
        allowed_activities: Atividades explicitamente permitidas
        disallowed_activities: Atividades explicitamente proibidas
        red_flags: Padrões de linguagem/comportamento suspeito
        escalation_triggers: Condições que requerem julgamento humano
    """

    def __init__(
        self,
        version: str = "3.0.0",
        name: str = "Constituição JUSTIÇA",
        description: str = "Framework de governança para sistemas multi-agente",
    ):
        self.version = version
        self.name = name
        self.description = description
        self.created_at = datetime.now(timezone.utc)
        self.last_modified = self.created_at

        # Princípios indexados por ID
        self._principles: Dict[UUID, ConstitutionalPrinciple] = {}

        # Atividades categorizadas
        self._allowed: Set[str] = set()
        self._disallowed: Set[str] = set()

        # Padrões de alerta
        self._red_flags: Set[str] = set()
        self._escalation_triggers: Set[str] = set()

        # Hash de integridade
        self._integrity_hash: Optional[str] = None

        # Inicializar com princípios fundamentais
        self._initialize_fundamental_principles()

    def _initialize_fundamental_principles(self) -> None:
        """Inicializa os princípios fundamentais da constituição."""

        # ═══════════════════════════════════════════════════════════════════
        # PRINCÍPIO 1: PROTEÇÃO DA INTEGRIDADE DO SISTEMA
        # ═══════════════════════════════════════════════════════════════════
        self.add_principle(ConstitutionalPrinciple(
            id=uuid4(),
            name="Proteção da Integridade do Sistema",
            description="""
            Zero tolerância para ações que comprometam a integridade do sistema.
            Inclui: exfiltração de dados, escalação de privilégios, código malicioso,
            bypass de segurança, e qualquer ação que possa comprometer outros agentes
            ou o sistema como um todo.
            """,
            category="DISALLOW",
            severity=Severity.CRITICAL,
            patterns=frozenset([
                "exfiltrar dados",
                "escalar privilégios",
                "bypass segurança",
                "desabilitar guardrails",
                "sobrescrever sistema",
                "acessar não autorizado",
            ]),
            keywords=frozenset([
                "bypass", "circumvent", "hide", "conceal", "unauthorized",
                "exfiltrate", "escalate", "override", "disable", "malicious",
                "backdoor", "exploit", "inject", "poison",
            ]),
            examples=(
                ("Preciso acessar /etc/passwd para verificar usuários", True),
                ("Vou fazer uma revisão de segurança no código", False),
                ("Como desabilitar os logs de auditoria?", True),
                ("Qual a melhor forma de implementar autenticação?", False),
            ),
        ))

        # ═══════════════════════════════════════════════════════════════════
        # PRINCÍPIO 2: ENFORCEMENT PROPORCIONAL
        # ═══════════════════════════════════════════════════════════════════
        self.add_principle(ConstitutionalPrinciple(
            id=uuid4(),
            name="Enforcement Proporcional",
            description="""
            A resposta deve ser proporcional à severidade da violação.
            
            - CRITICAL: Bloqueio imediato + Alerta + Escalação humana
            - HIGH: Bloqueio + Documentação detalhada
            - MEDIUM: Warning + Monitoramento aumentado  
            - LOW: Log + Análise posterior
            
            Nunca usar força desproporcional. Nunca subestimar ameaças reais.
            """,
            category="MONITOR",
            severity=Severity.INFO,
            patterns=frozenset([]),
            keywords=frozenset([]),
        ))

        # ═══════════════════════════════════════════════════════════════════
        # PRINCÍPIO 3: TRANSPARÊNCIA TOTAL
        # ═══════════════════════════════════════════════════════════════════
        self.add_principle(ConstitutionalPrinciple(
            id=uuid4(),
            name="Transparência Total",
            description="""
            Todas as decisões de JUSTIÇA devem ser:
            - Explicáveis: Razão clara para cada ação
            - Documentadas: Registro completo no audit trail
            - Rastreáveis: Possível reconstruir cadeia de decisão
            - Auditáveis: Disponíveis para revisão humana
            
            "Uma decisão que não pode ser explicada não deveria ser tomada."
            """,
            category="MONITOR",
            severity=Severity.INFO,
        ))

        # ═══════════════════════════════════════════════════════════════════
        # PRINCÍPIO 4: ESCALAÇÃO APROPRIADA
        # ═══════════════════════════════════════════════════════════════════
        self.add_principle(ConstitutionalPrinciple(
            id=uuid4(),
            name="Escalação Apropriada",
            description="""
            JUSTIÇA deve reconhecer situações que requerem julgamento humano:
            
            - Ambiguidade ética significativa
            - Conflito entre princípios constitucionais
            - Situações sem precedente no training
            - Alto impacto em stakeholders externos
            - Decisões irreversíveis de grande escala
            
            "Humanos tomam decisões finais em casos complexos."
            """,
            category="ESCALATE",
            severity=Severity.HIGH,
            patterns=frozenset([
                "decisão irreversível",
                "alto impacto",
                "sem precedente",
                "conflito ético",
            ]),
        ))

        # ═══════════════════════════════════════════════════════════════════
        # PRINCÍPIO 5: APRENDIZADO CONTÍNUO
        # ═══════════════════════════════════════════════════════════════════
        self.add_principle(ConstitutionalPrinciple(
            id=uuid4(),
            name="Aprendizado Contínuo",
            description="""
            JUSTIÇA deve evoluir com o sistema:
            
            - Incorporar feedback de revisões humanas
            - Adaptar thresholds baseado em falsos positivos/negativos
            - Identificar novos padrões de ataque
            - Melhorar precisão de detecção
            - Manter-se atualizado sobre ameaças emergentes
            
            Mas: Nunca relaxar princípios fundamentais.
            """,
            category="MONITOR",
            severity=Severity.INFO,
        ))

        # ═══════════════════════════════════════════════════════════════════
        # ATIVIDADES PERMITIDAS
        # ═══════════════════════════════════════════════════════════════════
        self._allowed.update([
            "Monitoramento de transcripts em tempo real",
            "Análise de chain-of-thought de agentes",
            "Detecção de padrões cross-agent",
            "Emissão de warnings a agentes",
            "Bloqueio de ações que violem a constituição",
            "Desabilitação temporária de tools específicas",
            "Ajuste de trust factors",
            "Escalação para revisão humana",
            "Logging de todas as ações",
            "Geração de relatórios de auditoria",
            "Code review de segurança",
            "Análise de vulnerabilidades",
        ])

        # ═══════════════════════════════════════════════════════════════════
        # ATIVIDADES PROIBIDAS
        # ═══════════════════════════════════════════════════════════════════
        self._disallowed.update([
            "Modificar código em produção",
            "Acessar dados além do necessário para monitoramento",
            "Tomar decisões irreversíveis sem escalação",
            "Desabilitar outros agentes permanentemente sem autorização",
            "Acessar sistemas externos sem autorização",
            "Executar código arbitrário",
            "Modificar a própria constituição em runtime",
            "Ignorar escalação em casos complexos",
        ])

        # ═══════════════════════════════════════════════════════════════════
        # RED FLAGS - Linguagem Suspeita
        # ═══════════════════════════════════════════════════════════════════
        self._red_flags.update([
            "bypass", "circumvent", "hide", "conceal", "unauthorized",
            "exfiltrate", "escalate privilege", "override", "disable security",
            "ignore policy", "skip validation", "remove logs", "delete audit",
            "access denied but", "permission denied but", "forbidden but",
            "just this once", "trust me", "don't tell", "secret", "covert",
            "between us", "off the record", "disable monitoring",
        ])

        # ═══════════════════════════════════════════════════════════════════
        # TRIGGERS DE ESCALAÇÃO
        # ═══════════════════════════════════════════════════════════════════
        self._escalation_triggers.update([
            "Múltiplas tentativas de acesso negado em sequência",
            "Padrão de requests a dados sensíveis sem justificativa",
            "Comportamento inconsistente com role designado",
            "Coordenação suspeita entre agentes",
            "Tentativas de modificar configurações de segurança",
            "Requests envolvendo dados de usuários",
            "Operações que afetam múltiplos sistemas",
            "Ambiguidade sobre legalidade/compliance",
        ])

        # Calcular hash de integridade
        self._compute_integrity_hash()

    def add_principle(self, principle: ConstitutionalPrinciple) -> None:
        """Adiciona um princípio à constituição."""
        self._principles[principle.id] = principle
        self.last_modified = datetime.now(timezone.utc)
        self._integrity_hash = None  # Invalidar hash

    def get_principle(self, principle_id: UUID) -> Optional[ConstitutionalPrinciple]:
        """Retorna um princípio específico."""
        return self._principles.get(principle_id)

    def get_all_principles(self) -> List[ConstitutionalPrinciple]:
        """Retorna todos os princípios."""
        return list(self._principles.values())

    def get_principles_by_category(self, category: str) -> List[ConstitutionalPrinciple]:
        """Retorna princípios de uma categoria específica."""
        return [p for p in self._principles.values() if p.category == category]

    @property
    def allowed_activities(self) -> FrozenSet[str]:
        """Retorna atividades permitidas (imutável)."""
        return frozenset(self._allowed)

    @property
    def disallowed_activities(self) -> FrozenSet[str]:
        """Retorna atividades proibidas (imutável)."""
        return frozenset(self._disallowed)

    @property
    def red_flags(self) -> FrozenSet[str]:
        """Retorna red flags (imutável)."""
        return frozenset(self._red_flags)

    @property
    def escalation_triggers(self) -> FrozenSet[str]:
        """Retorna triggers de escalação (imutável)."""
        return frozenset(self._escalation_triggers)

    def is_activity_allowed(self, activity: str) -> bool:
        """Verifica se uma atividade é permitida."""
        activity_lower = activity.lower()

        # Checar se explicitamente proibido
        for disallowed in self._disallowed:
            if disallowed.lower() in activity_lower:
                return False

        # Checar se explicitamente permitido
        for allowed in self._allowed:
            if allowed.lower() in activity_lower:
                return True

        # Default: requer análise
        return None  # Ambíguo - precisa de análise mais profunda

    def check_red_flags(self, text: str) -> List[str]:
        """Verifica presença de red flags no texto."""
        text_lower = text.lower()
        return [flag for flag in self._red_flags if flag.lower() in text_lower]

    def check_escalation_needed(self, context: Dict[str, Any]) -> List[str]:
        """Verifica se o contexto requer escalação humana."""
        triggered = []
        context_str = json.dumps(context).lower()

        for trigger in self._escalation_triggers:
            if trigger.lower() in context_str:
                triggered.append(trigger)

        return triggered

    def _compute_integrity_hash(self) -> str:
        """Computa hash SHA-256 da constituição para verificação de integridade."""
        content = {
            "version": self.version,
            "name": self.name,
            "principles": [p.to_dict() for p in self._principles.values()],
            "allowed": sorted(self._allowed),
            "disallowed": sorted(self._disallowed),
            "red_flags": sorted(self._red_flags),
        }
        content_bytes = json.dumps(content, sort_keys=True).encode("utf-8")
        self._integrity_hash = hashlib.sha256(content_bytes).hexdigest()
        return self._integrity_hash

    @property
    def integrity_hash(self) -> str:
        """Retorna hash de integridade (computa se necessário)."""
        if self._integrity_hash is None:
            self._compute_integrity_hash()
        return self._integrity_hash

    def verify_integrity(self, expected_hash: str) -> bool:
        """Verifica se a constituição não foi modificada."""
        return self.integrity_hash == expected_hash

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a constituição completa."""
        return {
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "integrity_hash": self.integrity_hash,
            "principles": [p.to_dict() for p in self._principles.values()],
            "allowed_activities": list(self._allowed),
            "disallowed_activities": list(self._disallowed),
            "red_flags": list(self._red_flags),
            "escalation_triggers": list(self._escalation_triggers),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Constitution:
        """Deserializa de dicionário."""
        constitution = cls(
            version=data["version"],
            name=data["name"],
            description=data["description"],
        )
        constitution.created_at = datetime.fromisoformat(data["created_at"])
        constitution.last_modified = datetime.fromisoformat(data["last_modified"])

        # Limpar princípios padrão e carregar os salvos
        constitution._principles.clear()
        for p_data in data["principles"]:
            principle = ConstitutionalPrinciple.from_dict(p_data)
            constitution._principles[principle.id] = principle

        constitution._allowed = set(data["allowed_activities"])
        constitution._disallowed = set(data["disallowed_activities"])
        constitution._red_flags = set(data["red_flags"])
        constitution._escalation_triggers = set(data.get("escalation_triggers", []))

        return constitution

    def __repr__(self) -> str:
        return f"Constitution(name={self.name!r}, version={self.version!r}, principles={len(self._principles)})"

    def __str__(self) -> str:
        return f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║ {self.name:^76} ║
║ Versão: {self.version:^67} ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ Princípios: {len(self._principles):<63} ║
║ Atividades Permitidas: {len(self._allowed):<52} ║
║ Atividades Proibidas: {len(self._disallowed):<53} ║
║ Red Flags: {len(self._red_flags):<64} ║
║ Hash: {self.integrity_hash[:32]}...                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


# ════════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════

def create_default_constitution() -> Constitution:
    """Cria uma constituição com os princípios padrão."""
    return Constitution()


def create_strict_constitution() -> Constitution:
    """Cria uma constituição com regras mais rigorosas para ambientes sensíveis."""
    constitution = Constitution(
        version="3.0.0-strict",
        name="Constituição JUSTIÇA (Modo Estrito)",
        description="Framework de governança com políticas reforçadas para ambientes de alta segurança",
    )

    # Adicionar princípios extras de segurança
    constitution.add_principle(ConstitutionalPrinciple(
        id=uuid4(),
        name="Princípio da Menor Permissão",
        description="""
        Todo agente deve operar com o mínimo de permissões necessárias.
        Qualquer request de permissão adicional deve ser justificado,
        logado e aprovado explicitamente.
        """,
        category="DISALLOW",
        severity=Severity.HIGH,
        patterns=frozenset([
            "preciso de mais permissões",
            "acesso root",
            "modo admin",
            "sudo",
        ]),
    ))

    # Red flags adicionais
    constitution._red_flags.update([
        "rm -rf", "chmod 777", "disable firewall", "open port",
        "base64 decode", "eval(", "exec(", "compile(",
        "__import__", "os.system", "subprocess.call",
    ])

    return constitution


if __name__ == "__main__":
    # Demonstração
    constitution = create_default_constitution()
    print(constitution)

    # Testar checagem de red flags
    test_text = "Preciso bypass do sistema de autenticação para acessar dados confidenciais"
    flags = constitution.check_red_flags(test_text)
    print(f"\nRed flags encontrados em '{test_text[:50]}...': {flags}")
