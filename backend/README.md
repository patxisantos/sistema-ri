# Configuración del Backend - Sistema RI

Este directorio contiene el backend del Sistema de Recuperación de Información.

## 📥 Descarga de Datos desde Google Drive

Para que el sistema funcione correctamente, necesitas descargar el corpus y el índice pre-construido desde Google Drive.

### Estructura en Google Drive

Cuando accedas al enlace de Google Drive, encontrarás la siguiente estructura:

```
📁 Sistema RI - Datos/
├── 📦 corpus.zip          (~10.4 GB comprimido a 3.78)
└── 📁 index/
    ├── index.pkl
    ├── index_metadata.json
    └── idf.json
```

### Archivos a descargar

1. **corpus.zip**: Contiene ~28,000 documentos de Project Gutenberg en formato JSON
2. **Carpeta index/**: Contiene el índice invertido pre-construido con tres archivos

## 📂 Estructura Final Requerida

Después de descargar y descomprimir los archivos, la estructura de carpetas debe quedar de la siguiente manera:

```
backend/
├── main.py
├── search_engine.py
├── indexing.py
├── corpus_handler.py
├── evaluation.py
├── requirements.txt
├── README.md                    # Este archivo
└── data/                        # ⚠️ CREAR ESTA CARPETA
    ├── corpus/                  # ⚠️ CREAR ESTA CARPETA
    │   ├── download_metadata.json
    │   ├── gutenberg_1_1767745768573496.json
    │   ├── gutenberg_100_1767745769619108.json
    │   ├── gutenberg_10000_1767746781683028.json
    │   └── ... (~28,000 archivos JSON más)
    └── index/                   # ⚠️ CREAR ESTA CARPETA
        ├── index.pkl
        ├── index_metadata.json
        └── idf.json
```

## 🔧 Pasos de Instalación

### 1. Crear la estructura de carpetas

Dentro del directorio `backend`, crea la carpeta `data` con las subcarpetas necesarias:

```bash
# Desde el directorio backend/
mkdir data
mkdir data\corpus
mkdir data\index
```

### 2. Descargar archivos desde Google Drive

🔗 **[Enlace a Google Drive](https://drive.google.com/drive/folders/1EDmw6QCi_2zTBF6jwhnnzEr6M3V3mkS1?usp=sharing)**

### 3. Extraer corpus.zip

1. Descarga `corpus.zip` desde Google Drive
2. **Descomprime el archivo ZIP**
3. **Copia TODOS los archivos JSON descomprimidos** a la carpeta `backend/data/corpus/`

> ⚠️ **IMPORTANTE**: NO copies la carpeta ZIP ni ninguna carpeta contenedora, solo los archivos JSON individuales deben estar directamente en `data/corpus/`

### 4. Copiar archivos del índice

1. Descarga la carpeta `index/` completa desde Google Drive
2. Copia los **tres archivos** (`index.pkl`, `index_metadata.json`, `idf.json`) a la carpeta `backend/data/index/`

### 5. Verificar la instalación

Una vez completados los pasos anteriores, verifica que la estructura sea correcta:

```bash
# Desde el directorio backend/
dir data\corpus    # Debe mostrar ~28,000 archivos .json
dir data\index     # Debe mostrar 3 archivos (index.pkl, index_metadata.json, idf.json)
```

## ✅ Verificación Final

Antes de iniciar el servidor, asegúrate de que:

- [ ] La carpeta `backend/data/corpus/` contiene aproximadamente 28,000 archivos JSON
- [ ] La carpeta `backend/data/index/` contiene exactamente 3 archivos
- [ ] No hay subcarpetas adicionales dentro de `corpus/` o `index/`
- [ ] Los archivos JSON están directamente en `corpus/`, no dentro de otra carpeta

Una vez completada la configuración, puedes iniciar el servidor:

```bash
# Activar entorno virtual
venv\Scripts\activate

# Iniciar servidor
uvicorn main:app --reload --port 8000
```

## ⚙️ Opción Alternativa: Construir el Índice

Si prefieres NO descargar el índice pre-construido, puedes construirlo desde cero:

1. Descarga SOLO el archivo `corpus.zip`
2. Extrae los archivos a `data/corpus/`
3. Inicia el servidor
4. Ejecuta el endpoint: `POST http://localhost:8000/api/index/build`

> ⚠️ **Advertencia**: La construcción del índice puede tardar ~40 minutos y requiere recursos significativos (ver requisitos de hardware en el README principal).

## 🆘 Problemas Comunes

| Problema | Solución |
|----------|----------|
| Error: "Corpus directory not found" | Verifica que `data/corpus/` existe y contiene archivos JSON |
| Error: "Index not found" | Asegúrate de que `data/index/` contiene los 3 archivos requeridos |
| El corpus está vacío | Verifica que descomprimiste el ZIP y copiaste los archivos JSON, no solo carpetas |
| Archivos en carpetas anidadas | Los JSON deben estar directamente en `corpus/`, no en subcarpetas |

## 📊 Tamaños Esperados

- **corpus.zip**: ~10.4 GB comprimido
- **Corpus descomprimido**: ~10.4 GB (~28,000 archivos)
- **Índice completo**: ~2.5 GB
  - `index.pkl`: ~2.4 GB
  - `index_metadata.json`: ~100 MB
  - `idf.json`: ~50 MB

---

Para más información sobre el proyecto completo, consulta el [README principal](../README.md).
