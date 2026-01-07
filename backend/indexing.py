import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
import json
import math
import pickle
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict, Counter
import re
import gc
from multiprocessing import Pool, cpu_count
from functools import partial
import os

# Importar psutil solo si se necesita monitoreo
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Descargar recursos NLTK
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Funciones para procesamiento paralelo

def process_document(doc_tuple, stemmer, stop_words):
    """Procesa un documento aplicando todas las fases de normalizacion."""
    doc_id, text = doc_tuple
    
    # Analisis lexico: normalizacion
    text = text.lower()
    text = re.sub(r'http\S+|www.\S+', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Tokenización
    try:
        tokens = word_tokenize(text)
    except:
        tokens = text.split()
    
    # Eliminación de stopwords y tokens cortos
    tokens = [t for t in tokens if t not in stop_words and len(t) > 2]
    
    # Stemming
    tokens = [stemmer.stem(t) for t in tokens]
    
    return (doc_id, tokens)


class IndexingEngine:
    """
    Motor de indexación que construye un índice invertido con pesos TF-IDF.
    Utiliza procesamiento paralelo para manejar grandes volúmenes de documentos.
    """

    def __init__(self, index_path="data/index", language='english', batch_size=500, 
                 num_workers=None, use_cpu_percent=70, enable_monitoring=False):
        """
        Args:
            index_path: Ruta para guardar índices
            language: Idioma
            batch_size: Documentos por lote
            num_workers: Número de procesos
            use_cpu_percent: % máximo de CPU a usar
            enable_monitoring: Activar monitoreo de RAM (psutil)
        """
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.language = language
        self.stemmer = SnowballStemmer(language)
        self.stop_words = set(stopwords.words(language))
        self.batch_size = batch_size
        
        # CPU control
        max_workers = max(1, cpu_count() - 2)
        self.num_workers = num_workers or max(1, int(max_workers * (use_cpu_percent / 100)))
        
        print(f"\nConfiguración de CPU:")
        print(f"  Total CPUs: {cpu_count()}")
        print(f"  CPUs a usar: {self.num_workers} ({use_cpu_percent}%)")
        print(f"  CPUs reservados para sistema: {cpu_count() - self.num_workers}\n")
        
        # Estructuras de datos
        self.inverted_index = defaultdict(lambda: defaultdict(int))
        self.document_index = {}
        self.idf = {}
        self.total_documents = 0
        
        # Monitoreo (OPCIONAL)
        self.enable_monitoring = enable_monitoring and PSUTIL_AVAILABLE
        if self.enable_monitoring:
            self.process = psutil.Process(os.getpid())
            print("Monitoreo de RAM activado\n")
        elif enable_monitoring and not PSUTIL_AVAILABLE:
            print("[WARNING] psutil no disponible, monitoreo desactivado\n")
        else:
            self.process = None

    def _get_memory_info(self):
        """Retorna uso de RAM en MB (0.0 si monitoreo desactivado)"""
        if self.process is None:
            return 0.0
        return self.process.memory_info().rss / 1024 / 1024

    def process_corpus(self, corpus, corpus_metadata=None):
        """Procesa el corpus en dos pasadas: cálculo de IDF y construcción del índice."""
        if corpus_metadata is None:
            corpus_metadata = {}
        
        print(f"\n{'='*70}")
        print(f"INDEXACION EN DOS PASADAS")
        print(f"{'='*70}\n")
        
        self.total_documents = len(corpus)
        corpus_items = list(corpus.items())
        
        # Pasada 1: Calcular DF/IDF
        print(f"\n{'-'*70}")
        print(f"PASADA 1: Tokenización y cálculo de DF/IDF")
        print(f"{'-'*70}\n")
        
        ram_inicio = self._get_memory_info()
        self._pass1_calculate_idf_only(corpus_items, corpus_metadata)
        ram_pass1 = self._get_memory_info()
        
        vocab_size = len(self.idf)
        print(f"\nPasada 1 completada: {vocab_size} términos")
        if self.enable_monitoring:
            print(f"  RAM inicio: {ram_inicio:.1f} MB")
            print(f"  RAM después Pasada 1: {ram_pass1:.1f} MB (+{ram_pass1 - ram_inicio:.1f} MB)\n")
        
        # Pasada 2: Construir índice invertido
        print(f"\n{'-'*70}")
        print(f"PASADA 2: Construcción del índice invertido")
        print(f"{'-'*70}\n")
        
        ram_antes_pass2 = self._get_memory_info()
        self._pass2_build_index_with_corpus(corpus_items)
        ram_pass2 = self._get_memory_info()
        
        print(f"\nPasada 2 completada: índice construido")
        if self.enable_monitoring:
            print(f"  RAM antes Pasada 2: {ram_antes_pass2:.1f} MB")
            print(f"  RAM después Pasada 2: {ram_pass2:.1f} MB\n")
        
        # Guardar en disco
        print("Guardando índices en disco...")
        self._save_index()
        print(f"Índices guardados\n")
        
        # Limpiar memoria
        gc.collect()
        
        ram_final = self._get_memory_info()
        
        print(f"{'='*70}")
        print(f"INDEXACION COMPLETADA")
        print(f"{'='*70}")
        if self.enable_monitoring:
            print(f"RAM Final: {ram_final:.1f} MB\n")
        else:
            print()

        return {
            'documents_processed': self.total_documents,
            'vocabulary_size': vocab_size,
            'index_size': len(self.inverted_index),
            'status': 'success',
            'num_workers': self.num_workers,
            'final_ram_mb': ram_final if self.enable_monitoring else None
        }

    def _pass1_calculate_idf_only(self, corpus_items, corpus_metadata):
        """Primera pasada: calcula la frecuencia de documentos e IDF de cada término."""
        document_frequency = defaultdict(int)
        
        print("Procesando corpus para calcular DF/IDF...\n")
        
        # Pool PERSISTENTE para todo PASS 1
        with Pool(self.num_workers) as pool:
            process_fn = partial(process_document, 
                               stemmer=self.stemmer, 
                               stop_words=self.stop_words)
            
            # Procesar en lotes
            for batch_start in range(0, len(corpus_items), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(corpus_items))
                batch_items = corpus_items[batch_start:batch_end]
                
                results = pool.map(process_fn, batch_items)
                
                # Procesar resultados SIN CACHEAR
                for doc_id, tokens in results:
                    # Guardar metadatos del documento
                    self.document_index[doc_id] = {
                        'processed': True,
                        'token_count': len(tokens),
                        **corpus_metadata.get(doc_id, {})
                    }
                    
                    # Actualizar frecuencia de documentos
                    unique_terms = set(tokens)
                    for term in unique_terms:
                        document_frequency[term] += 1
                
                batch_num = batch_start // self.batch_size + 1
                total_batches = (len(corpus_items) + self.batch_size - 1) // self.batch_size
                ram_actual = self._get_memory_info()
                docs_procesados = batch_end
                
                if self.enable_monitoring:
                    print(f" Lote {batch_num}/{total_batches}: {docs_procesados} docs | "
                          f"RAM: {ram_actual:.1f} MB (constante)")
                else:
                    print(f" Lote {batch_num}/{total_batches}: {docs_procesados} docs procesados")
                
                del results
                # Recolección de basura periódica
                if (batch_end % 2000) == 0:
                    gc.collect()
        
        # Calcular IDF global
        vocab_size = len(document_frequency)
        print(f"\nCalculando IDF global para {vocab_size} términos...")
        for term in tqdm(document_frequency.keys(), desc=" ", disable=False):
            docs_with_term = document_frequency[term]
            if docs_with_term > 0:
                # Formula IDF con suavizado
                self.idf[term] = math.log((1 + self.total_documents) / (1 + docs_with_term)) + 1
            else:
                self.idf[term] = 0
        
        self._save_idf()

    def _pass2_build_index_with_corpus(self, corpus_items):
        """Segunda pasada: construye el índice invertido con frecuencias de términos."""
        print("Construyendo índice invertido...\n")
        
        # Pool PERSISTENTE para PASS 2
        with Pool(self.num_workers) as pool:
            process_fn = partial(process_document, 
                               stemmer=self.stemmer, 
                               stop_words=self.stop_words)
            
            # Procesar en lotes
            for batch_start in range(0, len(corpus_items), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(corpus_items))
                batch_items = corpus_items[batch_start:batch_end]
                
                results = pool.map(process_fn, batch_items)
                
                for doc_id, tokens in results:
                    # Construir índice
                    term_freq = Counter(tokens)
                    for term, freq in term_freq.items():
                        self.inverted_index[term][doc_id] = freq
                
                batch_num = batch_start // self.batch_size + 1
                total_batches = (len(corpus_items) + self.batch_size - 1) // self.batch_size
                ram_actual = self._get_memory_info()
                docs_procesados = batch_end
                
                if self.enable_monitoring:
                    print(f" Lote {batch_num}/{total_batches}: {docs_procesados} docs | "
                          f"RAM: {ram_actual:.1f} MB")
                else:
                    print(f" Lote {batch_num}/{total_batches}: {docs_procesados} docs indexados")
                
                del results
                # Recolección de basura periódica
                if (batch_end % 2000) == 0:
                    gc.collect()

    def _save_index(self):
        """Guarda el índice invertido en formato pickle."""
        
        index_pickle = self.index_path / "index.pkl"
        
        index_data = {
            'inverted_index': dict(self.inverted_index),
            'vocabulary_size': len(self.idf),
            'document_count': len(self.document_index),
            'document_index': self.document_index,
            'idf': self.idf,
            'total_documents': self.total_documents
        }
        
        with open(index_pickle, 'wb') as f:
            pickle.dump(index_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        print(f"Guardado: {index_pickle}")
        
        # Guardar metadatos en JSON
        index_json = self.index_path / "index_metadata.json"
        json_data = {
            'vocabulary_size': len(self.idf),
            'document_count': len(self.document_index),
            'index_entries': len(self.inverted_index),
            'status': 'indexed'
        }
        
        with open(index_json, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"Guardado: {index_json}")

    def _save_idf(self):
        """Guardar IDF para referencia."""
        idf_file = self.index_path / "idf.json"
        with open(idf_file, 'w', encoding='utf-8') as f:
            json.dump(self.idf, f, ensure_ascii=False)

    def load_index(self):
        """Carga el índice desde disco."""
        index_pickle = self.index_path / "index.pkl"
        
        if not index_pickle.exists():
            index_json = self.index_path / "index.json"
            if not index_json.exists():
                print("No index found.")
                return False
            
            try:
                with open(index_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                return False
        else:
            try:
                with open(index_pickle, 'rb') as f:
                    data = pickle.load(f)
            except:
                return False
        
        try:
            self.inverted_index = defaultdict(lambda: defaultdict(int))
            for term, docs in data['inverted_index'].items():
                for doc_id, freq in docs.items():
                    self.inverted_index[term][doc_id] = freq
            
            self.document_index = data['document_index']
            self.idf = data.get('idf', {})
            self.total_documents = data.get('total_documents', len(self.document_index))
            
            vocab_size = len(self.idf)
            print(f"Índice cargado: {vocab_size} términos, {len(self.document_index)} documentos")
            return True
            
        except Exception as e:
            print(f"Error cargando: {e}")
            return False

    def get_index_statistics(self):
        """Retorna estadísticas del índice (usa IDF como fuente única)"""
        return {
            'vocabulary_size': len(self.idf),
            'documents_indexed': len(self.document_index),
            'index_entries': len(self.inverted_index),
            'avg_postings_per_term': (
                sum(len(docs) for docs in self.inverted_index.values()) /
                max(1, len(self.inverted_index))
            ) if self.inverted_index else 0
        }