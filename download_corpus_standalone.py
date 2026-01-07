import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import random

class CorpusCreator:
    """Creador de corpus con Project Gutenberg."""
    
    def __init__(self, base_path="backend/data/corpus"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.base_path / "download_metadata.json"
        
        # User-Agent para Gutenberg
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Thread safety
        self.size_lock = threading.Lock()
        self.count_lock = threading.Lock()
        
        self.current_size = 0
        self.doc_count = 0
        
        # IDs populares de Gutenberg (los más grandes y conocidos)
        # Estos son libros en inglés que funcionan bien
        self.gutenberg_ids = self._generate_gutenberg_ids()
        
        self.load_metadata()
        
    def _generate_gutenberg_ids(self) -> list:
        """
        Genera lista de IDs de Gutenberg.
        Rango 1-70000 (libros disponibles).
        """
        # IDs conocidos que funcionan bien (grandes clásicos)
        known_good = [
            1, 2, 11, 84, 98, 100, 219, 345, 730, 1080, 1184, 1342, 1400, 1661, 
            2542, 2600, 2701, 4300, 5200, 6130, 7370, 8800, 10676, 16328, 23700,
            25344, 30254, 35688, 41445, 45502, 51060, 55456, 60006, 64317, 67098
        ]
        
        # Generar rango completo (1-70000)
        all_ids = list(range(1, 70001))
        
        # Mezclar para variedad
        random.shuffle(all_ids)
        
        # Priorizar conocidos + resto aleatorio
        return known_good + all_ids
    
    def load_metadata(self):
        """Carga metadatos."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                'total_size': 0,
                'documents_count': 0,
                'last_update': None,
                'downloaded_ids': []
            }
    
    def save_metadata(self):
        """Guarda metadatos."""
        self.metadata['total_size'] = self.current_size
        self.metadata['documents_count'] = self.doc_count
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)
    
    def get_current_size(self) -> int:
        """Obtiene tamaño total actual."""
        total = 0
        count = 0
        for f in self.base_path.glob("*.json"):
            if f.name not in ["download_metadata.json", "metadata.json"]:
                try:
                    total += f.stat().st_size
                    count += 1
                except:
                    pass
        self.current_size = total
        self.doc_count = count
        return total
    
    def download_book(self, book_id: int, session: requests.Session) -> dict:
        """
        Descarga UN libro de Gutenberg.
        Intenta varios formatos hasta encontrar uno que funcione.
        """
        try:
            # URLs posibles para el libro (intentar varias)
            urls = [
                f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",  # UTF-8
                f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt",     # ASCII
                f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",  # Cache
            ]
            
            content = None
            for url in urls:
                try:
                    response = session.get(url, timeout=10, allow_redirects=True)
                    
                    if response.status_code == 200 and len(response.content) > 10000:
                        content = response.text
                        break
                except:
                    continue
            
            if not content or len(content) < 10000:
                return None
            
            # Extraer título (buscar en las primeras líneas)
            title = f"Gutenberg Book {book_id}"
            lines = content.split('\n')[:50]
            for line in lines:
                if 'Title:' in line:
                    title = line.split('Title:')[-1].strip()
                    break
            
            # Crear documento
            doc_id = f"gutenberg_{book_id}_{int(time.time() * 1000000)}"
            doc_path = self.base_path / f"{doc_id}.json"
            
            doc_data = {
                'id': doc_id,
                'title': title,
                'content': content,
                'source': 'Project Gutenberg',
                'book_id': book_id,
                'size': len(content.encode('utf-8')),
                'downloaded_at': datetime.now().isoformat()
            }
            
            # Guardar
            with open(doc_path, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, ensure_ascii=False)
            
            # Actualizar contadores (thread-safe)
            with self.size_lock:
                self.current_size += doc_data['size']
            
            with self.count_lock:
                self.doc_count += 1
            
            # Marcar como descargado
            if 'downloaded_ids' not in self.metadata:
                self.metadata['downloaded_ids'] = []
            self.metadata['downloaded_ids'].append(book_id)
            
            return doc_data
        
        except Exception as e:
            return None
    
    def download_parallel(self, target_size: int, workers: int = 20):
        """
        Descarga paralela de Gutenberg.
        """
        print("\n" + "="*70)
        print("PROJECT GUTENBERG - DESCARGA PARALELA")
        print("="*70)
        print(f"Workers: {workers}")
        print(f"Target: {target_size / (1024**3):.2f} GB")
        print("="*70 + "\n")
        
        # Session para reutilizar conexiones
        session = requests.Session()
        session.headers.update(self.headers)
        
        # Ya descargados
        downloaded_ids = set(self.metadata.get('downloaded_ids', []))
        
        # IDs disponibles
        available_ids = [book_id for book_id in self.gutenberg_ids if book_id not in downloaded_ids]
        
        idx = 0
        batch_size = 50
        
        try:
            while self.current_size < target_size and idx < len(available_ids):
                # Obtener batch
                batch = available_ids[idx:idx + batch_size]
                idx += batch_size
                
                print(f"[Batch {idx // batch_size}] Descargando {len(batch)} libros en paralelo...")
                
                # Descargar en paralelo
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = [
                        executor.submit(self.download_book, book_id, session)
                        for book_id in batch
                    ]
                    
                    # Esperar resultados
                    completed = 0
                    for future in as_completed(futures):
                        result = future.result()
                        if result:
                            completed += 1
                
                # Mostrar progreso
                size_mb = self.current_size / (1024**2)
                target_mb = target_size / (1024**2)
                percentage = (self.current_size / target_size * 100) if target_size > 0 else 0
                
                print(f"  {completed}/{len(batch)} exitosos | Total: {self.doc_count} docs | {size_mb:.1f} MB / {target_mb:.1f} MB [{percentage:.1f}%]")
                
                # Verificar target
                if self.current_size >= target_size:
                    print(f"\nTARGET ALCANZADO: {size_mb:.1f} MB")
                    break
                
                # Guardar progreso cada 5 batches
                if (idx // batch_size) % 5 == 0:
                    self.save_metadata()
        
        except KeyboardInterrupt:
            print("\nDescarga cancelada por usuario")
        
        finally:
            session.close()
            self.save_metadata()
    
    def create_corpus(self, target_gb: float, workers: int = 20):
        """Crea corpus hasta alcanzar tamaño objetivo."""
        
        target_bytes = int(target_gb * 1024**3)
        
        # Cargar tamaño actual
        self.get_current_size()
        
        print("\n" + "="*70)
        print("CORPUS CREATOR - PROJECT GUTENBERG")
        print("="*70)
        print(f"Tamaño actual:    {self.current_size / (1024**3):.2f} GB ({self.doc_count} docs)")
        print(f"Tamaño objetivo:  {target_gb:.2f} GB")
        remaining = max(0, target_bytes - self.current_size)
        print(f"Falta descargar:  {remaining / (1024**3):.2f} GB")
        print("="*70)
        
        if self.current_size >= target_bytes:
            print(f"\nTarget ya alcanzado!")
            return
        
        start_time = time.time()
        
        try:
            self.download_parallel(target_size=target_bytes, workers=workers)
        
        except Exception as e:
            print(f"\nError durante descarga: {e}")
        
        # Resumen final
        elapsed = time.time() - start_time
        final_size = self.get_current_size()
        
        print("\n" + "="*70)
        print("RESUMEN FINAL")
        print("="*70)
        print(f"Corpus total:        {final_size / (1024**3):.2f} GB")
        print(f"Documentos:          {self.doc_count}")
        print(f"Tiempo transcurrido: {elapsed / 60:.1f} minutos")
        if elapsed > 0:
            speed = (final_size / (1024**2)) / (elapsed / 60)
            print(f"Velocidad promedio:  {speed:.1f} MB/min")
        print(f"Ubicación:           {self.base_path}")
        print("="*70 + "\n")
        
        self.save_metadata()
        
        if final_size >= target_bytes:
            print("TARGET ALCANZADO\n")
            print("Próximos pasos:")
            print("  1. python test_indexing.py")
            print("  2. cd backend && uvicorn main:app --reload")
            print("  3. cd buscador-frontend && npm install  # primera vez")
            print("  4. npm start")
            print("  5. http://localhost:3000 -> Construir Índice\n")
        else:
            print(f"Tamaño parcial: {final_size / (1024**3):.2f} GB")
            print("Ejecuta nuevamente para continuar.\n")


def show_menu():
    """Muestra menú."""
    print("\n" + "="*70)
    print("CORPUS CREATOR - PROJECT GUTENBERG")
    print("="*70)
    print("""
Fuente: Project Gutenberg (70,000+ libros)
  • Descarga TXT directa (sin API)
  • 20 workers paralelos
  • Sin rate limits
  • Archivos grandes (100KB-1MB cada uno)
  • 50-100 MB/min (muy rápido)

Tamaños disponibles:
  1. 50 MB      (~30 segundos)
  2. 500 MB     (~5 minutos)
  3. 2 GB       (~20 minutos)      ← RECOMENDADO
  4. 5 GB       (~50 minutos)
  5. 10 GB      (~100 minutos)     ← Requisito PDF
  6. 20 GB      (~200 minutos)
  7. Personalizado

[Tiempos estimados con 20 workers y buena conexión]
""")
    print("="*70)


def main():
    """Función principal."""
    show_menu()
    
    while True:
        try:
            option = input("\nSelecciona opción (1-7): ").strip()
            
            sizes = {
                '1': 0.05,
                '2': 0.5,
                '3': 2.0,
                '4': 5.0,
                '5': 10.0,
                '6': 20.0,
            }
            
            if option in sizes:
                target_gb = sizes[option]
                break
            elif option == '7':
                try:
                    target_gb = float(input("Tamaño en GB: "))
                    if target_gb > 0:
                        break
                except ValueError:
                    print("Numero invalido")
            else:
                print("Opcion invalida")
        
        except KeyboardInterrupt:
            print("\n\nCancelado")
            sys.exit(0)
    
    # Número de workers
    workers = 20
    try:
        workers_input = input(f"\nNúmero de workers (default {workers}, max 30): ").strip()
        if workers_input:
            workers = int(workers_input)
            if workers < 1:
                workers = 20
            elif workers > 30:
                workers = 30
    except ValueError:
        pass
    
    print(f"\nUsando {workers} workers paralelos.")
    print("   Puedes detener con Ctrl+C en cualquier momento.\n")
    
    creator = CorpusCreator()
    creator.create_corpus(target_gb, workers=workers)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelado por usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)