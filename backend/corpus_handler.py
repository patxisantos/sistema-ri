import os
import json
import requests
from pathlib import Path
from tqdm import tqdm
import re
from datetime import datetime

class CorpusHandler:
    """
    Gestor de la colección documental.
    Lee el corpus descargado y extrae títulos, autores y metadatos.
    """

    def __init__(self, corpus_path=None):
        """
        Inicializa el gestor de corpus.
        Args:
            corpus_path: Si None, calcula ruta automáticamente desde este archivo
        """
        if corpus_path is None:
            # Ruta ABSOLUTA: desde este archivo al backend, luego data/corpus
            current_file = Path(__file__).resolve()
            backend_dir = current_file.parent
            corpus_path = backend_dir / "data" / "corpus"
        else:
            corpus_path = Path(corpus_path).resolve()

        self.corpus_path = corpus_path
        self.corpus_path.mkdir(parents=True, exist_ok=True)
        self.corpus_metadata = {}
        self.corpus_size = 0
        self.documents_count = 0

        print(f"[CorpusHandler] Corpus path: {self.corpus_path}")
        # Cargar info del disco al inicializar
        self._scan_corpus()

    def _scan_corpus(self):
        """
        Escanea el corpus en disco y calcula documentos y tamaño.
        """
        total_size = 0
        doc_count = 0

        if not self.corpus_path.exists():
            return

        json_files = [f for f in self.corpus_path.glob("*.json")
                      if f.name != "download_metadata.json"]

        for file_path in json_files:
            try:
                total_size += file_path.stat().st_size
                doc_count += 1
            except:
                pass

        self.corpus_size = total_size
        self.documents_count = doc_count

    def load_corpus(self):
        """
        Carga todos los documentos del corpus desde ficheros JSON.
        Extrae títulos, autores y metadatos.
        Returns:
            dict: Diccionario con {doc_id: contenido}
        """
        corpus = {}

        if not self.corpus_path.exists():
            print(f"Ruta del corpus no existe: {self.corpus_path}")
            return corpus

        json_files = [f for f in self.corpus_path.glob("*.json")
                      if f.name != "download_metadata.json"]

        print(f"\n{'='*70}")
        print(f"CARGANDO CORPUS: {len(json_files)} documentos desde disco")
        print(f"Ruta: {self.corpus_path}")
        print(f"{'='*70}")

        if len(json_files) == 0:
            print(f"No se encontraron documentos en {self.corpus_path}")
            return corpus

        total_size = 0

        for file_path in tqdm(json_files, desc="Cargando documentos"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    doc = json.load(f)

                # Soportar diferentes formatos de documento
                text = doc.get('content') or doc.get('text', '')
                doc_id = doc.get('id', file_path.stem)

                if text:
                    corpus[doc_id] = text
                    total_size += len(text.encode('utf-8'))

                    # Extraer metadatos del documento
                    title = (
                        doc.get('title') or
                        doc.get('name') or
                        doc.get('full_title') or
                        'Documento sin título'
                    )

                    # Extraer autor
                    author = (
                        doc.get('author') or
                        doc.get('authors') or
                        doc.get('author_name') or
                        'Autor desconocido'
                    )

                    # Manejar casos donde author es una lista
                    if isinstance(author, list) and author:
                        author = author[0] if isinstance(author[0], str) else str(author[0])

                    # Información adicional
                    download_count = doc.get('download_count', 0)
                    language = doc.get('language', 'en')
                    gutendex_id = doc.get('gutendex_id', None)
                    
                    # Extraer vista previa del texto (primeros 500 caracteres)
                    text_preview = text[:500] if len(text) > 500 else text

                    # Guardar metadatos
                    self.corpus_metadata[doc_id] = {
                        'title': str(title),
                        'author': str(author),
                        'size': len(text.encode('utf-8')),
                        'download_count': download_count,
                        'language': language,
                        'gutendex_id': gutendex_id,
                        'text_preview': text_preview
                    }

            except Exception as e:
                print(f"Error cargando {file_path.name}: {e}")
                continue

        self.documents_count = len(corpus)
        self.corpus_size = total_size

        print(f"\n{'='*70}")
        print(f"CORPUS CARGADO:")
        print(f"  Documentos: {self.documents_count}")
        print(f"  Tamaño total: {total_size / (1024*1024*1024):.2f} GB")
        if self.documents_count > 0:
            print(f"  Tamaño promedio: {total_size / self.documents_count / (1024*1024):.2f} MB/doc")
        print(f"{'='*70}\n")

        return corpus

    def get_corpus_statistics(self):
        """
        Obtiene estadísticas del corpus leyendo del disco si es necesario.
        Returns:
            dict: Estadísticas del corpus
        """
        # Si no tenemos info, escanear disco
        if self.documents_count == 0:
            self._scan_corpus()

        return {
            'documents': self.documents_count,
            'size_gb': self.corpus_size / (1024*1024*1024),
            'size_mb': self.corpus_size / (1024*1024),
            'average_doc_size_mb': self.corpus_size / max(1, self.documents_count) / (1024*1024),
            'metadata': self.corpus_metadata
        }

    def _normalize_text(self, text):
        """
        Normaliza el texto eliminando caracteres problemáticos.
        Args:
            text: Texto a normalizar
        Returns:
            str: Texto normalizado
        """
        # Eliminar saltos de línea múltiples
        text = re.sub(r'\n+', '\n', text)
        # Eliminar espacios múltiples
        text = re.sub(r' +', ' ', text)
        # Eliminar caracteres de control
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        return text.strip()