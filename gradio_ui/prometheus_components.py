"""
PROMETHEUS Dashboard Components for Gradio UI.

Render functions for Memory, World Model, and Evolution panels.
"""

from typing import Dict, Any


def render_memory_panel(memory_status: Dict[str, Any]) -> str:
    """
    Render Memory System (MIRIX) panel as HTML.

    Args:
        memory_status: Memory system status from PROMETHEUS

    Returns:
        HTML string for Gradio display
    """
    if not memory_status:
        return """
        <div class="prometheus-panel memory-panel">
            <h4>Memory System (MIRIX)</h4>
            <p class="status-inactive">Not initialized</p>
        </div>
        """

    # Extract memory counts
    episodic = memory_status.get("episodic_count", 0)
    semantic = memory_status.get("semantic_count", 0)
    procedural = memory_status.get("procedural_count", 0)
    vault = memory_status.get("vault_count", 0)
    total = episodic + semantic + procedural + vault

    return f"""
    <div class="prometheus-panel memory-panel">
        <h4>Memory System (MIRIX)</h4>
        <div class="memory-stats">
            <div class="stat-row">
                <span class="stat-label">Episodic:</span>
                <span class="stat-value">{episodic}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Semantic:</span>
                <span class="stat-value">{semantic}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Procedural:</span>
                <span class="stat-value">{procedural}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Vault:</span>
                <span class="stat-value">{vault}</span>
            </div>
            <div class="stat-row total">
                <span class="stat-label">Total:</span>
                <span class="stat-value">{total}</span>
            </div>
        </div>
    </div>
    """


def render_world_model_preview(world_model_status: Dict[str, Any]) -> str:
    """
    Render World Model (SimuRA) panel as HTML.

    Args:
        world_model_status: World model status from PROMETHEUS

    Returns:
        HTML string for Gradio display
    """
    if not world_model_status:
        return """
        <div class="prometheus-panel world-model-panel">
            <h4>World Model (SimuRA)</h4>
            <p class="status-inactive">Not initialized</p>
        </div>
        """

    simulations = world_model_status.get("total_simulations", 0)
    accuracy = world_model_status.get("prediction_accuracy", 0)
    last_sim = world_model_status.get("last_simulation", "None")

    accuracy_color = "#00ff00" if accuracy >= 0.8 else "#ffaa00" if accuracy >= 0.5 else "#ff4444"

    return f"""
    <div class="prometheus-panel world-model-panel">
        <h4>World Model (SimuRA)</h4>
        <div class="world-model-stats">
            <div class="stat-row">
                <span class="stat-label">Simulations:</span>
                <span class="stat-value">{simulations}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Accuracy:</span>
                <span class="stat-value" style="color: {accuracy_color}">
                    {accuracy*100:.1f}%
                </span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Last:</span>
                <span class="stat-value small">{str(last_sim)[:30]}...</span>
            </div>
        </div>
    </div>
    """


def render_evolution_progress(evolution_status: Dict[str, Any]) -> str:
    """
    Render Evolution (Agent0) panel as HTML.

    Args:
        evolution_status: Evolution status from PROMETHEUS

    Returns:
        HTML string for Gradio display
    """
    if not evolution_status:
        return """
        <div class="prometheus-panel evolution-panel">
            <h4>Evolution (Agent0)</h4>
            <p class="status-inactive">Not initialized</p>
        </div>
        """

    iterations = evolution_status.get("total_iterations", 0)
    frontier = evolution_status.get("frontier_level", 0)
    improvements = evolution_status.get("improvements", [])
    score = evolution_status.get("capability_score", 0)

    # Progress bar
    progress_pct = min(score * 100, 100)

    return f"""
    <div class="prometheus-panel evolution-panel">
        <h4>Evolution (Agent0)</h4>
        <div class="evolution-stats">
            <div class="stat-row">
                <span class="stat-label">Iterations:</span>
                <span class="stat-value">{iterations}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Frontier:</span>
                <span class="stat-value">Level {frontier}</span>
            </div>
            <div class="progress-container">
                <div class="progress-bar" style="width: {progress_pct}%"></div>
                <span class="progress-label">{progress_pct:.0f}%</span>
            </div>
        </div>
    </div>
    """


def render_thinking_process(thinking_data: Dict[str, Any]) -> str:
    """
    Render PROMETHEUS thinking process for debugging/transparency.

    Args:
        thinking_data: Thinking/reasoning data from PROMETHEUS

    Returns:
        HTML string showing the thinking process
    """
    if not thinking_data:
        return ""

    thought = thinking_data.get("thought", "")
    action = thinking_data.get("action", "")
    confidence = thinking_data.get("confidence", 0)

    return f"""
    <div class="thinking-process">
        <details>
            <summary>Thinking Process ({confidence*100:.0f}% confidence)</summary>
            <div class="thought-content">
                <p><strong>Thought:</strong> {thought}</p>
                <p><strong>Action:</strong> {action}</p>
            </div>
        </details>
    </div>
    """


def get_prometheus_css() -> str:
    """Get CSS styles for PROMETHEUS components."""
    return """
    .prometheus-panel {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #ff6600;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
    }

    .prometheus-panel h4 {
        color: #ff6600;
        margin: 0 0 10px 0;
        font-size: 14px;
        text-transform: uppercase;
    }

    .stat-row {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        border-bottom: 1px solid rgba(255, 102, 0, 0.2);
    }

    .stat-row.total {
        border-top: 2px solid #ff6600;
        border-bottom: none;
        margin-top: 8px;
        padding-top: 8px;
    }

    .stat-label {
        color: #888;
        font-size: 12px;
    }

    .stat-value {
        color: #fff;
        font-weight: bold;
        font-size: 12px;
    }

    .stat-value.small {
        font-size: 10px;
        font-weight: normal;
    }

    .status-inactive {
        color: #666;
        font-style: italic;
        font-size: 12px;
    }

    .progress-container {
        background: #333;
        border-radius: 4px;
        height: 20px;
        margin-top: 8px;
        position: relative;
        overflow: hidden;
    }

    .progress-bar {
        background: linear-gradient(90deg, #ff6600, #ff9900);
        height: 100%;
        transition: width 0.3s ease;
    }

    .progress-label {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        color: #fff;
        font-size: 11px;
        font-weight: bold;
    }

    .thinking-process {
        background: rgba(255, 102, 0, 0.1);
        border-left: 3px solid #ff6600;
        padding: 8px;
        margin: 8px 0;
        font-size: 12px;
    }

    .thinking-process summary {
        cursor: pointer;
        color: #ff6600;
    }

    .thought-content {
        padding: 8px;
        color: #aaa;
    }
    """
