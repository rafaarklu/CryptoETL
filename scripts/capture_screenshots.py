#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para capturar screenshot do Dashboard completo.
Uso:
  - python capture_screenshots.py
"""

import sys
import time
import io
from pathlib import Path

# Configurar stdout para UTF-8 no Windows
if sys.stdout.encoding not in ['utf-8', 'UTF-8']:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Adicionar src ao path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def capture_dashboard_full():
    """Captura screenshot do Dashboard completo"""
    print("\n" + "="*50)
    print("CAPTURANDO SCREENSHOT DO DASHBOARD")
    print("="*50)
    
    output_dir = ROOT / "reports" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            
            try:
                print("[*] Acessando Dashboard em http://localhost:8501...")
                page.goto("http://localhost:8501", timeout=15000, wait_until="networkidle")
                time.sleep(5)
                
                print("[*] Capturando Dashboard completo...")
                page.screenshot(path=str(output_dir / "dashboard_full.png"), full_page=True)
                print("    [OK] dashboard_full.png")
                
                browser.close()
                print("\n[SUCCESS] SCREENSHOT DO DASHBOARD CAPTURADO COM SUCESSO!")
                print(f"         Salvo em: {output_dir / 'dashboard_full.png'}")
                return True
                
            except PlaywrightTimeout as e:
                print(f"[ERROR] Timeout ao capturar: {e}")
                browser.close()
                return False
            except Exception as e:
                print(f"[ERROR] Erro ao capturar: {e}")
                browser.close()
                return False
    
    except ImportError:
        print("[!] Playwright nao instalado. Instalando...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "playwright"])
        # Tentar novamente
        return capture_dashboard_full()
    except Exception as e:
        print(f"[ERROR] Erro geral: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Erro geral: {e}")
        return False


def capture_airflow_screenshots_fallback():
    """Fallback para capturar Airflow via PowerShell"""
    import subprocess
    output_dir = ROOT / "reports" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        print("→ Capturando via PowerShell (Print Screen)...")
        script = f"""
Add-Type -AssemblyName System.Windows.Forms
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save("{output_dir / 'airflow_screenshot.png'}")
$graphics.Dispose()
$bitmap.Dispose()
Write-Host "Screenshot salvo"
"""
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"[OK] airflow_screenshot.png (fallback)")
            return True
        else:
            print(f"[ERROR] Erro no fallback: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Erro ao usar fallback: {e}")
        return False


def capture_dashboard_screenshots_fallback():
    """Fallback para capturar Dashboard via PowerShell"""
    import subprocess
    output_dir = ROOT / "reports" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        print("[*] Capturando via PowerShell (Print Screen)...")
        script = f"""
Add-Type -AssemblyName System.Windows.Forms
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save("{output_dir / 'dashboard_screenshot.png'}")
$graphics.Dispose()
$bitmap.Dispose()
Write-Host "Screenshot salvo"
"""
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"[OK] dashboard_screenshot.png (fallback)")
            return True
        else:
            print(f"[ERROR] Erro no fallback: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Erro ao usar fallback: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("[!] Playwright nao instalado. Instalando...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "playwright"])
        # Tentar novamente
        return capture_dashboard_full()
    except Exception as e:
        print(f"[ERROR] Erro geral: {e}")
        return False


if __name__ == "__main__":
    try:
        success = capture_dashboard_full()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        sys.exit(1)
