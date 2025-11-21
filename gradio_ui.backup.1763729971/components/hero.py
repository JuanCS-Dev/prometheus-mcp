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
        <div style="
            text-align: center;
            padding: 56px 32px;
            background: #FFFFFF;
            border: 0.5px solid #D2D2D7;
            border-radius: 12px;
            margin-bottom: 28px;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        ">
            <div style="
                font-size: 44px;
                font-weight: 700;
                color: #1D1D1F;
                margin-bottom: 14px;
                letter-spacing: -0.03em;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
            ">
                QWEN-DEV-CLI
            </div>
            <div style="
                font-size: 19px;
                color: #6E6E73;
                margin-bottom: 6px;
                font-weight: 400;
                line-height: 1.4;
            ">
                AI-Powered Development Partner
            </div>
            <div style="
                font-size: 14px;
                color: #86868B;
                display: flex;
                gap: 10px;
                justify-content: center;
                flex-wrap: wrap;
                margin-top: 18px;
                font-weight: 400;
            ">
                <span>Multi-language LSP</span>
                <span>•</span>
                <span>Smart Refactoring</span>
                <span>•</span>
                <span>Context-Aware AI</span>
            </div>
        </div>
        """
    )
