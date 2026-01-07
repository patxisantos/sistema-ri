# Sistema de Recuperación de Información

**Práctica Final - Recuperación de Información**  
Grado en Ingeniería Informática - Universidad de Granada  
Curso 2025-2026

## Descripción

Sistema de Recuperación de Información (SRI) completo que permite buscar documentos del corpus Project Gutenberg utilizando un índice invertido con ranking BM25.

### Características

- **Backend**: API REST con FastAPI
- **Frontend**: Interfaz web con React
- **Indexación**: Índice invertido con pesos BM25
- **Corpus**: ~28,000 documentos de Project Gutenberg (~10GB)
- **Preprocesamiento**: Tokenización, eliminación de stopwords, stemming (NLTK)
- **Evaluación**: Métricas P@k, R@k, MAP, MRR

## Requisitos

### Hardware recomendado

> **IMPORTANTE**: La construcción del índice requiere un alto consumo de CPU y memoria RAM.

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 4 núcleos | 8 núcleos / 16 hilos |
| RAM | 32 GB | 64 GB |
| Disco | 20 GB libres | SSD con 50 GB libres |

Los parámetros de indexación son configurables en `indexing.py`:
- `batch_size`: Documentos por lote (default: 500)
- `num_workers`: Número de procesos paralelos (default: 70% de CPUs)
- `use_cpu_percent`: Porcentaje de CPU a utilizar

Si tu sistema tiene menos recursos, reduce estos valores para evitar saturación, aunque el proceso será más lento.

### Software necesario

- Python 3.9+
- Node.js 16+
- npm o yarn

### Dependencias Python (especificadas también en requirements.txt)

```
fastapi
uvicorn
nltk
tqdm
psutil
pydantic
```

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/patxisantos/sistema-ri.git
cd sistema-ri
```

### 2. Configurar Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install fastapi uvicorn nltk tqdm psutil pydantic

# Descargar recursos NLTK
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

### 3. Descargar y Configurar Datos

> ⚠️ **IMPORTANTE**: Este paso es crucial para el funcionamiento del sistema.

#### 3.1. Acceder a Google Drive

El corpus y el índice pre-construido están disponibles en Google Drive:

🔗 **[Descargar datos desde Google Drive](https://drive.google.com/drive/folders/1EDmw6QCi_2zTBF6jwhnnzEr6M3V3mkS1?usp=sharing)**

**Estructura en Google Drive:**
```
📁 Sistema RI - Datos/
├── 📦 corpus.zip          (~10.4 GB comprimido - ~28,000 documentos JSON)
└── 📁 index/
    ├── index.pkl           (~2.4 GB)
    ├── index_metadata.json (~100 MB)
    └── idf.json            (~50 MB)
```

#### 3.2. Crear estructura de carpetas

Dentro del directorio `backend`, crea la carpeta `data` con las subcarpetas necesarias:

```bash
cd backend
mkdir data
mkdir data\corpus
mkdir data\index
```

#### 3.3. Descargar y extraer corpus

1. Descarga **corpus.zip** desde Google Drive (~10.4 GB)
2. **Descomprime el archivo ZIP**
3. **Copia TODOS los archivos JSON descomprimidos** a `backend/data/corpus/`

> ⚠️ Los archivos JSON deben estar **directamente** en `data/corpus/`, no dentro de subcarpetas.

#### 3.4. Descargar índice pre-construido

1. Descarga la carpeta **index/** desde Google Drive
2. Copia los **tres archivos** a `backend/data/index/`:
   - `index.pkl`
   - `index_metadata.json`
   - `idf.json`

#### 3.5. Verificar estructura final

La estructura debe quedar así:

```
backend/
├── main.py
├── search_engine.py
├── ...
└── data/                    ← CREAR
    ├── corpus/              ← CREAR
    │   ├── download_metadata.json
    │   ├── gutenberg_1_1767745768573496.json
    │   ├── gutenberg_100_1767745769619108.json
    │   └── ... (~28,000 archivos JSON más)
    └── index/               ← CREAR
        ├── index.pkl
        ├── index_metadata.json
        └── idf.json
```

Verificar con:
```bash
# Desde backend/
dir data\corpus    # Debe mostrar ~28,000 archivos .json
dir data\index     # Debe mostrar 3 archivos
```

> 📖 **Instrucciones detalladas**: Ver [backend/README.md](backend/README.md) para más información.
>
> 🔨 **Construir índice desde cero**: Si prefieres no descargar el índice, solo descarga el corpus y ejecuta `POST /api/index/build` (⚠️ ~40 minutos, requiere recursos significativos).

### 4. Configurar Frontend

```bash
cd ../buscador-frontend

# Instalar dependencias
npm install
```

## Uso

### Iniciar el Backend

```bash
cd backend
venv\Scripts\activate  # Windows
uvicorn main:app --reload --port 8000
```

El servidor estará disponible en `http://localhost:8000`

### Iniciar el Frontend

```bash
cd buscador-frontend
npm start
```

La aplicación estará disponible en `http://localhost:3000`

## API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Verificar estado del servidor |
| GET | `/health` | Estado detallado del sistema |
| GET | `/search?query=...&top_k=10` | Realizar búsqueda |
| GET | `/api/index/stats` | Estadísticas del índice |
| GET | `/api/evaluate` | Métricas de evaluación |
| POST | `/api/index/build` | Construir índice (40+ min) |

### Ejemplo de búsqueda

```bash
curl "http://localhost:8000/search?query=constitution&top_k=10"
```

Respuesta:
```json
{
  "status": "success",
  "query": "constitution",
  "results": [
    {
      "doc_id": "gutenberg_28067_...",
      "title": "The Spirit of American Government",
      "score": 42.42,
      "snippet": "...A Study Of The Constitution..."
    }
  ],
  "count": 10,
  "elapsed_ms": 23.5
}
```

## Estructura del Proyecto (una vez instalado correctamente)

```
sistema-ri/
├── backend/
│   ├── main.py              # API FastAPI
│   ├── search_engine.py     # Motor de búsqueda BM25
│   ├── indexing.py          # Motor de indexación
│   ├── corpus_handler.py    # Gestión del corpus
│   ├── evaluation.py        # Métricas de evaluación
│   └── data/
│       ├── corpus/          # Documentos
│       └── index/           # Índice invertido
├── buscador-frontend/
│   ├── src/
│   │   ├── App.js           # Componente principal
│   │   └── App.css          # Estilos
│   └── package.json
└── README.md
```

## Tecnologías Utilizadas

- **Backend**: Python, FastAPI, NLTK, Pickle
- **Frontend**: React, CSS
- **Algoritmo**: BM25 (k1=1.5, b=0.75)
- **Corpus**: Project Gutenberg

## Autor

Francisco Javier Santos Rivas  
Grado en Ingeniería Informática  
Universidad de Granada

## Licencia

Proyecto académico - Práctica Final de Recuperación de Información
