#!/usr/bin/env python3
"""
LNBits Dashboard Setup Helper - Read Only Version
Script interactivo para configurar el dashboard en modo read-only.

Uso:
    python setup.py
"""

import os
import sys
import subprocess
from pathlib import Path

class Colors:
    """ANSI color codes"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Imprime un encabezado"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text:^60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

def print_step(number, text):
    """Imprime un paso"""
    print(f"{Colors.BOLD}{Colors.BLUE}Paso {number}:{Colors.ENDC} {text}")

def print_success(text):
    """Imprime un mensaje de éxito"""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    """Imprime un mensaje de error"""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_warning(text):
    """Imprime una advertencia"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

def print_info(text):
    """Imprime información"""
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")

def check_python_version():
    """Verifica que tenemos Python 3.8+"""
    print_step(1, "Verificando versión de Python...")
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Se requiere Python 3.8+ (tienes {version.major}.{version.minor})")
        return False

def check_dependencies():
    """Verifica e instala dependencias"""
    print_step(2, "Verificando dependencias...")
    
    required_packages = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'requests': 'requests',
    }
    
    missing = []
    installed = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
            installed.append(package)
        except ImportError:
            missing.append(package)
    
    if installed:
        print_success(f"Paquetes instalados: {', '.join(installed)}")
    
    if missing:
        print_warning(f"Paquetes faltantes: {', '.join(missing)}")
        print_info("Instalando paquetes...")
        
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"] + missing,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print_success("Paquetes instalados correctamente")
            return True
        except subprocess.CalledProcessError:
            print_error("No se pudieron instalar los paquetes")
            print_info(f"Intenta manualmente: pip install {' '.join(missing)}")
            return False
    else:
        print_success("Todas las dependencias están instaladas")
        return True

def setup_env_file():
    """Crea el archivo .env con la configuración"""
    print_step(3, "Configurando archivo .env...")
    
    env_file = Path('.env')
    example_file = Path('.env.example')
    
    # Copiar .env.example si existe
    if example_file.exists() and not env_file.exists():
        with open(example_file, 'r') as f:
            example_content = f.read()
        with open(env_file, 'w') as f:
            f.write(example_content)
        print_success("Archivo .env creado desde .env.example")
    elif env_file.exists():
        print_info("Archivo .env ya existe")
        return True
    else:
        # Crear .env desde cero
        with open(env_file, 'w') as f:
            f.write("# LNBits Dashboard Configuration - Read Only\n")
            f.write("LNBITS_ENDPOINT=http://localhost:5000\n")
            f.write("WALLET_CANDIDATO1=your_invoice_key_here\n")
            f.write("WALLET_CANDIDATO2=your_invoice_key_here\n")
            f.write("WALLET_MESA0=your_invoice_key_here\n")
        print_success("Archivo .env creado")
    
    return True

def configure_wallets():
    """Configura interactivamente las wallets"""
    print_step(4, "Configurando wallets (Invoice Keys)...")
    
    print_info("Necesitarás obtener las Invoice Keys de tus wallets en LNBits")
    print_warning("⚠️  USA INVOICE KEYS (read-only), NO Admin Keys")
    print_info("Para cada wallet: LNBits → Wallet → API Keys → Invoice Key")
    print()
    
    env_file = Path('.env')
    config = {}
    
    # Leer configuración actual
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key] = value
    
    # Configurar LNBits endpoint
    default_endpoint = config.get('LNBITS_ENDPOINT', 'http://localhost:5000')
    print(f"LNBits Endpoint (default: {default_endpoint}):")
    endpoint = input("  > ").strip() or default_endpoint
    config['LNBITS_ENDPOINT'] = endpoint
    
    # Configurar wallets
    wallets = [
        ('WALLET_CANDIDATO1', 'Candidato 1'),
        ('WALLET_CANDIDATO2', 'Candidato 2'),
        ('WALLET_MESA0', 'Mesa 0'),
    ]
    
    for env_key, display_name in wallets:
        print(f"\n{display_name} - Invoice Key (read-only):")
        current = config.get(env_key, '')
        if current and current != 'your_invoice_key_here':
            print(f"  (actual: {current[:20]}...)")
        key = input("  > ").strip()
        if key:
            config[env_key] = key
    
    # Guardar configuración
    with open(env_file, 'w') as f:
        f.write("# LNBits Dashboard Configuration - Read Only Mode\n")
        f.write("# Generado por setup.py\n\n")
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    
    print_success("Configuración guardada en .env")
    return True

def test_connection():
    """Prueba la conexión a LNBits"""
    print_step(5, "Probando conexión a LNBits...")
    
    try:
        import requests
        from pathlib import Path
        
        config = {}
        env_file = Path('.env')
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key] = value
        
        endpoint = config.get('LNBITS_ENDPOINT', 'http://localhost:5000').rstrip('/')
        
        print_info(f"Probando conexión a: {endpoint}")
        
        try:
            response = requests.get(f"{endpoint}/health", timeout=5)
            if response.status_code < 500:
                print_success("✓ LNBits está respondiendo")
                return True
        except:
            pass
        
        # Intentar con /api/v1/wallet si no está disponible /health
        wallet_key = config.get('WALLET_CANDIDATO1', '').strip()
        if wallet_key and wallet_key != 'your_invoice_key_here':
            print_info("Probando con Invoice Key de candidato1...")
            headers = {'X-Api-Key': wallet_key}
            response = requests.get(
                f"{endpoint}/api/v1/wallet",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                balance = response.json().get('balance', 0)
                print_success(f"✓ Wallet conectada (saldo: {balance} sats)")
                return True
            elif response.status_code == 401:
                print_error("Invoice Key inválida o expirada")
                return False
        
        print_warning("No se pudo verificar la conexión completamente")
        print_info("Puedes probar manualmente ejecutando el dashboard")
        return True
        
    except Exception as e:
        print_error(f"Error en la prueba: {e}")
        return False

def show_next_steps():
    """Muestra los próximos pasos"""
    print_step(6, "Próximos pasos...")
    
    print(f"""
{Colors.BOLD}Para iniciar el dashboard:{Colors.ENDC}
  python lnbits_dashboard.py

{Colors.BOLD}Luego accede a:{Colors.ENDC}
  http://localhost:5000

{Colors.BOLD}Archivos importantes:{Colors.ENDC}
  - lnbits_dashboard.py    (aplicación principal)
  - .env                    (configuración, NO compartir)
  - README.md               (documentación)
  - TECHNICAL.md            (guía técnica)

{Colors.BOLD}Modo de seguridad:{Colors.ENDC}
  🔒 Read-Only (Solo lectura)
  ✅ Usa Invoice Keys (read-only)
  ❌ No crea invoices
  ❌ No paga invoices

{Colors.BOLD}Protege tus secrets:{Colors.ENDC}
  echo ".env" >> .gitignore

{Colors.BOLD}¿Necesitas ayuda?{Colors.ENDC}
  Consulta README.md para documentación completa
  Consulta TECHNICAL.md para detalles técnicos
""")

def main():
    """Función principal"""
    print_header("LNBits Dashboard Setup - Read Only")
    
    steps = [
        ("Verificar Python", check_python_version),
        ("Instalar dependencias", check_dependencies),
        ("Crear archivo .env", setup_env_file),
        ("Configurar wallets", configure_wallets),
        ("Probar conexión", test_connection),
    ]
    
    for i, (description, func) in enumerate(steps, 1):
        try:
            if not func():
                print_error(f"Error en: {description}")
                if i < 3:  # Los primeros 3 pasos son críticos
                    return False
        except Exception as e:
            print_error(f"Excepción en {description}: {e}")
            if i < 3:
                return False
    
    show_next_steps()
    print_success("Setup completado!")
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Setup cancelado por el usuario{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Error inesperado: {e}{Colors.ENDC}")
        sys.exit(1)
