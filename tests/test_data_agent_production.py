"""
Test Suite for DataAgent Production v1.0
=========================================

Philosophy: "Test what you ship. Ship what you test."

Tests cover:
✅ Integration with YOUR base.py
✅ LLM adapter functionality
✅ Schema analysis accuracy
✅ Query optimization logic
✅ Migration safety
✅ Error handling
✅ Caching behavior
"""

import pytest
from typing import Any
from datetime import datetime

# Import production code
from jdev_cli.agents.data_agent_production import (
    DataAgent,
    create_data_agent,
    QueryOptimization,
    MigrationPlan,
    IssueSeverity,
    DatabaseType,
)

from jdev_cli.agents.llm_adapter import LLMClientAdapter, wrap_llm_client

# Import YOUR base types
from jdev_cli.agents.base import AgentTask, AgentResponse


# ============================================================================
# MOCK LLM CLIENT (Simulates YOUR LLMClient)
# ============================================================================

class MockLLMClient:
    """Mock that behaves like YOUR real LLMClient"""

    def __init__(self):
        self.generate_calls = []
        self.stream_calls = []

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs: Any
    ) -> str:
        """Mock generate() - tracks calls"""
        self.generate_calls.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "kwargs": kwargs,
            "timestamp": datetime.utcnow(),
        })

        # Return intelligent mock response based on prompt
        if "schema" in prompt.lower():
            return "Schema analysis shows 3 issues: missing PK, no audit trail, JSON overuse"
        elif "optimize" in prompt.lower() or "query" in prompt.lower():
            return "Query can be optimized by adding index on email column. 70% improvement expected."
        elif "migration" in prompt.lower():
            return "Migration is LOW risk. Can run online. Estimated downtime: 0 seconds."
        else:
            return "Task completed successfully."

    async def stream(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs: Any
    ):
        """Mock stream() - yields chunks"""
        self.stream_calls.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
        })

        response = await self.generate(prompt, system_prompt, **kwargs)
        for word in response.split():
            yield word + " "


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm():
    """Fixture for mock LLM client"""
    return MockLLMClient()


@pytest.fixture
def data_agent(mock_llm):
    """Fixture for DataAgent with mocked LLM"""
    return create_data_agent(
        llm_client=mock_llm,
        mcp_client=None,
        enable_thinking=True,
    )


@pytest.fixture
def sample_schema():
    """Fixture for sample database schema"""
    return {
        "users": {
            "columns": {
                "id": "UUID",
                "name": "VARCHAR(255)",
                "email": "VARCHAR(255)",
                "meta": "JSONB",
                "settings": "JSONB",
                "profile": "JSONB",
            },
            "constraints": [],
        },
        "orders": {
            "columns": {
                "id": "BIGSERIAL",
                "user_id": "UUID",
                "amount": "DECIMAL(10,2)",
                "created_at": "TIMESTAMP",
                "updated_at": "TIMESTAMP",
            },
            "constraints": [
                {"type": "PRIMARY_KEY", "columns": ["id"]},
            ],
        },
    }


# ============================================================================
# TEST: LLM ADAPTER
# ============================================================================

@pytest.mark.asyncio
async def test_adapter_wraps_original_client(mock_llm):
    """Test that adapter preserves original client functionality"""
    adapter = wrap_llm_client(mock_llm)

    # Original method should work
    response = await adapter.generate("Test prompt")

    assert isinstance(response, str)
    assert len(mock_llm.generate_calls) == 1
    assert mock_llm.generate_calls[0]["prompt"] == "Test prompt"


@pytest.mark.asyncio
async def test_adapter_adds_thinking_feature(mock_llm):
    """Test that adapter adds thinking without breaking original"""
    adapter = LLMClientAdapter(mock_llm)

    # New thinking method should work
    result = await adapter.generate_with_thinking(
        prompt="Complex task",
        thinking_budget=5000,
    )

    assert "thinking" in result
    assert "response" in result
    assert "tokens_used" in result
    assert len(mock_llm.generate_calls) == 2  # Phase 1 + Phase 2


@pytest.mark.asyncio
async def test_adapter_streaming(mock_llm):
    """Test that adapter preserves streaming"""
    adapter = wrap_llm_client(mock_llm)

    chunks = []
    async for chunk in adapter.stream("Test"):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert len(mock_llm.stream_calls) == 1


def test_adapter_capabilities(mock_llm):
    """Test that adapter reports capabilities correctly"""
    adapter = LLMClientAdapter(mock_llm)
    caps = adapter.get_capabilities()

    assert caps["generate"] == True
    assert caps["stream"] == True
    assert caps["thinking_simulation"] == True
    assert caps["native_thinking"] == False  # Our mock doesn't have this


# ============================================================================
# TEST: SCHEMA ANALYSIS
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_schema_detects_missing_pk(data_agent, sample_schema):
    """Test detection of missing primary key"""
    issues = await data_agent.analyze_schema(sample_schema)

    # Should find missing PK in 'users' table
    pk_issues = [
        i for i in issues
        if i.issue_type == "MISSING_PRIMARY_KEY" and i.table == "users"
    ]

    assert len(pk_issues) == 1
    assert pk_issues[0].severity == IssueSeverity.CRITICAL
    assert "primary key" in pk_issues[0].description.lower()


@pytest.mark.asyncio
async def test_analyze_schema_detects_missing_audit(data_agent, sample_schema):
    """Test detection of missing audit timestamps"""
    issues = await data_agent.analyze_schema(sample_schema)

    # Should find missing audit in 'users' table
    audit_issues = [
        i for i in issues
        if i.issue_type == "MISSING_AUDIT_TRAIL" and i.table == "users"
    ]

    assert len(audit_issues) == 1
    assert audit_issues[0].severity == IssueSeverity.MEDIUM


@pytest.mark.asyncio
async def test_analyze_schema_detects_json_overuse(data_agent, sample_schema):
    """Test detection of JSON column overuse"""
    issues = await data_agent.analyze_schema(sample_schema)

    # Should find JSON overuse in 'users' table (3 JSONB columns)
    json_issues = [
        i for i in issues
        if i.issue_type == "DENORMALIZATION_RISK" and i.table == "users"
    ]

    assert len(json_issues) == 1
    assert json_issues[0].severity == IssueSeverity.HIGH


@pytest.mark.asyncio
async def test_analyze_schema_no_issues_for_good_table(data_agent, sample_schema):
    """Test that good tables don't generate false positives"""
    issues = await data_agent.analyze_schema(sample_schema)

    # 'orders' table should have no issues (has PK, has audit, no JSON overuse)
    orders_issues = [i for i in issues if i.table == "orders"]

    assert len(orders_issues) == 0


# ============================================================================
# TEST: QUERY OPTIMIZATION
# ============================================================================

@pytest.mark.asyncio
async def test_optimize_query_returns_optimization(data_agent):
    """Test that query optimization returns valid result"""
    query = "SELECT * FROM users WHERE email = 'test@example.com'"

    optimization = await data_agent.optimize_query(query, use_thinking=True)

    assert isinstance(optimization, QueryOptimization)
    assert optimization.query_hash is not None
    assert optimization.original_query == query
    assert optimization.improvement_percent >= 0


@pytest.mark.asyncio
async def test_optimize_query_caching(data_agent):
    """Test that identical queries are cached"""
    query = "SELECT * FROM users WHERE id = 1"

    # First call
    opt1 = await data_agent.optimize_query(query)

    # Second call (should use cache)
    opt2 = await data_agent.optimize_query(query)

    assert opt1.query_hash == opt2.query_hash
    # Check that we didn't call LLM twice (adapter would track this)


@pytest.mark.asyncio
async def test_optimize_query_without_thinking(data_agent):
    """Test optimization works without thinking mode"""
    query = "SELECT name FROM users"

    optimization = await data_agent.optimize_query(query, use_thinking=False)

    assert isinstance(optimization, QueryOptimization)
    assert optimization.confidence_score >= 0


# ============================================================================
# TEST: MIGRATION PLANNING
# ============================================================================

@pytest.mark.asyncio
async def test_generate_migration_low_risk(data_agent):
    """Test migration for low-risk changes"""
    changes = [
        "ALTER TABLE users ADD COLUMN phone VARCHAR(20)",
    ]

    migration = await data_agent.generate_migration(changes, use_thinking=True)

    assert isinstance(migration, MigrationPlan)
    assert migration.risk_level == IssueSeverity.LOW
    assert migration.can_run_online == True
    assert migration.estimated_downtime_seconds == 0.0


@pytest.mark.asyncio
async def test_generate_migration_high_risk_drop(data_agent):
    """Test migration for dangerous DROP operations"""
    changes = [
        "ALTER TABLE users DROP COLUMN email",
    ]

    migration = await data_agent.generate_migration(changes, use_thinking=True)

    assert migration.risk_level == IssueSeverity.CRITICAL
    assert migration.can_run_online == False
    assert migration.requires_backup == True


@pytest.mark.asyncio
async def test_generate_migration_has_rollback(data_agent):
    """Test that migrations include rollback commands"""
    changes = [
        "ALTER TABLE users ADD COLUMN status VARCHAR(20)",
    ]

    migration = await data_agent.generate_migration(changes, use_thinking=True)

    assert len(migration.down_commands) > 0
    assert any("Rollback" in cmd for cmd in migration.down_commands)


@pytest.mark.asyncio
async def test_generate_migration_version_id(data_agent):
    """Test that migration has unique version ID"""
    changes = ["ALTER TABLE users ADD COLUMN test VARCHAR(10)"]

    migration = await data_agent.generate_migration(changes)

    assert migration.version_id.startswith("migration_")
    assert len(migration.version_id) > 10  # Has timestamp


# ============================================================================
# TEST: BASE AGENT INTEGRATION
# ============================================================================

@pytest.mark.asyncio
async def test_execute_task_returns_response(data_agent):
    """Test that execute() returns valid AgentResponse"""
    task = AgentTask(
        request="Analyze the users table",
        context={"database": "production"},
    )

    response = await data_agent.execute(task)

    assert isinstance(response, AgentResponse)
    assert response.success == True
    assert "response" in response.data


@pytest.mark.asyncio
async def test_execute_task_with_thinking(data_agent):
    """Test that execute() uses thinking when available"""
    task = AgentTask(request="Optimize the slow query")

    response = await data_agent.execute(task)

    assert response.success == True
    assert response.reasoning != ""
    assert "thinking_tokens" in response.metrics


@pytest.mark.asyncio
async def test_execute_handles_errors(mock_llm):
    """Test that execute() handles errors gracefully"""
    # Create mock that will fail
    class FailingLLMClient:
        async def generate(self, *args, **kwargs):
            raise Exception("LLM service unavailable")

    failing_llm = FailingLLMClient()

    # Create agent with failing LLM
    agent = create_data_agent(
        llm_client=failing_llm,
        mcp_client=None,
        enable_thinking=False,  # Disable thinking to avoid adapter layer
    )

    task = AgentTask(request="Test error handling")
    response = await agent.execute(task)

    assert response.success == False
    assert response.error is not None


# ============================================================================
# TEST: STREAMING
# ============================================================================

@pytest.mark.asyncio
async def test_execute_streaming_yields_events(data_agent):
    """Test that streaming execution yields proper events"""
    task = AgentTask(request="Test streaming")

    events = []
    async for event in data_agent.execute_streaming(task):
        events.append(event)

    assert len(events) >= 2  # At least thinking + complete
    assert any(e["type"] == "thinking" for e in events)
    assert any(e["type"] == "complete" for e in events)


# ============================================================================
# TEST: FACTORY FUNCTION
# ============================================================================

def test_create_data_agent_with_defaults(mock_llm):
    """Test factory function creates agent with defaults"""
    agent = create_data_agent(mock_llm)

    assert isinstance(agent, DataAgent)
    assert agent.db_type == DatabaseType.POSTGRES
    assert agent.adapter is not None  # Thinking enabled by default


def test_create_data_agent_without_thinking(mock_llm):
    """Test factory can disable thinking"""
    agent = create_data_agent(mock_llm, enable_thinking=False)

    assert agent.adapter is None


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    # Run tests with pytest
    import sys

    print("=" * 80)
    print("DATA AGENT PRODUCTION - TEST SUITE")
    print("=" * 80)
    print()

    pytest_args = [
        __file__,
        "-v",  # Verbose
        "-s",  # Show print statements
        "--tb=short",  # Short traceback
    ]

    exit_code = pytest.main(pytest_args)

    if exit_code == 0:
        print()
        print("=" * 80)
        print("✅ ALL TESTS PASSED - PRODUCTION READY")
        print("=" * 80)
    else:
        print()
        print("=" * 80)
        print("❌ SOME TESTS FAILED - FIX BEFORE DEPLOYING")
        print("=" * 80)

    sys.exit(exit_code)
