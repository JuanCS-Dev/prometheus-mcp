"""
Prometheus Training on Modal.

Runs the Co-Evolution Loop in the cloud to train the agent.
Persists the learned memory to a Modal Volume.
"""

import modal
import os
import sys
from datetime import datetime

# Define the Modal App
app = modal.App("prometheus-training")

# Define persistence volume for MIRIX memory
volume = modal.Volume.from_name("prometheus-memory", create_if_missing=True)

# Load .env if present
from dotenv import load_dotenv
load_dotenv("/media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli/.env")

# Define the image
image = (
    modal.Image.debian_slim()
    .pip_install("google-generativeai", "rich", "tqdm", "python-dotenv", "httpx")
    .env({"GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", "")})
    .add_local_dir(
        "/media/juan/DATA/projects/GEMINI-CLI-2/qwen-dev-cli",
        remote_path="/root/qwen-dev-cli",
        ignore=["**/.git", "**/__pycache__", "**/.venv", "**/.env", "**/venv"],
    )
)

@app.function(
    image=image,
    volumes={"/data": volume},
    timeout=3600,  # 1 hour max training time
)
async def train_prometheus(num_iterations: int = 10):
    """
    Run the Co-Evolution Loop remotely.
    """
    print(f"🚀 Starting Prometheus Training ({num_iterations} iterations)...")

    # Add project root to path so imports work
    sys.path.append("/root/qwen-dev-cli")

    try:
        from prometheus.core.evolution import CoEvolutionLoop
        from prometheus.core.llm_client import GeminiClient
        from prometheus.memory.memory_system import MemorySystem
        from prometheus.core.reflection import ReflectionEngine
        from prometheus.tools.tool_factory import ToolFactory
        from prometheus.sandbox.executor import SandboxExecutor
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        # Debug: list files
        import subprocess
        subprocess.run(["find", "/root/qwen-dev-cli", "-maxdepth", "3"])
        raise

    # Initialize components
    # Note: In a real scenario, we'd load existing memory from /data
    print("🧠 Initializing Cognitive Engines...")
    llm = GeminiClient()
    memory = MemorySystem()
    reflection = ReflectionEngine(llm, memory)
    sandbox = SandboxExecutor()
    tool_factory = ToolFactory(llm, sandbox)

    # Initialize Evolution Loop
    evolution = CoEvolutionLoop(
        llm_client=llm,
        tool_factory=tool_factory,
        memory_system=memory,
        reflection_engine=reflection,
        sandbox_executor=sandbox,
    )

    # Run Evolution
    print("🧬 Evolving...")
    stats = await evolution.evolve(num_iterations=num_iterations)

    # Export Memory
    print("💾 Persisting Memory...")
    memory_state = memory.export_state()

    # Save to Volume
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"/data/prometheus_memory_{timestamp}.json"

    import json
    with open(filename, "w") as f:
        json.dump(memory_state, f, indent=2)

    # Also save as 'latest'
    with open("/data/prometheus_memory_latest.json", "w") as f:
        json.dump(memory_state, f, indent=2)

    volume.commit()

    print(f"✅ Training Complete! Memory saved to {filename}")
    print(f"📈 Stats: {stats.to_dict()}")

    return stats.to_dict()

@app.local_entrypoint()
def main(iterations: int = 10):
    """
    Local entrypoint to trigger remote training.
    Usage: modal run prometheus/training/modal_train.py --iterations 20
    """
    print(f"Triggering remote training for {iterations} iterations...")
    stats = train_prometheus.remote(num_iterations=iterations)
    print("Remote training finished.")
    print(stats)
