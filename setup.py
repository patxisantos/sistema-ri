import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

# Forzar UTF-8 en Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

# ==================== FUNCIONES ====================

def print_header(text):
    """Encabezado sin caracteres especiales."""
    print("\n" + "="*70)
    print(text)
    print("="*70 + "\n")

def print_ok(text):
    """Mensaje OK."""
    print(f"[OK] {text}")

def print_error(text):
    """Mensaje ERROR."""
    print(f"[ERROR] {text}")

def print_warning(text):
    """Mensaje WARNING."""
    print(f"[WARNING] {text}")

def print_step(step_num, text, end="\n"):
    """Paso numerado."""
    print(f"[{step_num}] {text}", end=end)
    sys.stdout.flush()

# ==================== RUTAS ====================

BASE_DIR = Path(__file__).parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "buscador-frontend"
DATA_DIR = BACKEND_DIR / "data"
CORPUS_DIR = DATA_DIR / "corpus"
INDEX_DIR = DATA_DIR / "index"
VENV_DIR = BACKEND_DIR / "venv"

# Ejecutables según SO
if sys.platform == "win32":
    PIP_EXE = VENV_DIR / "Scripts" / "pip.exe"
    PYTHON_EXE = VENV_DIR / "Scripts" / "python.exe"
else:
    PIP_EXE = VENV_DIR / "bin" / "pip"
    PYTHON_EXE = VENV_DIR / "bin" / "python"

# ==================== INICIO ====================

print_header("CONFIGURACIÓN DEL SISTEMA DE RECUPERACIÓN DE INFORMACIÓN")
print(f"Python: {sys.version.split()[0]}")
print(f"Sistema: {sys.platform}")
print(f"Directorio: {BASE_DIR}\n")

# ==================== PASO 1: CREAR DIRECTORIOS ====================

print_header("PASO 1: Creando estructura de directorios")

try:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    print_ok("Directorio corpus")
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    print_ok("Directorio index")
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    print_ok("Directorio frontend")
except Exception as e:
    print_error(f"No se pudieron crear directorios: {e}")
    sys.exit(1)

# ==================== PASO 2: LIMPIAR VENV ANTERIOR ====================

print_header("PASO 2: Limpiando entorno virtual anterior")

if VENV_DIR.exists():
    print("Intentando eliminar venv anterior...")
    # Intentar hasta 3 veces (a veces falla por permisos temporales)
    for attempt in range(3):
        try:
            shutil.rmtree(VENV_DIR)
            print_ok(f"Venv eliminado (intento {attempt + 1})")
            break
        except Exception as e:
            if attempt < 2:
                print_warning(f"Intento {attempt + 1} fallido, esperando...")
                time.sleep(2)  # Esperar 2 segundos antes de reintentar
            else:
                print_warning("No se pudo eliminar venv anterior (continuando de todas formas)")
                print("Nota: Si hay problemas, ejecuta: rmdir /s /q backend\\venv")

# ==================== PASO 3: CREAR VENV ====================

print_header("PASO 3: Creando entorno virtual")

try:
    result = subprocess.run(
        [sys.executable, "-m", "venv", str(VENV_DIR)],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode != 0:
        print_error(f"Error creando venv: {result.stderr}")
        sys.exit(1)
    
    print_ok("Entorno virtual creado correctamente")
except subprocess.TimeoutExpired:
    print_error("Timeout creando venv")
    sys.exit(1)
except Exception as e:
    print_error(f"Error: {e}")
    sys.exit(1)

# ==================== PASO 4: INSTALAR DEPENDENCIAS ====================

print_header("PASO 4: Instalando dependencias Python")

# Dependencias con versiones especificadas (INCLUYE psutil)
dependencies = [
    "fastapi==0.104.1",
    "uvicorn==0.24.0",
    "nltk==3.8.1",
    "requests==2.31.0",
    "beautifulsoup4==4.12.2",
    "python-multipart==0.0.6",
    "tqdm==4.66.1",
    "psutil>=5.0.0",
]

installed = []
failed = []

for i, dep in enumerate(dependencies, 1):
    # Obtener nombre del paquete correctamente
    pkg_name = dep.split("==")[0].split(">=")[0]
    print_step(i, f"Instalando {pkg_name}...", end=" ")
    
    try:
        result = subprocess.run(
            [str(PIP_EXE), "install", "--quiet", dep],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print_ok("OK")
            installed.append(pkg_name)
        else:
            print_error("FALLO")
            failed.append(pkg_name)
    except subprocess.TimeoutExpired:
        print_warning("TIMEOUT (continuando)")
    except Exception as e:
        print_error(f"ERROR: {str(e)[:50]}")
        failed.append(pkg_name)

print(f"\nInstaladas: {len(installed)}/{len(dependencies)} dependencias")

# Si hay fallos, intentar recuperación
if failed:
    print_warning(f"\nPaquetes con problemas: {', '.join(failed)}")
    print("Intentando instalación sin especificar versión...")
    
    recovered = []
    for pkg_name in failed:
        try:
            result = subprocess.run(
                [str(PIP_EXE), "install", "--quiet", pkg_name],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print_ok(f"Recuperado: {pkg_name}")
                recovered.append(pkg_name)
        except Exception:
            pass
    
    failed = [p for p in failed if p not in recovered]
    
    if failed:
        print_warning(f"Aún fallan: {', '.join(failed)}")

# ==================== PASO 5: DESCARGAR NLTK ====================

print_header("PASO 5: Descargando recursos NLTK")

nltk_script = """import nltk
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

resources = ['punkt', 'stopwords']

for resource in resources:
    try:
        nltk.download(resource, quiet=True)
        print(f"[OK] {resource} descargado")
    except Exception as e:
        print(f"[WARNING] {resource}: {str(e)[:50]}")
"""

try:
    result = subprocess.run(
        [str(PYTHON_EXE), "-c", nltk_script],
        capture_output=True,
        text=True,
        timeout=120,
        encoding='utf-8',
        errors='replace'
    )
    
    print(result.stdout)
    
    if result.returncode != 0 and result.stderr:
        print_warning(f"Notas: {result.stderr[:100]}")
except subprocess.TimeoutExpired:
    print_warning("Timeout descargando NLTK (continuando)")
except Exception as e:
    print_warning(f"Error NLTK: {e}")

# ==================== PASO 6: VERIFICAR INSTALACIÓN ====================

print_header("PASO 6: Verificando instalacion")

# Mapeo correcto de nombres de paquetes
verify_script = """import sys

packages = {
    'fastapi': 'fastapi',
    'uvicorn': 'uvicorn',
    'nltk': 'nltk',
    'requests': 'requests',
    'beautifulsoup4': 'bs4',
    'python-multipart': 'multipart',
    'tqdm': 'tqdm',
    'psutil': 'psutil'
}

all_ok = True

for display_name, import_name in packages.items():
    try:
        __import__(import_name)
        print(f"[OK] {display_name}")
    except ImportError:
        print(f"[ERROR] {display_name} (import: {import_name})")
        all_ok = False

if all_ok:
    print("\\n[OK] TODAS LAS DEPENDENCIAS VERIFICADAS")
    sys.exit(0)
else:
    print("\\n[ERROR] Faltan dependencias")
    sys.exit(1)
"""

try:
    result = subprocess.run(
        [str(PYTHON_EXE), "-c", verify_script],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    print(result.stdout)
    
    if result.returncode != 0:
        print_error("Verificación fallida")
        print_warning("Intentar ejecutar manualmente: python -m pip install -r requirements.txt")
    else:
        print_ok("Verificación completada exitosamente")
except Exception as e:
    print_warning(f"Error en verificación: {e}")

# ==================== FINALIZACIÓN ====================

print_header("INSTALACIÓN COMPLETADA")

print("Para ejecutar el sistema:\n")

print("TERMINAL 1 - Backend:")
print(f" cd {BACKEND_DIR.name}")

if sys.platform == "win32":
    print(" venv\\Scripts\\activate.bat")
else:
    print(" source venv/bin/activate")

print(" uvicorn main:app --reload\n")

print("TERMINAL 2 - Frontend:")
print(f" cd {FRONTEND_DIR.name}")
print(" npm install  # primera vez")
print(" npm start\n")

print("TERMINAL 3 - Navegador:")
print(" http://localhost:3000\n")

print_ok("Sistema listo para ejecutarse")

print("\nSi hay problemas, prueba:")
print(" - Cerrar todas las terminales")
print(" - Ejecutar: rmdir /s /q backend\\venv")
print(" - Ejecutar nuevamente: python setup.py")

sys.exit(0)