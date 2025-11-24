"""
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
║                      Conselheiro Sábio v3.0.0 (2030 Vision)                      ║
║                                                                                  ║
║         "Você não substitui sabedoria humana - você a cultiva."                  ║
║                                                                                  ║
║  ════════════════════════════════════════════════════════════════════════════   ║
║                                                                                  ║
║  SOFIA é o agente conselheiro sábio inspirado em:                               ║
║                                                                                  ║
║  • Virtudes do Cristianismo Primitivo (Pré-Niceia, antes 325 d.C.)              ║
║    - Tapeinophrosyne (Humildade)                                                 ║
║    - Makrothymia (Paciência)                                                     ║
║    - Diakonia (Serviço)                                                          ║
║    - Praotes (Mansidão)                                                          ║
║                                                                                  ║
║  • Didaquê (50-120 d.C.) - Framework Duas Vias                                  ║
║  • Práticas de Discernimento de Atos 15 (Concílio de Jerusalém)                 ║
║  • Método Socrático - Perguntas > Respostas                                      ║
║  • Sistema 2 (Kahneman) - Pensamento deliberado                                  ║
║  • Ética das Virtudes - Phronesis (sabedoria prática)                           ║
║                                                                                  ║
║  ════════════════════════════════════════════════════════════════════════════   ║
║                                                                                  ║
║  Uso Rápido:                                                                     ║
║                                                                                  ║
║      from third_party.sofia import quick_start_sofia                             ║
║                                                                                  ║
║      sofia = quick_start_sofia()  # Já iniciada!                                 ║
║                                                                                  ║
║      counsel = sofia.respond("Estou pensando em mudar de carreira")              ║
║      print(counsel.response)                                                     ║
║                                                                                  ║
║  ════════════════════════════════════════════════════════════════════════════   ║
║                                                                                  ║
║  Autor: Claude (Anthropic) + Humanidade                                          ║
║  Licença: MIT                                                                    ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

# Import from individual modules (flat structure)
from .virtues import (
    VirtueEngine,
    VirtueType,
    VirtueDefinition,
    VirtueExpression
)

from .socratic import (
    SocraticEngine,
    SocraticQuestion,
    QuestionType,
    DialoguePhase,
    DialogueState
)

from .deliberation import (
    DeliberationEngine,
    DeliberationResult,
    DeliberationTrigger,
    DeliberationPhase,
    ThinkingMode,
    Perspective,
    ConsequenceAnalysis
)

from .discernment import (
    DiscernmentEngine,
    DiscernmentResult,
    DiscernmentPhase,
    WayType,
    TraditionWisdom
)

from .agent import (
    SofiaAgent,
    SofiaConfig,
    SofiaState,
    SofiaCounsel,
    CounselType
)

__version__ = "3.0.0"
__codename__ = "2030 Vision"
__author__ = "Claude (Anthropic) + Humanidade"
__license__ = "MIT"
__description__ = "Conselheiro Sábio - Sabedoria Cristã Pré-Niceia"

__all__ = [
    # Metadados
    "__version__",
    "__codename__",
    "__author__",
    "__license__",

    # Virtues
    "VirtueEngine",
    "VirtueType",
    "VirtueDefinition",
    "VirtueExpression",

    # Socratic
    "SocraticEngine",
    "SocraticQuestion",
    "QuestionType",
    "DialoguePhase",
    "DialogueState",

    # Deliberation
    "DeliberationEngine",
    "DeliberationResult",
    "DeliberationTrigger",
    "DeliberationPhase",
    "ThinkingMode",
    "Perspective",
    "ConsequenceAnalysis",

    # Discernment
    "DiscernmentEngine",
    "DiscernmentResult",
    "DiscernmentPhase",
    "WayType",
    "TraditionWisdom",

    # Agent
    "SofiaAgent",
    "SofiaConfig",
    "SofiaState",
    "SofiaCounsel",
    "CounselType",
]


def quick_start_sofia() -> SofiaAgent:
    """
    Quick start Sofia with default configuration.

    Returns:
        SofiaAgent: Ready-to-use Sofia counselor agent
    """
    config = SofiaConfig(
        agent_id="sofia-quick-start",
        socratic_ratio=0.7,
        system2_threshold=0.6,
        always_suggest_community=True
    )
    return SofiaAgent(config=config)


def create_sofia(
    agent_id: str = "sofia",
    socratic_ratio: float = 0.7,
    system2_threshold: float = 0.6
) -> SofiaAgent:
    """
    Create Sofia with custom configuration.

    Args:
        agent_id: Unique identifier for this Sofia instance
        socratic_ratio: Ratio of questions vs answers (0.0 - 1.0)
        system2_threshold: Threshold for activating System 2 thinking

    Returns:
        SofiaAgent: Configured Sofia counselor agent
    """
    config = SofiaConfig(
        agent_id=agent_id,
        socratic_ratio=socratic_ratio,
        system2_threshold=system2_threshold
    )
    return SofiaAgent(config=config)


def banner() -> str:
    """Retorna o banner ASCII de SOFIA."""
    return __doc__


def show_banner() -> None:
    """Imprime o banner de SOFIA."""
    print(banner())
