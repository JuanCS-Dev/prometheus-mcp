#!/usr/bin/env python3
"""
🎨 Visual Test - Valida CSS está 100% carregado
Tira screenshots e verifica estilos computados
"""

import time
import subprocess
import signal
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

# Configurações
URL = "http://0.0.0.0:7861"
SCREENSHOT_DIR = Path("test_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

def start_server():
    """Inicia o servidor Gradio em background"""
    print("🚀 Iniciando servidor Gradio...")
    
    # Matar processos antigos
    subprocess.run("pkill -9 -f 'gradio_ui.app'", shell=True, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    # Iniciar novo servidor
    process = subprocess.Popen(
        ["python3", "-m", "gradio_ui.app"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
    )
    
    # Aguardar servidor iniciar
    print("⏳ Aguardando servidor iniciar...")
    for i in range(30):
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('0.0.0.0', 7861))
            sock.close()
            if result == 0:
                print(f"✅ Servidor rodando! (tentativa {i+1})")
                time.sleep(3)  # Aguardar mais um pouco para estabilizar
                return process
        except:
            pass
        time.sleep(1)
    
    raise Exception("❌ Servidor não iniciou em 30 segundos!")

def validate_css(page):
    """Valida que o CSS está aplicado corretamente"""
    print("\n🔍 Validando CSS aplicado...")
    
    checks = []
    
    # 1. Verificar fonte Inter no body
    try:
        font_family = page.evaluate("() => window.getComputedStyle(document.body).fontFamily")
        has_inter = "Inter" in font_family or "inter" in font_family.lower()
        checks.append(("✅" if has_inter else "❌", f"Font Inter: {font_family[:50]}"))
    except Exception as e:
        checks.append(("❌", f"Font check error: {e}"))
    
    # 2. Verificar cor de fundo
    try:
        bg_color = page.evaluate("() => window.getComputedStyle(document.body).backgroundColor")
        is_white = "255, 255, 255" in bg_color or bg_color == "rgb(255, 255, 255)"
        checks.append(("✅" if is_white else "❌", f"Background: {bg_color}"))
    except Exception as e:
        checks.append(("❌", f"BG check error: {e}"))
    
    # 3. Verificar Hero State existe
    try:
        hero = page.query_selector("#hero-welcome")
        checks.append(("✅" if hero else "❌", f"Hero State: {'Found' if hero else 'Not found'}"))
        
        if hero:
            # Verificar estilo do hero
            hero_bg = page.evaluate("() => window.getComputedStyle(document.querySelector('#hero-welcome')).background")
            checks.append(("✅" if hero_bg else "❌", f"Hero BG: {hero_bg[:50] if hero_bg else 'None'}"))
    except Exception as e:
        checks.append(("❌", f"Hero check error: {e}"))
    
    # 4. Verificar Terminal background
    try:
        terminal_bg = page.evaluate("""() => {
            const terminal = document.querySelector('.terminal-output, [data-testid="code"]');
            return terminal ? window.getComputedStyle(terminal).backgroundColor : null;
        }""")
        is_dark = terminal_bg and ("26, 26, 26" in terminal_bg or "0, 0, 0" in terminal_bg)
        checks.append(("✅" if is_dark else "⚠️", f"Terminal BG: {terminal_bg}"))
    except Exception as e:
        checks.append(("⚠️", f"Terminal check: {e}"))
    
    # 5. Verificar CSS variables
    try:
        css_var = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--color-primary')")
        has_vars = css_var and css_var.strip()
        checks.append(("✅" if has_vars else "❌", f"CSS Variables: {css_var}"))
    except Exception as e:
        checks.append(("❌", f"CSS vars error: {e}"))
    
    # 6. Verificar se há tags <style> com nosso CSS
    try:
        has_championship_css = page.evaluate("""() => {
            const styles = Array.from(document.querySelectorAll('style'));
            return styles.some(s => s.textContent.includes('CHAMPIONSHIP') || s.textContent.includes('championship-css'));
        }""")
        checks.append(("✅" if has_championship_css else "❌", f"Championship CSS injected: {has_championship_css}"))
    except Exception as e:
        checks.append(("❌", f"Style tag check: {e}"))
    
    # Imprimir resultados
    print("\n📊 RESULTADOS DA VALIDAÇÃO:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for status, message in checks:
        print(f"  {status} {message}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Contar sucessos
    success_count = sum(1 for s, _ in checks if s == "✅")
    total_count = len(checks)
    
    return success_count, total_count, checks

def take_screenshots(page):
    """Tira screenshots da página"""
    print("\n📸 Tirando screenshots...")
    
    # Screenshot full page
    screenshot_path = SCREENSHOT_DIR / "full_page.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"  ✅ Full page: {screenshot_path}")
    
    # Screenshot do Hero State
    try:
        hero = page.query_selector("#hero-welcome")
        if hero:
            hero_path = SCREENSHOT_DIR / "hero_state.png"
            hero.screenshot(path=str(hero_path))
            print(f"  ✅ Hero State: {hero_path}")
    except Exception as e:
        print(f"  ⚠️  Hero screenshot: {e}")
    
    # Screenshot do Terminal
    try:
        terminal = page.query_selector(".terminal-output, [data-testid='code']")
        if terminal:
            terminal_path = SCREENSHOT_DIR / "terminal.png"
            terminal.screenshot(path=str(terminal_path))
            print(f"  ✅ Terminal: {terminal_path}")
    except Exception as e:
        print(f"  ⚠️  Terminal screenshot: {e}")
    
    return screenshot_path

def main():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🎨 TESTE VISUAL - Validação de CSS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    server_process = None
    
    try:
        # Iniciar servidor
        server_process = start_server()
        
        # Iniciar Playwright
        print("\n🌐 Iniciando browser...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1
            )
            page = context.new_page()
            
            # Navegar para a página
            print(f"\n🔗 Acessando {URL}...")
            page.goto(URL, wait_until="load", timeout=60000)
            
            # Aguardar página carregar completamente
            print("⏳ Aguardando página carregar...")
            page.wait_for_timeout(5000)
            
            # Aguardar Gradio inicializar
            page.wait_for_selector("gradio-app", timeout=10000)
            
            # Tirar screenshots
            screenshot_path = take_screenshots(page)
            
            # Validar CSS
            success_count, total_count, checks = validate_css(page)
            
            # Resultado final
            print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"📊 RESULTADO FINAL: {success_count}/{total_count} checks passaram")
            print(f"📸 Screenshots salvos em: {SCREENSHOT_DIR.absolute()}")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # Fechar browser
            browser.close()
            
            # Retornar código de saída baseado no resultado
            if success_count >= total_count - 1:  # Permitir 1 falha
                print("\n✅ TESTE PASSOU! CSS está carregado!")
                return 0
            else:
                print(f"\n❌ TESTE FALHOU! Apenas {success_count}/{total_count} checks passaram")
                print(f"\n💡 Verifique os screenshots em: {SCREENSHOT_DIR.absolute()}")
                return 1
    
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Matar servidor
        if server_process:
            print("\n🛑 Encerrando servidor...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except:
                server_process.kill()

if __name__ == "__main__":
    sys.exit(main())

