#!/usr/bin/env python
"""
Script para capturar screenshot específico do dashboard Streamlit.
Captura apenas os gráficos: 'Comparativo de preço médio por ativo' e 'Evolução do dólar'.
"""

import sys
import time
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Erro: Selenium ou webdriver-manager nao instalado")
    print("Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "selenium", "webdriver-manager"])
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT / "reports" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def setup_driver():
    """Configura o driver do Chrome em modo headless"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def capture_charts():
    """Captura screenshot dos gráficos específicos"""
    driver = None
    try:
        print("Iniciando capture de gráficos do dashboard...")
        driver = setup_driver()
        
        # Acessar o dashboard
        print("Acessando http://localhost:8501...")
        driver.get("http://localhost:8501")
        
        # Aguardar carregamento inicial
        time.sleep(5)
        
        # Remover sidebar para melhor visualização
        try:
            sidebar = driver.find_element(By.CSS_SELECTOR, "[data-testid='stSidebarNav']")
            driver.execute_script("arguments[0].style.display = 'none';", sidebar)
        except:
            pass
        
        # Aguardar os gráficos carregarem
        print("Aguardando gráficos carregarem...")
        wait = WebDriverWait(driver, 15)
        
        # Localizar os títulos dos gráficos
        try:
            # Scroll até encontrar "Comparativo de preço médio por ativo (BRL)"
            driver.execute_script("window.scrollTo(0, 2500);")
            time.sleep(3)
            
            # Encontrar o elemento pai que contém ambos os gráficos
            # Geralmente Streamlit usa a estrutura de colunas com divs
            
            # Capturar todo o viewport após scroll
            screenshot_path = SCREENSHOTS_DIR / "dashboard_charts.png"
            driver.save_screenshot(str(screenshot_path))
            print(f"Screenshot capturado: {screenshot_path}")
            
            return True
            
        except Exception as e:
            print(f"Erro ao localizar gráficos: {e}")
            # Capturar mesmo assim
            screenshot_path = SCREENSHOTS_DIR / "dashboard_charts.png"
            driver.save_screenshot(str(screenshot_path))
            print(f"Screenshot capturado (fallback): {screenshot_path}")
            return False
        
    except Exception as e:
        print(f"Erro durante capture: {e}")
        return False
    
    finally:
        if driver:
            driver.quit()
            print("Driver fechado")

if __name__ == "__main__":
    try:
        success = capture_charts()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Erro fatal: {e}")
        sys.exit(1)
