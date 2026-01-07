import json
import math
from pathlib import Path
from collections import defaultdict, Counter
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
import re
import time

class SearchEngine:
    """
    Motor de búsqueda basado en BM25.
    BM25 es el algoritmo estándar en motores de búsqueda modernos.
    """
    
    def __init__(self, indexing_engine):
        """Inicializa el motor de búsqueda con el índice invertido."""
        self.indexing_engine = indexing_engine
        self.inverted_index = indexing_engine.inverted_index
        self.idf = indexing_engine.idf
        self.document_index = indexing_engine.document_index
        self.stemmer = SnowballStemmer('english')
        self.stop_words = set(stopwords.words('english'))
        
        # Parámetros BM25
        self.k1 = 1.5  # Saturación de frecuencia de término
        self.b = 0.75  # Normalización por longitud de documento
        
        # Calcular longitud promedio de documentos
        self.avgdl = self._calculate_avgdl()
        self.total_docs = len(self.document_index)
        
        print(f"SearchEngine BM25 inicializado")
        print(f"  Términos en vocabulario: {len(self.idf)}")
        print(f"  Documentos indexados: {self.total_docs}")
        print(f"  Longitud promedio: {self.avgdl:.0f} tokens")
    
    def _calculate_avgdl(self):
        """Calcula la longitud promedio de los documentos."""
        if not self.document_index:
            return 1
        total_tokens = sum(
            doc.get('token_count', 0) 
            for doc in self.document_index.values()
        )
        return total_tokens / max(1, len(self.document_index))
    
    def search(self, query, top_k=10):
        """
        Busca documentos usando BM25.
        
        BM25 produce scores mas discriminativos que TF-IDF con coseno,
        penalizando documentos largos y saturando frecuencias altas.
        """
        start_time = time.time()
        
        if not self.inverted_index or not self.idf:
            return []
        
        query_terms = self._process_query(query)
        
        if not query_terms:
            return []
        
        # Calcular scores BM25
        scores = defaultdict(float)
        matching_terms = defaultdict(set)
        
        for term in query_terms:
            if term not in self.inverted_index:
                continue
                
            idf = self.idf.get(term, 0)
            docs_with_term = self.inverted_index[term]
            
            for doc_id, freq in docs_with_term.items():
                doc_info = self.document_index.get(doc_id, {})
                doc_len = doc_info.get('token_count', 1)
                
                # Formula BM25
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))
                
                scores[doc_id] += idf * (numerator / denominator)
                matching_terms[doc_id].add(term)
        
        if not scores:
            return []
        
        # Normalizar scores a porcentaje
        # Usamos un score teórico máximo basado en el número de términos de la query
        # para que los porcentajes sean más informativos
        max_theoretical = len(query_terms) * 10  # Score teórico máximo
        max_score = max(scores.values())
        
        for doc_id in scores:
            # Escala relativa al máximo teórico, con tope en 99%
            normalized = (scores[doc_id] / max(max_theoretical, max_score)) * 100
            scores[doc_id] = min(99, normalized)
        
        # Ordenar por score descendente
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in ranked[:top_k]:
            doc_info = self.document_index.get(doc_id, {})
            text_preview = doc_info.get('text_preview', '')
            snippet = self._extract_snippet(text_preview, list(matching_terms[doc_id]))
            
            results.append({
                'doc_id': doc_id,
                'title': doc_info.get('title', 'Sin título'),
                'score': round(score, 4),
                'language': doc_info.get('language', 'en'),
                'snippet': snippet,
                'token_count': doc_info.get('token_count', 0),
                'matching_terms': list(matching_terms[doc_id]),
                'matching_terms_count': len(matching_terms[doc_id])
            })
        
        elapsed_ms = (time.time() - start_time) * 1000
        print(f"Búsqueda completada en {elapsed_ms:.0f} ms")
        print(f"  Documentos evaluados: {len(scores)}")
        print(f"  Resultados retornados: {len(results)}")
        
        return results
    
    def _process_query(self, query):
        """Procesa la consulta del usuario y devuelve lista de términos stemizados."""
        # Normalizar
        query = query.lower()
        query = re.sub(r'[^\w\s]', ' ', query)
        query = re.sub(r'\s+', ' ', query).strip()
        
        # Tokenizar
        try:
            tokens = word_tokenize(query)
        except:
            tokens = query.split()
        
        # Eliminar stopwords
        tokens = [t for t in tokens if t not in self.stop_words and len(t) > 2]
        
        if not tokens:
            return []
        
        # Aplicar stemming
        tokens = [self.stemmer.stem(t) for t in tokens]
        
        return tokens
    
    def _extract_snippet(self, text_preview, query_terms, max_length=100):
        """Extrae un fragmento relevante del texto que contenga términos de la consulta."""
        if not text_preview:
            return "Vista previa no disponible"
        
        # Limpiar y normalizar
        text = text_preview.lower()
        
        # Si no hay términos de consulta, retornar inicio del texto
        if not query_terms:
            snippet = text_preview[:max_length].strip()
            if len(text_preview) > max_length:
                snippet += "..."
            return f'"{snippet}"'
        
        # Buscar primera ocurrencia de algún término de la consulta
        for term in query_terms:
            term_lower = term.lower()
            pos = text.find(term_lower)
            
            if pos != -1:
                # Encontré el término, extrae contexto
                start = max(0, pos - 20)
                end = min(len(text), start + max_length)
                
                snippet = text_preview[start:end].strip()
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text_preview):
                    snippet = snippet + "..."
                
                return f'"{snippet}"'
        
        # Fallback: primeras max_length caracteres
        snippet = text_preview[:max_length].strip()
        if len(text_preview) > max_length:
            snippet += "..."
        
        return f'"{snippet}"'
    
    def get_document_content(self, doc_id):
        """Obtiene información detallada del documento."""
        doc_info = self.document_index.get(doc_id, {})
        return {
            'title': doc_info.get('title', 'Unknown'),
            'author': doc_info.get('author', 'Unknown'),
            'download_count': doc_info.get('download_count', 0),
            'language': doc_info.get('language', 'en'),
            'token_count': doc_info.get('token_count', 0),
            'doc_id': doc_id
        }
    
    def get_search_statistics(self):
        """Retorna estadísticas del índice."""
        return {
            'vocabulary_size': len(self.idf),
            'documents_indexed': len(self.document_index),
            'inverted_index_size': len(self.inverted_index),
            'index_status': 'Ready' if self.inverted_index else 'Empty'
        }
