#!/usr/bin/env python
"""
Script simples para capturar screenshots dos navegadores abertos
usando pyautogui ou selenium
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def capture_with_pyautogui():
    """Captura screenshots com pyautogui"""
    try:
        import pyautogui
        import time
        
        output_dir = ROOT / "reports" / "screenshots"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Ativar e capturar Airflow
        print("Capturando Airflow...")
        import pygetwindow as gw
        
        airflow_windows = gw.getWindowsWithTitle('Airflow')
        if airflow_windows:
            airflow_windows[0].activate()
            time.sleep(1)
            screenshot = pyautogui.screenshot()
            screenshot.save(str(output_dir / "airflow_home.png"))
            print("✓ airflow_home.png")
        
        # Ativar e capturar Dashboard
        print("Capturando Dashboard...")
        dashboard_windows = gw.getWindowsWithTitle('Streamlit')
        if dashboard_windows:
            dashboard_windows[0].activate()
            time.sleep(1)
            screenshot = pyautogui.screenshot()
            screenshot.save(str(output_dir / "dashboard_overview.png"))
            print("✓ dashboard_overview.png")
        
        return True
    except Exception as e:
        print(f"Erro com pyautogui: {e}")
        return False


def capture_with_urllib_screenshot():
    """Captura usando urllib e screenshot genérico"""
    import subprocess
    from pathlib import Path
    
    output_dir = ROOT / "reports" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Usar Windows' SnippingTool ou Print Screen + Paint
        # Alternativa: PowerShell para capturar janelas
        
        script_ps = """
        Add-Type -AssemblyName System.Windows.Forms
        
        # Capturar tela inteira
        $bitmap = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Location, [System.Drawing.Point]::Empty, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Size)
        $bitmap.Save("{}")
        """
        
        output_path = str(output_dir / "full_screen.png")
        ps_cmd = script_ps.format(output_path)
        
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✓ Screenshot capturado: {output_path}")
            return True
        else:
            print(f"Erro PowerShell: {result.stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"Erro: {e}")
        return False


def capture_html_to_image():
    """Captura como HTML para visualização offline"""
    import urllib.request
    
    output_dir = ROOT / "reports" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    urls = {
        "http://localhost:8080/home": "airflow_home.html",
        "http://localhost:8501": "dashboard.html"
    }
    
    for url, filename in urls.items():
        try:
            print(f"Capturando {url}...")
            with urllib.request.urlopen(url, timeout=5) as response:
                html = response.read()
                output_file = output_dir / filename
                with open(output_file, 'wb') as f:
                    f.write(html)
                print(f"✓ {filename} (HTML)")
        except Exception as e:
            print(f"✗ Erro ao capturar {url}: {e}")


def main():
    print("\n" + "="*50)
    print("Capturando Screenshots")
    print("="*50 + "\n")
    
    # Tentar com pyautogui primeiro
    if capture_with_pyautogui():
        print("\n✓ Screenshots capturados com sucesso!")
        return
    
    # Tentar com PowerShell
    print("\nTentando PowerShell...")
    if capture_with_urllib_screenshot():
        return
    
    # Fallback: capturar como HTML
    print("\nFallback: Capturando como HTML...")
    capture_html_to_image()
    
    print("\n✓ Captura concluída!\n")


if __name__ == "__main__":
    main()
