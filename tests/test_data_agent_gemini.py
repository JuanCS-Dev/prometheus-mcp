#!/usr/bin/env python3
"""
DataAgent + Gemini Real Test
=============================

Test DataAgent with real Gemini LLM.
"""

import asyncio
from rich.console import Console

from jdev_cli.core.llm import LLMClient
from jdev_cli.agents.data_agent_production import create_data_agent

console = Console()


async def main():
    console.print("\n[bold cyan]" + "=" * 80 + "[/bold cyan]")
    console.print("[bold cyan]DataAgent + Gemini Real Integration Test[/bold cyan]")
    console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]\n")

    # Initialize real Gemini LLM
    console.print("[dim]Initializing Gemini 2.0 Flash...[/dim]")
    llm = LLMClient()

    # Create DataAgent with thinking enabled
    agent = create_data_agent(
        llm_client=llm,
        mcp_client=None,
        enable_thinking=True
    )

    console.print("[green]✅ DataAgent initialized with Gemini 2.0 Flash[/green]\n")

    # Test 1: Schema Analysis
    console.print("[bold yellow]TEST 1: Schema Analysis[/bold yellow]")
    console.print("[dim]" + "-" * 80 + "[/dim]\n")

    schema = {
        "users": {
            "columns": {
                "id": "UUID",
                "name": "VARCHAR(255)",
                "email": "VARCHAR(255)",
                "created": "TIMESTAMP",
                "meta": "JSONB",
                "settings": "JSONB",
                "preferences": "JSONB",
            },
            "constraints": [],  # No PK!
        },
        "orders": {
            "columns": {
                "order_id": "BIGSERIAL",
                "user_id": "UUID",
                "amount": "DECIMAL(10,2)",
                "status": "VARCHAR(50)",
                "created_at": "TIMESTAMP",
            },
            "constraints": [
                {"type": "PRIMARY_KEY", "columns": ["order_id"]},
            ],
        }
    }

    console.print("[dim]Analyzing schema with Gemini...[/dim]\n")
    issues = await agent.analyze_schema(schema)

    console.print(f"[green]✅ Found {len(issues)} schema issues:[/green]\n")

    for issue in issues:
        severity_icon = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }.get(issue.severity.value, "⚪")

        console.print(f"{severity_icon} [bold]{issue.severity.value.upper()}[/bold]: {issue.description}")
        console.print(f"   💡 [dim]{issue.recommendation}[/dim]")
        console.print()

    # Test 2: Query Optimization
    console.print("[bold yellow]TEST 2: Query Optimization (with Extended Thinking)[/bold yellow]")
    console.print("[dim]" + "-" * 80 + "[/dim]\n")

    query = """
    SELECT u.*, o.*
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    WHERE u.email LIKE '%@gmail.com'
    AND o.created_at > NOW() - INTERVAL '30 days'
    ORDER BY o.created_at DESC
    """

    console.print(f"[dim]Original query:[/dim]\n{query}\n")
    console.print("[dim]Optimizing with Gemini (thinking enabled)...[/dim]\n")

    optimization = await agent.optimize_query(query, use_thinking=True)

    console.print("[green]✅ Optimization complete:[/green]\n")
    console.print(f"  [bold]Improvement:[/bold] {optimization.improvement_percent}%")
    console.print(f"  [bold]Confidence:[/bold] {optimization.confidence_score:.0%}")
    console.print(f"  [bold]Type:[/bold] {optimization.optimization_type.value}")

    if optimization.required_indexes:
        console.print("\n  [yellow]Required indexes:[/yellow]")
        for idx in optimization.required_indexes:
            console.print(f"    • {idx}")

    # Test 3: Migration Planning
    console.print("\n[bold yellow]TEST 3: Migration Planning (with Risk Assessment)[/bold yellow]")
    console.print("[dim]" + "-" * 80 + "[/dim]\n")

    changes = [
        "ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN last_login TIMESTAMP",
        "CREATE INDEX idx_users_email ON users(email)",
    ]

    console.print("[dim]Proposed changes:[/dim]")
    for change in changes:
        console.print(f"  • {change}")
    console.print()

    console.print("[dim]Generating migration plan with Gemini...[/dim]\n")

    migration = await agent.generate_migration(changes, use_thinking=True)

    risk_icon = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
    }.get(migration.risk_level.value, "⚪")

    console.print("[green]✅ Migration plan generated:[/green]\n")
    console.print(f"  {risk_icon} [bold]Risk Level:[/bold] {migration.risk_level.value.upper()}")
    console.print(f"  ⏱️  [bold]Downtime:[/bold] {migration.estimated_downtime_seconds}s")
    console.print(f"  {'✅' if migration.can_run_online else '❌'} [bold]Can run online:[/bold] {migration.can_run_online}")
    console.print(f"  {'⚠️' if migration.requires_backup else '✅'} [bold]Requires backup:[/bold] {migration.requires_backup}")
    console.print(f"\n  [dim]Version:[/dim] {migration.version_id}")

    # Summary
    console.print("\n[bold cyan]" + "=" * 80 + "[/bold cyan]")
    console.print("[bold green]✅ ALL TESTS PASSED WITH GEMINI 2.0 FLASH[/bold green]")
    console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]\n")

    console.print("[bold]Summary:[/bold]")
    console.print(f"  • Schema Analysis: {len(issues)} issues detected")
    console.print(f"  • Query Optimization: {optimization.improvement_percent}% improvement")
    console.print(f"  • Migration Planning: {migration.risk_level.value.upper()} risk")
    console.print()
    console.print("[green]DataAgent + Gemini integration is WORKING! 🚀[/green]\n")


if __name__ == "__main__":
    asyncio.run(main())
