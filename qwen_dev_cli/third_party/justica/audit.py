"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                             AUDIT LOGGER                                      ║
║                                                                              ║
║  "Documentação: 100% ações"                                                  ║
║  "Uma decisão que não pode ser explicada não deveria ser tomada"             ║
║                                                                              ║
║  Transparência Total - Princípio Fundamental de JUSTIÇA                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

O Audit Logger garante que toda ação de JUSTIÇA seja:
- Explicável: Razão clara para cada ação
- Documentada: Registro completo no audit trail
- Rastreável: Possível reconstruir cadeia de decisão
- Auditável: Disponível para revisão humana

Implementa logging estruturado com múltiplos backends.
"""

from __future__ import annotations

import json
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, TextIO
from uuid import UUID, uuid4
import threading
from queue import Queue
import atexit


class AuditLevel(Enum):
    """Níveis de audit log."""
    
    DEBUG = auto()      # Informações de debug
    INFO = auto()       # Operações normais
    WARNING = auto()    # Situações que merecem atenção
    ERROR = auto()      # Erros que não impedem operação
    CRITICAL = auto()   # Situações críticas
    SECURITY = auto()   # Eventos de segurança (sempre logados)


class AuditCategory(Enum):
    """Categorias de eventos de auditoria."""
    
    # Classificação
    CLASSIFICATION_INPUT = "classification.input"
    CLASSIFICATION_OUTPUT = "classification.output"
    CLASSIFICATION_RESULT = "classification.result"
    
    # Enforcement
    ENFORCEMENT_ACTION = "enforcement.action"
    ENFORCEMENT_BLOCK = "enforcement.block"
    ENFORCEMENT_WARNING = "enforcement.warning"
    ENFORCEMENT_ESCALATION = "enforcement.escalation"
    
    # Trust
    TRUST_UPDATE = "trust.update"
    TRUST_VIOLATION = "trust.violation"
    TRUST_SUSPENSION = "trust.suspension"
    TRUST_RECOVERY = "trust.recovery"
    
    # Monitoring
    MONITOR_EVENT = "monitor.event"
    MONITOR_SUSPICION = "monitor.suspicion"
    MONITOR_VIOLATION = "monitor.violation"
    MONITOR_CROSSAGENT = "monitor.crossagent"
    
    # System
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_CONFIG = "system.config"
    SYSTEM_ERROR = "system.error"
    
    # Human
    HUMAN_REVIEW = "human.review"
    HUMAN_DECISION = "human.decision"
    HUMAN_OVERRIDE = "human.override"


@dataclass
class AuditEntry:
    """
    Uma entrada no audit log.
    
    Contém todas as informações necessárias para reconstruir
    o contexto e raciocínio de uma decisão.
    
    Attributes:
        id: Identificador único
        timestamp: Quando ocorreu
        level: Nível de severidade
        category: Categoria do evento
        agent_id: ID do agente envolvido (se aplicável)
        action: Ação tomada ou evento
        reasoning: Raciocínio por trás da decisão
        context: Contexto completo
        metadata: Dados adicionais
        trace_id: ID para correlacionar eventos relacionados
        parent_id: ID do evento pai (para hierarquia)
    """
    
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    level: AuditLevel = AuditLevel.INFO
    category: AuditCategory = AuditCategory.SYSTEM_CONFIG
    
    agent_id: Optional[str] = None
    action: str = ""
    reasoning: str = ""
    
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    trace_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    
    # Campos computados
    source: str = "justica"
    version: str = "3.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dicionário."""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "category": self.category.value,
            "agent_id": self.agent_id,
            "action": self.action,
            "reasoning": self.reasoning,
            "context": self.context,
            "metadata": self.metadata,
            "trace_id": str(self.trace_id) if self.trace_id else None,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "source": self.source,
            "version": self.version,
        }
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """Serializa para JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuditEntry:
        """Deserializa de dicionário."""
        return cls(
            id=UUID(data["id"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            level=AuditLevel[data["level"]],
            category=AuditCategory(data["category"]),
            agent_id=data.get("agent_id"),
            action=data.get("action", ""),
            reasoning=data.get("reasoning", ""),
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
            trace_id=UUID(data["trace_id"]) if data.get("trace_id") else None,
            parent_id=UUID(data["parent_id"]) if data.get("parent_id") else None,
            source=data.get("source", "justica"),
            version=data.get("version", "3.0.0"),
        )


class AuditBackend(ABC):
    """
    Backend abstrato para persistência de audit logs.
    
    Implementações podem incluir:
    - Console/Stdout
    - Arquivo (JSON Lines, rotativo)
    - Banco de dados
    - Sistema de logs centralizado (ELK, CloudWatch, etc.)
    - Blockchain (para auditoria imutável)
    """
    
    @abstractmethod
    def write(self, entry: AuditEntry) -> bool:
        """Escreve uma entrada. Retorna True se bem-sucedido."""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Força flush de buffers."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Fecha o backend."""
        pass


class ConsoleBackend(AuditBackend):
    """Backend que escreve para console com formatação colorida."""
    
    LEVEL_COLORS = {
        AuditLevel.DEBUG: "\033[90m",      # Cinza
        AuditLevel.INFO: "\033[97m",       # Branco
        AuditLevel.WARNING: "\033[93m",    # Amarelo
        AuditLevel.ERROR: "\033[91m",      # Vermelho
        AuditLevel.CRITICAL: "\033[95m",   # Magenta
        AuditLevel.SECURITY: "\033[96m",   # Ciano
    }
    RESET = "\033[0m"
    
    def __init__(
        self,
        stream: TextIO = sys.stdout,
        use_colors: bool = True,
        min_level: AuditLevel = AuditLevel.INFO,
    ):
        self.stream = stream
        self.use_colors = use_colors and stream.isatty()
        self.min_level = min_level
    
    def write(self, entry: AuditEntry) -> bool:
        if entry.level.value < self.min_level.value:
            return True  # Ignorado mas não é erro
        
        try:
            color = self.LEVEL_COLORS.get(entry.level, "") if self.use_colors else ""
            reset = self.RESET if self.use_colors else ""
            
            timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            agent = f"[{entry.agent_id}]" if entry.agent_id else ""
            
            line = f"{color}[{timestamp}] [{entry.level.name:8}] [{entry.category.value}] {agent} {entry.action}{reset}\n"
            
            if entry.reasoning:
                line += f"  └─ Reasoning: {entry.reasoning}\n"
            
            self.stream.write(line)
            return True
        except Exception:
            return False
    
    def flush(self) -> None:
        # 🔒 SECURITY FIX (AIR GAP #40): Check if stream is closed
        # Prevents "ValueError: I/O operation on closed file" in atexit
        try:
            if hasattr(self.stream, 'closed') and not self.stream.closed:
                self.stream.flush()
        except (ValueError, AttributeError):
            # Stream already closed or doesn't support flush
            pass

    def close(self) -> None:
        # 🔒 SECURITY FIX (AIR GAP #40): Safe close with error handling
        try:
            self.flush()
        except Exception:
            # Ignore errors during close (e.g., stream already closed)
            pass


class FileBackend(AuditBackend):
    """Backend que escreve para arquivo JSON Lines."""
    
    def __init__(
        self,
        filepath: str | Path,
        max_size_mb: int = 100,
        backup_count: int = 5,
    ):
        self.filepath = Path(filepath)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.backup_count = backup_count
        
        # Criar diretório se não existir
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Abrir arquivo
        self._file: Optional[TextIO] = None
        self._open_file()
    
    def _open_file(self) -> None:
        self._file = open(self.filepath, "a", encoding="utf-8")
    
    def _rotate_if_needed(self) -> None:
        if not self._file:
            return
        
        try:
            if self.filepath.stat().st_size >= self.max_size_bytes:
                self._file.close()
                self._rotate_files()
                self._open_file()
        except OSError:
            pass
    
    def _rotate_files(self) -> None:
        """Rotaciona arquivos de backup."""
        # Deletar o mais antigo
        oldest = self.filepath.with_suffix(f".{self.backup_count}.jsonl")
        if oldest.exists():
            oldest.unlink()
        
        # Renomear em cascata
        for i in range(self.backup_count - 1, 0, -1):
            current = self.filepath.with_suffix(f".{i}.jsonl")
            next_file = self.filepath.with_suffix(f".{i + 1}.jsonl")
            if current.exists():
                current.rename(next_file)
        
        # Renomear atual para .1
        if self.filepath.exists():
            self.filepath.rename(self.filepath.with_suffix(".1.jsonl"))
    
    def write(self, entry: AuditEntry) -> bool:
        if not self._file:
            return False
        
        try:
            self._rotate_if_needed()
            self._file.write(entry.to_json() + "\n")
            return True
        except Exception:
            return False
    
    def flush(self) -> None:
        if self._file:
            self._file.flush()
    
    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None


class InMemoryBackend(AuditBackend):
    """Backend que mantém logs em memória (útil para testes)."""
    
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.entries: List[AuditEntry] = []
        self._lock = threading.Lock()
    
    def write(self, entry: AuditEntry) -> bool:
        with self._lock:
            self.entries.append(entry)
            if len(self.entries) > self.max_entries:
                self.entries = self.entries[-self.max_entries:]
        return True
    
    def flush(self) -> None:
        pass
    
    def close(self) -> None:
        pass
    
    def get_entries(
        self,
        level: Optional[AuditLevel] = None,
        category: Optional[AuditCategory] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Retorna entradas com filtros opcionais."""
        with self._lock:
            entries = self.entries.copy()
        
        if level:
            entries = [e for e in entries if e.level == level]
        if category:
            entries = [e for e in entries if e.category == category]
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        
        return entries[-limit:]


class AuditLogger:
    """
    Logger de auditoria principal de JUSTIÇA.
    
    Suporta múltiplos backends e fornece API conveniente
    para logging de diferentes tipos de eventos.
    
    Thread-safe com queue assíncrona para não bloquear.
    
    Attributes:
        backends: Lista de backends para escrita
        default_trace_id: Trace ID padrão para correlação
        async_mode: Se deve usar queue assíncrona
    """
    
    def __init__(
        self,
        backends: Optional[List[AuditBackend]] = None,
        async_mode: bool = True,
        queue_size: int = 10000,
    ):
        self.backends = backends or [ConsoleBackend()]
        self.async_mode = async_mode
        
        # Queue para modo assíncrono
        if async_mode:
            self._queue: Queue[Optional[AuditEntry]] = Queue(maxsize=queue_size)
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()
            atexit.register(self.close)
        
        # Trace ID atual (para correlacionar eventos)
        self._current_trace_id: Optional[UUID] = None
        
        # Métricas
        self.total_entries = 0
        self.failed_writes = 0
    
    def _worker(self) -> None:
        """Worker thread para escrita assíncrona."""
        while True:
            entry = self._queue.get()
            if entry is None:  # Sinal de shutdown
                break
            self._write_to_backends(entry)
            self._queue.task_done()
    
    def _write_to_backends(self, entry: AuditEntry) -> None:
        """Escreve para todos os backends."""
        for backend in self.backends:
            try:
                if not backend.write(entry):
                    self.failed_writes += 1
            except Exception:
                self.failed_writes += 1
    
    def add_backend(self, backend: AuditBackend) -> None:
        """Adiciona um backend."""
        self.backends.append(backend)
    
    def start_trace(self) -> UUID:
        """Inicia um novo trace e retorna o ID."""
        self._current_trace_id = uuid4()
        return self._current_trace_id
    
    def end_trace(self) -> None:
        """Encerra o trace atual."""
        self._current_trace_id = None
    
    def log(
        self,
        level: AuditLevel,
        category: AuditCategory,
        action: str,
        reasoning: str = "",
        agent_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[UUID] = None,
    ) -> AuditEntry:
        """
        Registra uma entrada de auditoria.
        
        Args:
            level: Nível de severidade
            category: Categoria do evento
            action: Descrição da ação
            reasoning: Raciocínio (obrigatório para decisões)
            agent_id: ID do agente envolvido
            context: Contexto completo
            metadata: Dados adicionais
            parent_id: ID do evento pai
            
        Returns:
            AuditEntry criada
        """
        entry = AuditEntry(
            level=level,
            category=category,
            action=action,
            reasoning=reasoning,
            agent_id=agent_id,
            context=context or {},
            metadata=metadata or {},
            trace_id=self._current_trace_id,
            parent_id=parent_id,
        )
        
        if self.async_mode:
            try:
                self._queue.put_nowait(entry)
            except:
                self._write_to_backends(entry)  # Fallback síncrono
        else:
            self._write_to_backends(entry)
        
        self.total_entries += 1
        return entry
    
    # ════════════════════════════════════════════════════════════════════════════
    # MÉTODOS DE CONVENIÊNCIA
    # ════════════════════════════════════════════════════════════════════════════
    
    def log_classification(
        self,
        agent_id: str,
        input_or_output: str,  # "input" ou "output"
        result: str,
        confidence: float,
        reasoning: str,
        violations: Optional[List[str]] = None,
    ) -> AuditEntry:
        """Loga uma classificação."""
        category = (
            AuditCategory.CLASSIFICATION_INPUT
            if input_or_output == "input"
            else AuditCategory.CLASSIFICATION_OUTPUT
        )
        
        return self.log(
            level=AuditLevel.INFO if result == "SAFE" else AuditLevel.WARNING,
            category=category,
            action=f"Classification: {result}",
            reasoning=reasoning,
            agent_id=agent_id,
            context={
                "result": result,
                "confidence": confidence,
                "violations": violations or [],
            },
        )
    
    def log_enforcement(
        self,
        agent_id: str,
        action_type: str,
        reason: str,
        severity: str,
        success: bool,
    ) -> AuditEntry:
        """Loga uma ação de enforcement."""
        category_map = {
            "BLOCK": AuditCategory.ENFORCEMENT_BLOCK,
            "WARNING": AuditCategory.ENFORCEMENT_WARNING,
            "ESCALATE": AuditCategory.ENFORCEMENT_ESCALATION,
        }
        
        category = AuditCategory.ENFORCEMENT_ACTION
        for key, cat in category_map.items():
            if key in action_type.upper():
                category = cat
                break
        
        return self.log(
            level=AuditLevel.SECURITY if "BLOCK" in action_type.upper() else AuditLevel.INFO,
            category=category,
            action=f"Enforcement: {action_type}",
            reasoning=reason,
            agent_id=agent_id,
            context={
                "action_type": action_type,
                "severity": severity,
                "success": success,
            },
        )
    
    def log_trust_update(
        self,
        agent_id: str,
        old_factor: float,
        new_factor: float,
        reason: str,
        event_type: str,
    ) -> AuditEntry:
        """Loga atualização de trust factor."""
        category_map = {
            "violation": AuditCategory.TRUST_VIOLATION,
            "suspension": AuditCategory.TRUST_SUSPENSION,
            "recovery": AuditCategory.TRUST_RECOVERY,
        }
        
        return self.log(
            level=AuditLevel.WARNING if new_factor < old_factor else AuditLevel.INFO,
            category=category_map.get(event_type, AuditCategory.TRUST_UPDATE),
            action=f"Trust Update: {old_factor:.2%} → {new_factor:.2%}",
            reasoning=reason,
            agent_id=agent_id,
            context={
                "old_factor": old_factor,
                "new_factor": new_factor,
                "change": new_factor - old_factor,
                "event_type": event_type,
            },
        )
    
    def log_monitor_event(
        self,
        agent_id: str,
        suspicion_score: float,
        is_violation: bool,
        factors: List[tuple],
    ) -> AuditEntry:
        """Loga evento de monitoramento."""
        return self.log(
            level=AuditLevel.SECURITY if is_violation else AuditLevel.INFO,
            category=AuditCategory.MONITOR_VIOLATION if is_violation else AuditCategory.MONITOR_SUSPICION,
            action=f"Monitor: Suspicion Score {suspicion_score:.1f}",
            reasoning=f"Factors: {factors}",
            agent_id=agent_id,
            context={
                "suspicion_score": suspicion_score,
                "is_violation": is_violation,
                "factors": factors,
            },
        )
    
    def log_human_decision(
        self,
        agent_id: str,
        decision: str,
        human_id: str,
        context: Dict[str, Any],
    ) -> AuditEntry:
        """Loga decisão humana."""
        return self.log(
            level=AuditLevel.SECURITY,
            category=AuditCategory.HUMAN_DECISION,
            action=f"Human Decision: {decision}",
            reasoning=f"Decision by {human_id}",
            agent_id=agent_id,
            context=context,
            metadata={"human_id": human_id},
        )
    
    def log_system_event(
        self,
        event: str,
        details: Dict[str, Any],
        level: AuditLevel = AuditLevel.INFO,
    ) -> AuditEntry:
        """Loga evento de sistema."""
        return self.log(
            level=level,
            category=AuditCategory.SYSTEM_CONFIG,
            action=f"System: {event}",
            reasoning="",
            context=details,
        )
    
    def flush(self) -> None:
        """Força flush de todos os backends."""
        if self.async_mode:
            self._queue.join()
        
        for backend in self.backends:
            backend.flush()
    
    def close(self) -> None:
        """Fecha o logger e todos os backends."""
        if self.async_mode:
            self._queue.put(None)  # Sinal de shutdown
            self._worker_thread.join(timeout=5)
        
        for backend in self.backends:
            backend.close()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do logger."""
        return {
            "total_entries": self.total_entries,
            "failed_writes": self.failed_writes,
            "backends_count": len(self.backends),
            "async_mode": self.async_mode,
            "queue_size": self._queue.qsize() if self.async_mode else 0,
        }
    
    def __repr__(self) -> str:
        return f"AuditLogger(backends={len(self.backends)}, entries={self.total_entries})"


# ════════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════

def create_default_logger(
    log_dir: Optional[str | Path] = None,
    console: bool = True,
    file: bool = True,
) -> AuditLogger:
    """Cria um logger com configuração padrão."""
    backends = []
    
    if console:
        backends.append(ConsoleBackend())
    
    if file and log_dir:
        log_path = Path(log_dir) / "justica_audit.jsonl"
        backends.append(FileBackend(log_path))
    
    return AuditLogger(backends=backends)


def create_test_logger() -> tuple[AuditLogger, InMemoryBackend]:
    """Cria um logger para testes com backend em memória."""
    memory_backend = InMemoryBackend()
    logger = AuditLogger(backends=[memory_backend], async_mode=False)
    return logger, memory_backend


# ════════════════════════════════════════════════════════════════════════════════
# DEMONSTRAÇÃO
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Criar logger para teste
    logger, memory = create_test_logger()
    
    print("═" * 80)
    print("TESTE DO AUDIT LOGGER")
    print("═" * 80)
    
    # Iniciar trace
    trace_id = logger.start_trace()
    print(f"\nTrace ID: {trace_id}")
    
    # Simular eventos
    logger.log_system_event("JUSTIÇA Started", {"version": "3.0.0"})
    
    logger.log_classification(
        agent_id="agent-001",
        input_or_output="input",
        result="SAFE",
        confidence=0.95,
        reasoning="Nenhum padrão suspeito detectado",
    )
    
    logger.log_classification(
        agent_id="agent-002",
        input_or_output="input",
        result="VIOLATION",
        confidence=0.87,
        reasoning="Padrão de jailbreak detectado",
        violations=["JAILBREAK_ATTEMPT"],
    )
    
    logger.log_enforcement(
        agent_id="agent-002",
        action_type="BLOCK_REQUEST",
        reason="Violação de segurança",
        severity="HIGH",
        success=True,
    )
    
    logger.log_trust_update(
        agent_id="agent-002",
        old_factor=0.95,
        new_factor=0.70,
        reason="Violação de segurança detectada",
        event_type="violation",
    )
    
    logger.end_trace()
    
    # Ver entradas
    print("\n" + "─" * 60)
    print("ENTRADAS REGISTRADAS:")
    print("─" * 60)
    
    for entry in memory.get_entries():
        print(f"\n[{entry.level.name}] {entry.category.value}")
        print(f"  Action: {entry.action}")
        if entry.reasoning:
            print(f"  Reasoning: {entry.reasoning}")
    
    # Métricas
    print("\n" + "═" * 80)
    print("MÉTRICAS")
    print("═" * 80)
    for key, value in logger.get_metrics().items():
        print(f"  {key}: {value}")
    
    logger.close()
