"""
Componentes SVG/HTML para Dashboard Cyberpunk - VISUAL ATUALIZADO
Réplica pixel-perfect da imagem de referência com glassmorphism neon.
"""
from __future__ import annotations

from typing import List


def render_tailwind_header() -> str:
    """Injeta Tailwind CDN + custom theme variables"""
    return """
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
      :root {
        --cyber-bg: #0A0E14;
        --cyber-panel: #141922;
        --cyber-accent: #00D9FF;
        --cyber-text: #E6E6E6;
        --cyber-muted: #8A8A8A;
      }
      
      * { 
        box-sizing: border-box;
      }
      
      body {
        background-color: var(--cyber-bg);
        color: var(--cyber-text);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'JetBrains Mono', monospace;
      }
    </style>
    <script>
      tailwind.config = {
        darkMode: 'class',
        theme: {
          extend: {
            colors: {
              'cyber-bg': '#0A0E14',
              'cyber-panel': '#141922',
              'cyber-accent': '#00D9FF',
              'cyber-accent-light': '#00F0FF',
              'cyber-text': '#E6E6E6',
              'cyber-muted': '#8A8A8A',
            },
            backgroundImage: {
              'gradient-neon': 'linear-gradient(135deg, #00D9FF 0%, #00A8CC 100%)',
            }
          }
        }
      }
    </script>
    """


def render_gauge(percentage: float, label: str, max_value: str) -> str:
    """
    Gauge circular SVG com neon glow - IDÊNTICO À IMAGEM
    
    Características:
    - Stroke dinâmico baseado em percentual
    - Sombra de neon brilhante
    - Texto em uppercase com glow
    - Cores: Cyan por padrão, Orange/Red em warning
    """
    percentage = max(0.0, min(100.0, percentage))

    radius = 60
    circumference = 2 * 3.14159 * radius
    offset = circumference - (percentage / 100) * circumference

    # Cor dinâmica baseada no percentual
    if percentage >= 90:
        stroke_color = "#EF4444"  # Red
        glow_color = "rgba(239, 68, 68, 0.8)"
    elif percentage >= 75:
        stroke_color = "#F59E0B"  # Orange
        glow_color = "rgba(245, 158, 11, 0.8)"
    else:
        stroke_color = "#00D9FF"  # Cyan
        glow_color = "rgba(0, 217, 255, 0.8)"

    return f"""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 16px;">
        <div style="position: relative; width: 140px; height: 140px;">
            <svg width="140" height="140" style="transform: rotate(-90deg); filter: drop-shadow(0 0 20px {glow_color});">
                <!-- Background circle -->
                <circle cx="70" cy="70" r="{radius}"
                        fill="none" stroke="rgba(255, 255, 255, 0.08)" stroke-width="8"/>
                <!-- Progress circle -->
                <circle cx="70" cy="70" r="{radius}"
                        fill="none" stroke="{stroke_color}" stroke-width="8"
                        stroke-dasharray="{circumference}"
                        stroke-dashoffset="{offset}"
                        stroke-linecap="round"
                        style="transition: stroke-dashoffset 1s cubic-bezier(0.34, 1.56, 0.64, 1);"/>
            </svg>
            <!-- Centered text -->
            <div style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                <span style="font-size: 32px; font-weight: 700; color: {stroke_color}; 
                            text-shadow: 0 0 10px {stroke_color}, 0 0 20px rgba(0, 217, 255, 0.5);
                            letter-spacing: 2px;">{int(percentage)}%</span>
            </div>
        </div>
        <h3 style="font-size: 11px; font-family: 'Courier New', monospace; color: var(--cyber-text); 
                   margin-top: 12px; margin-bottom: 4px; letter-spacing: 3px; font-weight: 600;
                   text-shadow: 0 0 5px rgba(0, 217, 255, 0.6);">
            {label.upper()}
        </h3>
        <p style="font-size: 10px; color: var(--cyber-muted); font-family: 'Courier New', monospace;
                  margin: 0; letter-spacing: 1px;">
            {max_value}
        </p>
    </div>
    """


def render_bar_chart(values: List[float], label: str) -> str:
    """
    Gráfico de barras estilo equalizer - IDÊNTICO À IMAGEM
    
    Características:
    - 6 barras verticais (Safety Index CPI)
    - Gradient cyan to darker cyan
    - Hover effect com brilho
    - Responsive height baseada em valores
    """
    max_val = max(values) if values else 1.0

    bars_html = ""
    for i, val in enumerate(values):
        # Normalizar valor para 0-1
        norm_val = val / max_val if max_val > 0 else 0.5
        height_percent = norm_val * 100

        # Cores degradadas cyan
        bars_html += f"""
        <div style="display: flex; align-items: flex-end; justify-content: center; 
                    width: 14px; height: 60px; margin: 0 3px; group: hover;">
            <div style="width: 100%; height: {height_percent}%; 
                       background: linear-gradient(to top, #00D9FF, #00A8CC);
                       border-radius: 2px 2px 0 0;
                       box-shadow: 0 0 10px rgba(0, 217, 255, 0.6);
                       transition: all 0.3s ease;
                       opacity: {0.6 + norm_val * 0.4};"
                   onmouseover="this.style.boxShadow='0 0 20px rgba(0, 217, 255, 1)'; this.style.opacity='1';"
                   onmouseout="this.style.boxShadow='0 0 10px rgba(0, 217, 255, 0.6)'; this.style.opacity='{0.6 + norm_val * 0.4}';">
            </div>
        </div>
        """

    return f"""
    <div style="display: flex; flex-direction: column; justify-content: flex-end; height: 100%; padding: 12px;">
        <!-- Bars container -->
        <div style="display: flex; justify-content: space-around; align-items: flex-end; height: 70px; margin-bottom: 8px;">
            {bars_html}
        </div>
        <!-- Label -->
        <h3 style="font-size: 11px; font-family: 'Courier New', monospace; color: var(--cyber-text);
                   text-align: center; margin: 4px 0; letter-spacing: 2px; font-weight: 600;
                   text-shadow: 0 0 5px rgba(0, 217, 255, 0.6);">
            {label.upper()}
        </h3>
        <!-- Scale indicator -->
        <div style="display: flex; justify-content: space-between; font-size: 9px; color: var(--cyber-muted);
                    font-family: 'Courier New', monospace; margin-top: 4px;">
            <span>SAFE</span>
            <span style="font-size: 8px; color: rgba(138, 138, 138, 0.6);">45ms</span>
            <span>RISK</span>
        </div>
    </div>
    """


def render_dual_gauge(left_val: float, left_label: str, right_val: float, right_label: str) -> str:
    """
    Dois mini gauges lado a lado - IDÊNTICO À IMAGEM
    
    Características:
    - Mini SVG circulares com 20px radius
    - Cores: Cyan (esquerda), Verde (direita)
    - Porcentagem centralizada
    - Labels pequenos embaixo
    """
    def mini_gauge_svg(val: float, label: str, color: str) -> str:
        val = max(0.0, min(100.0, val))
        radius = 18
        circ = 2 * 3.14159 * radius
        off = circ * (1 - val/100)

        return f"""
        <div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
            <div style="position: relative; width: 56px; height: 56px;">
                <svg width="56" height="56" style="filter: drop-shadow(0 0 8px {color}40);">
                    <circle cx="28" cy="28" r="{radius}" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="3"/>
                    <circle cx="28" cy="28" r="{radius}" fill="none" stroke="{color}" stroke-width="3"
                            stroke-dasharray="{circ}" stroke-dashoffset="{off}" 
                            stroke-linecap="round" style="transition: stroke-dashoffset 0.8s ease-out;
                            filter: drop-shadow(0 0 6px {color}80);"/>
                </svg>
                <div style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
                           font-size: 16px; font-weight: 700; color: {color};
                           text-shadow: 0 0 8px {color};">
                    {int(val)}
                </div>
            </div>
            <span style="font-size: 10px; color: rgba(138, 138, 138, 0.9); font-family: 'Courier New', monospace;
                        text-align: center; letter-spacing: 1px;">
                {label}
            </span>
        </div>
        """

    return f"""
    <div style="display: flex; justify-content: space-around; align-items: center; height: 100%; padding: 8px;">
        {mini_gauge_svg(left_val, left_label.upper(), "#00D9FF")}
        <div style="width: 1px; height: 40px; background: rgba(0, 217, 255, 0.2);"></div>
        {mini_gauge_svg(right_val, right_label.upper(), "#10B981")}
    </div>
    """


def render_terminal_logs(logs: List[str]) -> str:
    """
    Logs em estilo terminal com syntax highlighting - IDÊNTICO À IMAGEM
    
    Color scheme:
    - [INFO]    -> Cyan blue (#3B82F6)
    - [SUCCESS] -> Green (#10B981)
    - [ERROR]   -> Red (#EF4444)
    - [WARN]    -> Orange (#F59E0B)
    - Timestamp -> Muted gray
    - Cursor    -> Cyan pulsante
    """
    log_lines = ""

    for log in (logs or [])[-15:]:  # Últimas 15 linhas
        # Extrair nível e cores
        color_class = "text-gray-400"

        if "[INFO]" in log:
            color_class = "text-blue-400"
        elif "[SUCCESS]" in log:
            color_class = "text-green-400"
        elif "[ERROR]" in log:
            color_class = "text-red-400"
        elif "[WARN]" in log:
            color_class = "text-yellow-400"

        # Colorir timestamp separadamente
        parts = log.split(" - ", 1)
        if len(parts) == 2:
            timestamp, message = parts
            log_lines += f"""
            <div style="margin-bottom: 2px; font-family: 'Courier New', monospace; font-size: 11px;">
                <span style="color: rgba(138, 138, 138, 0.7);">{timestamp}</span>
                <span style="margin: 0 4px; color: rgba(138, 138, 138, 0.5);">-</span>
                <span style="color: {
                    '#3B82F6' if '[INFO]' in log else
                    '#10B981' if '[SUCCESS]' in log else
                    '#EF4444' if '[ERROR]' in log else
                    '#F59E0B' if '[WARN]' in log else
                    'var(--cyber-text)'
                };">{message}</span>
            </div>
            """
        else:
            log_lines += f"""
            <div style="margin-bottom: 2px; font-family: 'Courier New', monospace; font-size: 11px; color: {color_class};">
                {log}
            </div>
            """

    return f"""
    <div style="background: rgba(0, 0, 0, 0.6); border: 1px solid rgba(0, 217, 255, 0.2); 
                border-radius: 4px; padding: 8px; font-family: 'Courier New', monospace; 
                max-height: 160px; overflow-y: auto; font-size: 11px;">
        {log_lines}
        <div style="color: var(--cyber-accent); font-size: 10px; margin-top: 4px;">
            <span>root@gemini-cli:~$</span>
            <span style="margin-left: 4px; animation: blink 1s infinite;">█</span>
        </div>
    </div>
    <style>
        @keyframes blink {{
            0%, 49% {{ opacity: 1; }}
            50%, 100% {{ opacity: 0; }}
        }}
    </style>
    """


def render_docker_progress(percentage: float, label: str = "Processing") -> str:
    """
    Progress bar estilo Docker build - Hackathon Visual

    Características:
    - Barra horizontal com gradient cyan
    - Percentual centralizado
    - Glow neon
    - Animação suave na transição
    """
    percentage = max(0.0, min(100.0, percentage))

    return f"""
    <div class="docker-progress">
        <div class="docker-progress-bar" style="width: {percentage}%;"></div>
        <div class="docker-progress-text">{label} - {percentage:.0f}%</div>
    </div>
    """


def render_latency_chart(values: List[int], current: str = "0ms") -> str:
    """
    Sparkline chart para latência - Hackathon Visual

    Características:
    - Barras verticais estilo sparkline
    - Última barra destacada em laranja
    - Altura proporcional ao valor
    - Hover com glow
    """
    if not values:
        values = [0]

    max_val = max(values) if values else 1
    bars = ""

    for i, v in enumerate(values):
        height = int((v / max_val) * 40) if max_val > 0 else 4
        # Última barra em laranja, resto em cyan
        color = "#f59e0b" if i == len(values) - 1 else "#00D9FF"
        bars += f'<div class="latency-bar" style="height: {height}px; background: linear-gradient(180deg, {color} 0%, {color}99 100%);"></div>'

    return f"""
    <div style="padding: 8px;">
        <div class="latency-label">Latency (ms)</div>
        <div class="latency-chart">{bars}</div>
        <div class="latency-value">{current}</div>
    </div>
    """


def render_dual_status(model: str, env: str) -> str:
    """
    Status cards lado a lado - Hackathon Visual

    Características:
    - Dois cards com labels
    - Model em cyan, Environment em verde
    - Layout grid responsivo
    - Estilo minimalista
    """
    return f"""
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 8px;">
        <div class="status-card">
            <div class="status-card-label">Model</div>
            <div class="status-card-value status-card-value-cyan">{model}</div>
        </div>
        <div class="status-card status-card-green">
            <div class="status-card-label">Environment</div>
            <div class="status-card-value status-card-value-green">{env}</div>
        </div>
    </div>
    """


def render_memory_status(memory_data: dict) -> str:
    """
    Render MIRIX Memory System status.
    
    Visualizes 6 memory types with active/inactive indicators.
    """
    types = ["episodic", "semantic", "procedural", "core", "resource", "vault"]
    active_types = memory_data.get("active_types", [])

    grid_html = ""
    for mtype in types:
        is_active = mtype in active_types
        color = "#00D9FF" if is_active else "#4B5563"
        glow = f"box-shadow: 0 0 8px {color};" if is_active else ""

        grid_html += f"""
        <div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
            <div style="width: 12px; height: 12px; border-radius: 50%; background-color: {color}; {glow}"></div>
            <span style="font-size: 9px; color: var(--cyber-muted); font-family: 'Courier New', monospace;">{mtype.upper()}</span>
        </div>
        """

    return f"""
    <div style="padding: 8px;">
        <h3 style="font-size: 11px; font-family: 'Courier New', monospace; color: var(--cyber-text); margin-bottom: 8px;">MIRIX MEMORY</h3>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
            {grid_html}
        </div>
    </div>
    """


def render_world_model_status(wm_data: dict) -> str:
    """
    Render SimuRA World Model status.
    
    Shows simulation depth and confidence.
    """
    depth = wm_data.get("simulation_depth", 0)
    confidence = wm_data.get("confidence", 0.0)

    return f"""
    <div style="padding: 8px;">
        <h3 style="font-size: 11px; font-family: 'Courier New', monospace; color: var(--cyber-text); margin-bottom: 8px;">WORLD MODEL</h3>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <span style="font-size: 10px; color: var(--cyber-muted);">DEPTH</span>
            <span style="font-size: 10px; color: var(--cyber-accent);">{depth} steps</span>
        </div>
        <div style="width: 100%; height: 4px; background: #1F2937; border-radius: 2px;">
            <div style="width: {min(100, depth*20)}%; height: 100%; background: var(--cyber-accent); border-radius: 2px;"></div>
        </div>
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; margin-bottom: 4px;">
            <span style="font-size: 10px; color: var(--cyber-muted);">CONFIDENCE</span>
            <span style="font-size: 10px; color: #10B981;">{int(confidence*100)}%</span>
        </div>
        <div style="width: 100%; height: 4px; background: #1F2937; border-radius: 2px;">
            <div style="width: {confidence*100}%; height: 100%; background: #10B981; border-radius: 2px;"></div>
        </div>
    </div>
    """


def render_evolution_status(evo_data: dict) -> str:
    """
    Render Agent0 Evolution status.
    
    Shows current generation and mutation rate.
    """
    generation = evo_data.get("generation", 1)
    mutation_rate = evo_data.get("mutation_rate", 0.0)

    return f"""
    <div style="padding: 8px;">
        <h3 style="font-size: 11px; font-family: 'Courier New', monospace; color: var(--cyber-text); margin-bottom: 8px;">EVOLUTION</h3>
        <div style="display: flex; justify-content: space-between;">
            <div style="text-align: center;">
                <div style="font-size: 16px; font-weight: bold; color: #F59E0B;">v{generation}.0</div>
                <div style="font-size: 9px; color: var(--cyber-muted);">GEN</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 16px; font-weight: bold; color: #8B5CF6;">{mutation_rate:.2f}</div>
                <div style="font-size: 9px; color: var(--cyber-muted);">MUTATION</div>
            </div>
        </div>
    </div>
    """
