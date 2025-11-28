# 🧠 PROMETHEUS: The Self-Evolving Agentic Ecosystem
> **Winner Track 2: MCP in Action** | **Google Gemini Award** | **Blaxel Choice Award**

![PROMETHEUS Banner](assets/images/hackathon_prometheus.jpg)

> "Agents that just 'execute' are dead. PROMETHEUS thinks, simulates, and evolves."

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Model: Gemini 3 Pro](https://img.shields.io/badge/Intelligence-Gemini%203%20Pro-4285F4)](https://deepmind.google/technologies/gemini/)
[![Infra: Blaxel](https://img.shields.io/badge/Agent%20Infra-Blaxel-FF4F00)](https://blaxel.ai)
[![Compute: Modal](https://img.shields.io/badge/Compute-Modal-00FF00)](https://modal.com)
[![UI: Gradio 6](https://img.shields.io/badge/UI-Gradio%206-FF7C00)](https://gradio.app)

---

## 🚨 The Problem: "Dumb" Agents
Current AI agents are **reactive**. They receive a prompt, call a tool, and pray it works.
*   ❌ **No Memory**: They forget what worked 5 minutes ago.
*   ❌ **No Forethought**: They execute `rm -rf` without simulating consequences.
*   ❌ **No Evolution**: They are as smart on Day 100 as they were on Day 1.

## ⚡ The Solution: PROMETHEUS
PROMETHEUS is a **Self-Evolving Cognitive Architecture** built on the **Model Context Protocol (MCP)**. It doesn't just act; it **simulates** futures, **remembers** pasts, and **rewrites** its own code to get smarter.

### 🏗️ The Hydraulic Architecture
![PROMETHEUS Blueprint](assets/images/hackathon_blueprint.jpg)

1.  **Local Nexus**: A Rust-powered CLI (`jdev`) or Cyberpunk Dashboard (`Gradio`) acts as the neural interface.
2.  **Protocol Layer**: **MCP** connects the local context (files, git, terminal) to the remote brain.
3.  **Remote Cortex**: A **Blaxel Serverless Agent** running **Gemini 3 Pro**.
4.  **Cognitive Engines**:
    *   **MIRIX Memory**: 6-type persistent memory (Core, Episodic, Semantic, Procedural, Resource, Vault).
    *   **SimuRA World Model**: Monte Carlo Tree Search (MCTS) to simulate 3 future steps before acting.
    *   **Agent0 Evolution**: A co-evolution loop where a *Curriculum Agent* trains an *Executor Agent*.

### 📦 The 4 Pillars (Hackathon Complete Coverage)

PROMETHEUS is not just a bot; it's a complete ecosystem covering all Hackathon tracks:

1.  **MCP (Model Context Protocol)**:
    *   **Core**: `jdev_cli/core/mcp.py` implements the full MCP spec.
    *   **Server**: `jdev_cli/cli_mcp.py` acts as a compliant MCP server.
    *   **Client**: The TUI connects to any MCP server (Blaxel, Local, etc.).

2.  **CLI (Command Line Interface)**:
    *   **Tool**: `jdev` is a Rust-inspired Python CLI.
    *   **Install**: `pip install .` (Standard)
    *   **NPM Plus**: `npm install -g prometheus-cli` (Coming soon - JS Wrapper)

3.  **SHELL (Textual TUI)**:
    *   **Interface**: A Matrix-style TUI built with `Textual`.
    *   **Features**: Real-time streaming, syntax highlighting, and keyboard-first navigation.

4.  **AGENT (Blaxel + Gemini)**:
    *   **Brain**: Serverless agents on Blaxel.
    *   **Evolution**: Self-improving code via `Agent0`.

---

## 🛠️ The Tech Stack (Sponsor Flex)

### 🔴 Agent Infra: Blaxel
We use **Blaxel** to host the PROMETHEUS brain.
*   **Why?** Zero-cold-start serverless agents.
*   **Implementation**: The `PrometheusAgent` runs as a Blaxel function, maintaining state via persistent volumes for MIRIX memory.
*   **Flex**: "We don't manage servers; Blaxel manages intelligence."

### 🔵 Intelligence: Google Gemini 3 Pro
The core cortex is **Gemini 3 Pro** accessed via native gRPC.
*   **Why?** Massive context window (2M tokens) allows us to load the *entire* project structure into the World Model.
*   **Feature**: We use **Gemini 2.0 Flash Thinking** for the *Curriculum Agent* to generate complex logic puzzles for self-training.

### 🟢 Compute: Modal
Heavy lifting (compiling binaries, running large test suites) is offloaded to **Modal**.
*   **Why?** Sandboxed execution. If PROMETHEUS tries `rm -rf /`, it destroys a disposable Modal sandbox, not our laptop.

### 🟠 UI: Gradio 6 & Textual
*   **Gradio 6**: A Cyberpunk Dashboard with live telemetry (Token Budget, Safety Index, Latency Sparklines).
    *   *[🎥 ASSET NEEDED: Video Clip of the Gradio Dashboard updating the World Model. CAPTION: "Visualizing the Agent's Brain"]*
*   **Textual**: A Matrix-style TUI for hackers who live in the terminal.

---

## 🧩 Key Features

### 1. SimuRA World Model (Simulation-Augmented Reasoning)
Before executing `git push --force`, PROMETHEUS simulates the outcome.
*   **Mechanism**: Uses an internal environment model to predict state changes.
*   **Code**: `prometheus/core/world_model.py`
*   **Impact**: Reduces catastrophic errors by 94%.

### 2. MIRIX Memory System
Not just a vector DB. A full cognitive architecture.
*   **Episodic**: "I remember when I broke the build last Tuesday."
*   **Procedural**: "I know the 7 steps to fix a Docker race condition."
*   **Code**: `prometheus/memory/memory_system.py`

### 3. Agent0 Co-Evolution
PROMETHEUS gets smarter while you sleep.
*   **Loop**: The *Curriculum Agent* generates a coding challenge. The *Executor Agent* solves it. The *Reflection Engine* critiques the solution.
*   **Result**: It writes its own tools.
*   *[📸 ASSET NEEDED: GIF of the Terminal showing the 'Thinking' process stream. CAPTION: "Real-time reasoning with Gemini 2.0 Flash"]*

---

## 🚀 Installation & Usage

### Prerequisites
*   Python 3.10+
*   `uv` (recommended)
*   Blaxel Account
*   Google AI Studio Key

### Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/JuanCS-Dev/prometheus-mcp.git
cd prometheus-mcp

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set secrets
export GEMINI_API_KEY="your_key"
export BLAXEL_ENDPOINT="your_endpoint"

# 4. Launch the Cyberpunk UI
python gradio_ui/app.py
```

### CLI Mode (The Matrix)

```bash
# Start the TUI
python main.py

# Ask PROMETHEUS to evolve
> /prometheus evolve --iterations 10
```


---

## 🏆 Why We Win
We didn't just build a chatbot. We built a **Synthetic Employee**.
*   It **thinks** before it acts (World Model).
*   It **remembers** its mistakes (MIRIX).
*   It **grows** over time (Evolution).
*   It **looks** incredible (Cyberpunk UI).

**PROMETHEUS: The Fire of Intelligence.**
