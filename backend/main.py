from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import json
import time

# Importar módulos propios
from corpus_handler import CorpusHandler
from indexing import IndexingEngine
from search_engine import SearchEngine
from evaluation import evaluate_search_engine, generate_evaluation_report, evaluate_single_query

# Crear aplicación FastAPI
app = FastAPI(
    title="Information Retrieval System",
    description="Sistema de Recuperación de Información con FastAPI",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales
corpus_handler = CorpusHandler()
indexing_engine = None
search_engine = None


def _load_index_if_exists():
    """
    Carga índice automáticamente si existe en disco
    """
    global indexing_engine, search_engine

    backend_dir = Path(__file__).resolve().parent
    index_path = backend_dir / "data" / "index"
    index_pickle = index_path / "index.pkl"

    if index_pickle.exists():
        print(f"\n{'='*70}")
        print(f"ÍNDICE DETECTADO EN DISCO")
        print(f"   Ruta: {index_pickle}")
        print(f"{'='*70}\n")

        try:
            indexing_engine = IndexingEngine(
                index_path=str(index_path),
                language='english',
                enable_monitoring=True
            )

            success = indexing_engine.load_index()

            if success:
                search_engine = SearchEngine(indexing_engine)
                stats = indexing_engine.get_index_statistics()

                print(f"\nÍNDICE CARGADO EXITOSAMENTE")
                print(f"   Vocabulario: {stats['vocabulary_size']} términos")
                print(f"   Documentos: {stats['documents_indexed']}")
                print(f"   Entradas de índice: {stats['index_entries']}")
                print(f"   Postings promedio por término: {stats['avg_postings_per_term']:.2f}\n")

                return True
            else:
                print("Error cargando índice desde pickle\n")
                indexing_engine = None
                search_engine = None
                return False

        except Exception as e:
            print(f"Error al cargar índice: {e}\n")
            indexing_engine = None
            search_engine = None
            return False
    else:
        print(f"\n{'='*70}")
        print(f"NO HAY ÍNDICE EN DISCO")
        print(f"   Ejecuta POST /api/index/build primero")
        print(f"{'='*70}\n")
        return False


@app.on_event("startup")
async def startup_event():
    """Se ejecuta cuando FastAPI inicia."""
    print("\n" + "="*70)
    print("INICIANDO INFORMATION RETRIEVAL SYSTEM")
    print("="*70)

    _load_index_if_exists()

    print("SISTEMA LISTO\n")


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


@app.get("/")
def hello():
    """Endpoint raiz que verifica que el servidor esta activo."""
    return {
        "message": "Information Retrieval System Active",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    """Verifica el estado del sistema y sus componentes."""
    global corpus_handler, indexing_engine, search_engine

    corpus_stats = corpus_handler.get_corpus_statistics()

    index_status = "not_loaded"
    index_stats = {
        'vocabulary_size': 0,
        'documents_indexed': 0,
        'index_entries': 0
    }

    if indexing_engine is not None:
        index_status = "loaded"
        index_stats = indexing_engine.get_index_statistics()

    return {
        "status": "healthy",
        "corpus_loaded": corpus_stats['documents'] > 0,
        "corpus_docs": corpus_stats['documents'],
        "corpus_size_gb": round(corpus_stats['size_gb'], 2),
        "index_status": index_status,
        "index_vocabulary": index_stats['vocabulary_size'],
        "index_documents": index_stats['documents_indexed'],
        "search_ready": search_engine is not None
    }


@app.get("/api/index/stats")
def get_index_stats():
    """Retorna estadísticas del índice."""
    global indexing_engine, search_engine, corpus_handler

    if indexing_engine is None or search_engine is None:
        return {
            "status": "not_ready",
            "documents_count": 0,
            "vocabulary_size": 0,
            "index_size": 0,
            "message": "Index not loaded. Call POST /api/index/build"
        }

    try:
        stats = indexing_engine.get_index_statistics()
        corpus_stats = corpus_handler.get_corpus_statistics()

        return {
            "status": "success",
            "documents_count": stats['documents_indexed'],
            "vocabulary_size": stats['vocabulary_size'],
            "index_size": stats['index_entries'],
            "avg_postings_per_term": round(stats['avg_postings_per_term'], 2),
            "corpus_size_gb": round(corpus_stats['size_gb'], 2)
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/search")
def search(query: str = "", top_k: int = 10):
    """
    Realiza búsqueda en el índice construido.
    Endpoint GET como especifica el PDF: /search?query=...
    """
    global search_engine, indexing_engine

    try:
        if not query.strip():
            return {
                "status": "error",
                "message": "Query is empty",
                "results": []
            }

        if search_engine is None or indexing_engine is None:
            raise HTTPException(
                status_code=400,
                detail="Index not loaded. Call POST /api/index/build or check disk for existing index."
            )

        # Medir tiempo de búsqueda
        start_time = time.time()
        results = search_engine.search(query, top_k=top_k)
        elapsed_time = (time.time() - start_time) * 1000  # milisegundos

        print(f"Búsqueda completada en {elapsed_time:.0f} ms")
        print(f"   Resultados retornados: {len(results)}")

        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results),
            "elapsed_ms": round(elapsed_time, 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error searching: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search-with-metrics")
def search_with_metrics(query: str = "", top_k: int = 10):
    """
    Realiza búsqueda y calcula métricas de evaluación para la consulta específica.
    Retorna resultados + Precision@k, Recall@k, AP y RR para ESTA consulta.
    """
    global search_engine, indexing_engine

    try:
        if not query.strip():
            return {
                "status": "error",
                "message": "Query is empty",
                "results": [],
                "metrics": {}
            }

        if search_engine is None or indexing_engine is None:
            raise HTTPException(
                status_code=400,
                detail="Index not loaded. Call POST /api/index/build or check disk for existing index."
            )

        # Medir tiempo de búsqueda
        start_time = time.time()
        results = search_engine.search(query, top_k=top_k)
        elapsed_time = (time.time() - start_time) * 1000

        # Calcular métricas para esta consulta específica
        metrics = evaluate_single_query(results, query, k_values=[5, 10, 20])

        print(f"Búsqueda con métricas completada en {elapsed_time:.0f} ms")
        print(f"   Resultados: {len(results)}, Relevantes: {metrics['relevant_found']}")
        print(f"   AP: {metrics['average_precision']}, RR: {metrics['reciprocal_rank']}")

        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results),
            "elapsed_ms": round(elapsed_time, 2),
            "metrics": {
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "average_precision": metrics["average_precision"],
                "reciprocal_rank": metrics["reciprocal_rank"],
                "relevant_found": metrics["relevant_found"],
                "total_results": metrics["total_results"]
            },
            "relevance_details": metrics["relevance_details"]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in search with metrics: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/index/build")
def build_index():
    """Construye el índice desde cero."""
    global corpus_handler, indexing_engine, search_engine

    try:
        print("\n[BACKEND] Iniciando construcción de índice...")
        print("[BACKEND] Cargando corpus desde disco...")

        corpus = corpus_handler.load_corpus()

        if not corpus:
            raise HTTPException(
                status_code=400,
                detail="Corpus vacío. Descarga documentos primero con download_corpus_standalone.py"
            )

        print(f"[BACKEND] Corpus cargado: {len(corpus)} documentos")

        # Obtener metadatos del corpus
        corpus_metadata = corpus_handler.corpus_metadata
        print(f"[BACKEND] Metadatos disponibles para {len(corpus_metadata)} documentos")

        backend_dir = Path(__file__).resolve().parent
        index_path = backend_dir / "data" / "index"

        indexing_engine = IndexingEngine(
            index_path=str(index_path),
            language='english',
            enable_monitoring=True
        )

        print("[BACKEND] Ejecutando fases de indexación...")

        # Pasar corpus_metadata al proceso
        result = indexing_engine.process_corpus(corpus, corpus_metadata=corpus_metadata)

        # Crear SearchEngine con el índice construido
        search_engine = SearchEngine(indexing_engine)

        stats = indexing_engine.get_index_statistics()

        print("\nÍNDICE CONSTRUIDO EXITOSAMENTE")
        print(f"   Documentos: {stats['documents_indexed']}")
        print(f"   Vocabulario: {stats['vocabulary_size']} términos")
        print(f"   Entradas de índice: {stats['index_entries']}")
        print(f"   Postings promedio: {stats['avg_postings_per_term']:.2f}\n")

        return {
            "status": "success",
            "message": f"Índice construido con {stats['documents_indexed']} documentos",
            "documents_count": stats['documents_indexed'],
            "vocabulary_size": stats['vocabulary_size'],
            "index_size": stats['index_entries']
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[BACKEND] Error construyendo índice: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lexical_analysis")
def lexical_analysis(text: str = ""):
    """Realiza analisis lexico en un texto."""
    if not text:
        return {"status": "error", "message": "Empty text"}

    normalized = text.lower().strip()

    return {
        "status": "success",
        "original": text,
        "normalized": normalized
    }

@app.get("/api/tokenize")
def tokenize(text: str = ""):
    """Tokeniza un texto."""
    if not text:
        return {"status": "error", "message": "Empty text"}

    tokens = text.split()

    return {
        "status": "success",
        "text": text,
        "tokens": tokens,
        "count": len(tokens)
    }


@app.post("/api/reload")
def reload_system():
    """Recarga el sistema sin reiniciar el servidor."""
    global corpus_handler, indexing_engine, search_engine

    print("\n[BACKEND] Recargando sistema...")

    corpus_handler = CorpusHandler()
    indexing_engine = None
    search_engine = None

    success = _load_index_if_exists()

    return {
        "status": "success" if success else "partial",
        "index_loaded": success
    }


@app.get("/api/evaluate")
def evaluate_system():
    """
    Ejecuta evaluación del sistema con métricas estándar de IR.
    Retorna Precision@k, Recall@k, MAP y MRR.
    """
    global search_engine

    if search_engine is None:
        raise HTTPException(
            status_code=400,
            detail="Search engine not loaded. Load index first."
        )

    try:
        metrics = evaluate_search_engine(search_engine, k_values=[5, 10, 20])
        
        return {
            "status": "success",
            "metrics": metrics,
            "interpretation": {
                "MAP": "Mean Average Precision - promedio de precision en todos los puntos de recall",
                "MRR": "Mean Reciprocal Rank - promedio del inverso de la posicion del primer doc relevante",
                "P@k": "Precision at k - proporcion de docs relevantes en top k",
                "R@k": "Recall at k - proporcion de docs relevantes recuperados en top k"
            }
        }
    except Exception as e:
        print(f"Error in evaluation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)