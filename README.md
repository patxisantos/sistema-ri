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

### 3. Descargar Datos

El corpus y el índice pre-construido están disponibles en Google Drive:

🔗 **[Descargar datos desde Google Drive](https://drive.google.com/drive/folders/1EDmw6QCi_2zTBF6jwhnnzEr6M3V3mkS1?usp=sharing)**

Descarga y extrae los archivos en la carpeta:

```
    ├── corpus/          # Documentos del corpus (~10GB)
    │   └── *.json (archivos de documentos, previamente TXT)
    └── index/           # Índice pre-construido
        └── index.pkl
```

> **Nota**: Si prefieres construir el índice desde cero, omite la carpeta `index/` y ejecuta `POST /api/index/build` (proceso de ~40 minutos).

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

## Estructura del Proyecto

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

## Métricas de Evaluación

El sistema incluye evaluación automática con las siguientes métricas:

| Métrica | Valor | Descripción |
|---------|-------|-------------|
| MAP | 12.31% | Mean Average Precision |
| MRR | 21.00% | Mean Reciprocal Rank |
| P@5 | 8.0% | Precision at 5 |
| P@10 | 8.0% | Precision at 10 |
| R@10 | 16.0% | Recall at 10 |
| R@20 | 24.0% | Recall at 20 |

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
