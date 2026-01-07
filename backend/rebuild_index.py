import sys
from pathlib import Path
import time

# Agregar backend al path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Importar módulos
from corpus_handler import CorpusHandler
from indexing import IndexingEngine

def main():
    """
    Función principal: Reconstruir índice desde cero
    """
    
    print("\n" + "="*70)
    print("🔧 REBUILD INDEX - Script Standalone")
    print("="*70)
    
    # PASO 1: Inicializar CorpusHandler
    
    print("\n[PASO 1] Inicializando CorpusHandler...")
    corpus_handler = CorpusHandler()
    
    corpus_stats = corpus_handler.get_corpus_statistics()
    print(f"  Corpus path: {corpus_handler.corpus_path}")
    print(f"  Documentos detectados: {corpus_stats['documents']}")
    print(f"  Tamaño total: {corpus_stats['size_gb']:.2f} GB")
    
    # Paso 2: Cargar corpus
    print("\n[PASO 2] Cargando corpus desde disco...")
    start_load = time.time()
    
    corpus = corpus_handler.load_corpus()
    
    if not corpus:
        print("ERROR: Corpus vacio")
        print("   Ejecuta primero: python download_corpus_standalone.py")
        return False
    
    load_time = time.time() - start_load
    print(f"  Corpus cargado en {load_time:.2f}s")
    print(f"  {len(corpus)} documentos")
    
    # Paso 3: Obtener metadatos
    print("\n[PASO 3] Preparando metadatos...")
    corpus_metadata = corpus_handler.corpus_metadata
    
    print(f"  Metadatos disponibles: {len(corpus_metadata)}")
    
    if len(corpus_metadata) > 0:
        # Mostrar ejemplo
        first_doc_id = list(corpus_metadata.keys())[0]
        first_meta = corpus_metadata[first_doc_id]
        print(f"\n  Ejemplo (doc: {first_doc_id}):")
        print(f"    - Título: {first_meta.get('title', 'N/A')}")
        print(f"    - Autor: {first_meta.get('author', 'N/A')}")
        print(f"    - Descargas: {first_meta.get('download_count', 0)}")
        print(f"    - Idioma: {first_meta.get('language', 'N/A')}\n")
    
    # Paso 4: Inicializar IndexingEngine
    print("[PASO 4] Inicializando IndexingEngine...")
    index_path = backend_dir / "data" / "index"
    
    indexing_engine = IndexingEngine(
        index_path=str(index_path),
        language='english',
        batch_size=500,
        num_workers=None,
        use_cpu_percent=70,
        enable_monitoring=True
    )
    
    print(f"  Ruta de índice: {index_path}")
    
    # Paso 5: Ejecutar indexación
    print("\n[PASO 5] Ejecutando indexación...")
    print("  Esto puede tomar varios minutos...\n")
    
    start_index = time.time()
    
    result = indexing_engine.process_corpus(corpus, corpus_metadata=corpus_metadata)
    
    index_time = time.time() - start_index
    
    print(f"\n  Indexación completada en {index_time:.2f}s")
    
    # Paso 6: Mostrar resultados
    print("\n[PASO 6] Resumen de indexación:\n")
    
    print(f"  Documentos procesados:     {result['documents_processed']:>10}")
    print(f"  Vocabulario (términos):    {result['vocabulary_size']:>10}")
    print(f"  Entradas de índice:        {result['index_size']:>10}")
    print(f"  CPUs utilizados:           {result['num_workers']:>10}")
    
    if result['final_ram_mb'] is not None:
        print(f"  RAM final:                 {result['final_ram_mb']:>10.1f} MB")
    
    print(f"\n  Estado:                    {result['status']}")
    
    # Paso 7: Verificar índice
    print("\n[PASO 7] Verificando índice...")
    
    # Cargar índice desde disco
    indexing_engine_verify = IndexingEngine(
        index_path=str(index_path),
        language='english'
    )
    
    success = indexing_engine_verify.load_index()
    
    if success:
        stats = indexing_engine_verify.get_index_statistics()
        print(f"  Índice cargado correctamente desde disco")
        print(f"    - Vocabulario: {stats['vocabulary_size']} términos")
        print(f"    - Documentos: {stats['documents_indexed']}")
        print(f"    - Postings promedio: {stats['avg_postings_per_term']:.2f}")
    else:
        print(f"  ERROR cargando índice desde disco")
        return False
    
    # Resumen final
    print("\n" + "="*70)
    print("REBUILD COMPLETADO")
    print("="*70)
    
    print("\nPróximos pasos:")
    print("  1. En otra terminal: uvicorn backend.main:app --reload")
    print("  2. Abre en navegador: http://localhost:8000")
    print("  3. Ve a POST /api/search")
    print("  4. Prueba búsquedas")
    
    print("\nArchivos generados:")
    print(f"  - {index_path / 'index.pkl'}")
    print(f"  - {index_path / 'index_metadata.json'}")
    print(f"  - {index_path / 'idf.json'}")
    
    print("\n" + "="*70 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)