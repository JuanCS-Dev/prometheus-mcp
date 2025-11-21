"""Hero section component - Emotional entry point."""
import gradio as gr


def create_hero_section():
    """
    Create hero section with emotional impact.
    
    Design goals:
    - Immediate "wow" factor
    - Clear value proposition
    - Inviting call-to-action
    """
    gr.HTML(
        """
        <div class="hero-section" style="
            text-align: center;
            padding: 60px 20px;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(6, 182, 212, 0.2));
            border-radius: 24px;
            margin-bottom: 40px;
        ">
            <div class="hero-title" style="
                font-size: 3.5rem;
                font-weight: 700;
                background: linear-gradient(135deg, #3b82f6, #06b6d4);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 16px;
                display: inline-block;
            ">
                🚀 QWEN-DEV-CLI
            </div>
            <div class="hero-subtitle" style="
                font-size: 1.25rem;
                color: #94a3b8;
                margin-bottom: 16px;
            ">
                Your AI-Powered Development Partner
            </div>
            <p style="color: #64748b; font-size: 1rem; margin: 0;">
                Multi-language LSP • Smart Refactoring • Context-Aware Suggestions
            </p>
        </div>
        """
    )
