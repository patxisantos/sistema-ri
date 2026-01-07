import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState(null);
  
  // Estados para paginación y top_k
  const [topK, setTopK] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);
  const resultsPerPage = 10;
  
  // Estado para métricas de evaluación
  const [metrics, setMetrics] = useState(null);
  const [loadingMetrics, setLoadingMetrics] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);

  // Cargar estadísticas del índice al iniciar
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/index/stats');
        const data = await response.json();
        if (data.status === 'success') {
          setStats(data);
        }
      } catch (err) {
        console.error('Error fetching stats:', err);
      }
    };
    
    fetchStats();
  }, []);

  // Función de búsqueda usando GET como especifica el PDF
  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError('Por favor, ingresa una búsqueda');
      return;
    }
    
    setLoading(true);
    setError('');
    setResults([]);
    setCurrentPage(1);
    
    try {
      // GET request como especifica el PDF: /search?query=...
      const response = await fetch(
        `http://localhost:8000/search?query=${encodeURIComponent(query)}&top_k=${topK}`
      );
      
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.status === 'success') {
        if (data.results.length === 0) {
          setError('No se encontraron resultados');
        } else {
          setResults(data.results);
        }
      } else {
        setError(data.message || data.detail || 'Error en la búsqueda');
      }
    } catch (err) {
      setError(`Error conectando con el servidor: ${err.message}`);
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Función para cargar métricas de evaluación
  const handleLoadMetrics = async () => {
    setLoadingMetrics(true);
    try {
      const response = await fetch('http://localhost:8000/api/evaluate');
      const data = await response.json();
      if (data.status === 'success') {
        setMetrics(data.metrics);
        setShowMetrics(true);
      }
    } catch (err) {
      console.error('Error fetching metrics:', err);
      setError('Error cargando métricas de evaluación');
    } finally {
      setLoadingMetrics(false);
    }
  };

  // Función para resaltar términos en el snippet
  const highlightTerms = (text, terms) => {
    if (!text || !terms || terms.length === 0) return text;
    
    const queryWords = query.toLowerCase().split(/\s+/).filter(w => w.length > 2);
    if (queryWords.length === 0) return text;
    
    const regex = new RegExp(`(${queryWords.join('|')})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, i) => 
      queryWords.some(term => part.toLowerCase().includes(term.toLowerCase())) 
        ? <mark key={i} className="highlight">{part}</mark>
        : part
    );
  };

  // Paginación
  const totalPages = Math.ceil(results.length / resultsPerPage);
  const startIndex = (currentPage - 1) * resultsPerPage;
  const currentResults = results.slice(startIndex, startIndex + resultsPerPage);

  const goToPage = (page) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="App">
      {/* HEADER */}
      <header className="header">
        <div className="header-content">
          <h1>Buscador de Documentos</h1>
          <p>Motor de Recuperación de Información - Práctica Final</p>
          
          {/* Estadísticas en header */}
          {stats && (
            <div className="header-stats">
              <div className="stat-item">
                <span className="stat-label">Documentos:</span>
                <span className="stat-value">{stats.documents_count.toLocaleString()}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Vocabulario:</span>
                <span className="stat-value">{stats.vocabulary_size.toLocaleString()}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Índice:</span>
                <span className="stat-value">{(stats.corpus_size_gb || 0).toFixed(1)}GB</span>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="container">
        {/* SEARCH FORM */}
        <section className="search-section">
          <form onSubmit={handleSearch} className="search-form">
            <div className="search-input-group">
              <input
                type="text"
                placeholder="Escribe tu búsqueda..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="search-input"
                disabled={loading}
              />
              <button 
                type="submit" 
                className="search-button"
                disabled={loading}
              >
                {loading ? 'Buscando...' : 'Buscar'}
              </button>
            </div>

            {/* Selector de cantidad de resultados */}
            <div className="search-options">
              <label className="option-label">
                <span>Resultados:</span>
                <select 
                  value={topK} 
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="select-topk"
                  disabled={loading}
                >
                  <option value={5}>Top 5</option>
                  <option value={10}>Top 10</option>
                  <option value={20}>Top 20</option>
                  <option value={50}>Top 50</option>
                </select>
              </label>
            </div>

            {/* EXAMPLE QUERIES */}
            <div className="example-queries">
              <p>EJEMPLOS:</p>
              <div className="query-buttons">
                <button 
                  type="button"
                  onClick={() => {
                    setQuery('love and marriage');
                    setTimeout(() => document.querySelector('.search-button').click(), 0);
                  }}
                  disabled={loading}
                >
                  love and marriage
                </button>
                <button 
                  type="button"
                  onClick={() => {
                    setQuery('freedom justice');
                    setTimeout(() => document.querySelector('.search-button').click(), 0);
                  }}
                  disabled={loading}
                >
                  freedom justice
                </button>
                <button 
                  type="button"
                  onClick={() => {
                    setQuery('science discovery');
                    setTimeout(() => document.querySelector('.search-button').click(), 0);
                  }}
                  disabled={loading}
                >
                  science discovery
                </button>
              </div>
            </div>
          </form>
        </section>

        {/* SECCIÓN DE MÉTRICAS DE EVALUACIÓN */}
        <section className="metrics-section">
          <div className="metrics-header">
            <h3>EVALUACIÓN DEL SISTEMA</h3>
            <button 
              onClick={handleLoadMetrics}
              className="metrics-button"
              disabled={loadingMetrics}
            >
              {loadingMetrics ? 'Calculando...' : (metrics ? 'Actualizar Métricas' : 'Calcular Métricas')}
            </button>
          </div>
          
          {showMetrics && metrics && (
            <div className="metrics-grid">
              <div className="metric-card">
                <span className="metric-label">MAP</span>
                <span className="metric-value">{(metrics.MAP * 100).toFixed(2)}%</span>
                <span className="metric-desc">Mean Average Precision</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">MRR</span>
                <span className="metric-value">{(metrics.MRR * 100).toFixed(2)}%</span>
                <span className="metric-desc">Mean Reciprocal Rank</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">P@5</span>
                <span className="metric-value">{(metrics['Mean_P@5'] * 100).toFixed(1)}%</span>
                <span className="metric-desc">Precision at 5</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">P@10</span>
                <span className="metric-value">{(metrics['Mean_P@10'] * 100).toFixed(1)}%</span>
                <span className="metric-desc">Precision at 10</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">R@10</span>
                <span className="metric-value">{(metrics['Mean_R@10'] * 100).toFixed(1)}%</span>
                <span className="metric-desc">Recall at 10</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">R@20</span>
                <span className="metric-value">{(metrics['Mean_R@20'] * 100).toFixed(1)}%</span>
                <span className="metric-desc">Recall at 20</span>
              </div>
            </div>
          )}
        </section>

        {/* ERROR MESSAGE */}
        {error && (
          <div className={`error-message ${error.includes('exitosamente') ? 'success' : ''}`}>
            {error}
          </div>
        )}

        {/* LOADING INDICATOR */}
        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Buscando documentos...</p>
          </div>
        )}

        {/* RESULTS */}
        {results.length > 0 && (
          <section className="results-section">
            <div className="results-header">
              <h2>RESULTADOS ({results.length})</h2>
              {totalPages > 1 && (
                <span className="page-info">
                  Página {currentPage} de {totalPages}
                </span>
              )}
            </div>
            
            <div className="results-list">
              {currentResults.map((result, index) => (
                <article key={index} className="result-card">
                  <div className="result-header">
                    <h3>
                      {startIndex + index + 1}. {result.title || `Documento ${result.doc_id}`}
                    </h3>
                    <span className={`score ${result.score >= 50 ? 'high' : ''}`}>
                      {result.score !== undefined && result.score !== null 
                        ? `${result.score.toFixed(2)}%` 
                        : 'N/A'
                      }
                    </span>
                  </div>
                  
                  <div className="result-metadata">
                    {/* Idioma */}
                    {result.language && (
                      <div className="metadata-item">
                        <strong>IDIOMA:</strong>
                        <span>{result.language.toUpperCase()}</span>
                      </div>
                    )}
                    
                    {/* Tokens */}
                    {result.token_count > 0 && (
                      <div className="metadata-item">
                        <strong>TOKENS:</strong>
                        <span>{result.token_count.toLocaleString()}</span>
                      </div>
                    )}
                    
                    {/* Términos coincidentes */}
                    {result.matching_terms_count > 0 && (
                      <div className="metadata-item">
                        <strong>COINCIDENCIAS:</strong>
                        <span>{result.matching_terms_count} término(s)</span>
                      </div>
                    )}
                    
                    {/* ID */}
                    <div className="metadata-item">
                      <strong>ID:</strong>
                      <span className="doc-id">{result.doc_id}</span>
                    </div>
                  </div>
                  
                  {/* Snippet con highlighting */}
                  {result.snippet && (
                    <p className="snippet">
                      {highlightTerms(result.snippet, result.matching_terms)}
                    </p>
                  )}
                </article>
              ))}
            </div>

            {/* PAGINACIÓN */}
            {totalPages > 1 && (
              <div className="pagination">
                <button 
                  onClick={() => goToPage(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="page-btn"
                >
                  ← Anterior
                </button>
                
                <div className="page-numbers">
                  {[...Array(totalPages)].map((_, i) => (
                    <button
                      key={i}
                      onClick={() => goToPage(i + 1)}
                      className={`page-num ${currentPage === i + 1 ? 'active' : ''}`}
                    >
                      {i + 1}
                    </button>
                  ))}
                </div>
                
                <button 
                  onClick={() => goToPage(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="page-btn"
                >
                  Siguiente →
                </button>
              </div>
            )}
          </section>
        )}

        {/* EMPTY STATE */}
        {!loading && results.length === 0 && !error && (
          <section className="empty-state">
            <div className="empty-illustration"></div>
            <h2>¿Qué buscas?</h2>
            <p>Ingresa términos de búsqueda para encontrar documentos en la colección</p>
          </section>
        )}
      </main>

      {/* FOOTER */}
      <footer className="footer">
        <p>Sistema de Recuperación de Información - Práctica Final</p>
        <p>Backend FastAPI + BM25 | Frontend React</p>
      </footer>
    </div>
  );
}

export default App;
