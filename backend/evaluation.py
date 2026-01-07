import json
from pathlib import Path


# Conjunto de consultas de prueba con documentos relevantes conocidos
# Basado en búsquedas manuales y verificación de títulos
EVALUATION_QUERIES = [
    {
        "query": "love marriage",
        "description": "Documentos sobre amor y matrimonio",
        "relevant_keywords": ["love", "marriage", "conjugial", "married", "wedding", "wife", "husband"],
        "min_expected": 5
    },
    {
        "query": "war battle military",
        "description": "Documentos sobre guerra y batallas",
        "relevant_keywords": ["war", "battle", "military", "army", "soldier", "combat", "troops"],
        "min_expected": 5
    },
    {
        "query": "science discovery",
        "description": "Documentos sobre ciencia y descubrimientos",
        "relevant_keywords": ["science", "discovery", "scientific", "research", "experiment"],
        "min_expected": 3
    },
    {
        "query": "robot artificial intelligence",
        "description": "Documentos sobre robots e IA",
        "relevant_keywords": ["robot", "artificial", "intelligence", "machine", "automaton"],
        "min_expected": 2
    },
    {
        "query": "democracy freedom liberty",
        "description": "Documentos sobre democracia y libertad",
        "relevant_keywords": ["democracy", "freedom", "liberty", "rights", "citizen", "vote"],
        "min_expected": 3
    }
]


def is_relevant(result, query_info):
    """
    Determina si un resultado es relevante basandose en keywords.
    
    Esta es una heuristica simple - en un sistema real usariamos
    juicios de relevancia humanos (qrels).
    """
    title = result.get('title', '').lower()
    snippet = result.get('snippet', '').lower()
    
    text = title + ' ' + snippet
    
    # Contar cuantos keywords relevantes aparecen
    matches = sum(1 for kw in query_info['relevant_keywords'] if kw in text)
    
    # Considerar relevante si al menos 2 keywords aparecen
    return matches >= 2


def precision_at_k(results, query_info, k):
    """
    Calcula Precision@k.
    
    Precision@k = (Documentos relevantes en top-k) / k
    """
    if k == 0:
        return 0.0
    
    top_k = results[:k]
    relevant_count = sum(1 for r in top_k if is_relevant(r, query_info))
    
    return relevant_count / k


def recall_at_k(results, query_info, k, total_relevant=None):
    """
    Calcula Recall@k.
    
    Recall@k = (Documentos relevantes en top-k) / (Total documentos relevantes)
    """
    if total_relevant is None:
        total_relevant = query_info.get('min_expected', 5)
    
    if total_relevant == 0:
        return 0.0
    
    top_k = results[:k]
    relevant_count = sum(1 for r in top_k if is_relevant(r, query_info))
    
    return min(1.0, relevant_count / total_relevant)


def average_precision(results, query_info):
    """
    Calcula Average Precision (AP) para una consulta.
    
    AP = sum(P@k * rel(k)) / total_relevant
    """
    relevant_count = 0
    precision_sum = 0.0
    
    for i, result in enumerate(results):
        if is_relevant(result, query_info):
            relevant_count += 1
            precision_sum += relevant_count / (i + 1)
    
    if relevant_count == 0:
        return 0.0
    
    return precision_sum / relevant_count


def reciprocal_rank(results, query_info):
    """
    Calcula Reciprocal Rank (RR).
    
    RR = 1 / posicion_primer_relevante
    """
    for i, result in enumerate(results):
        if is_relevant(result, query_info):
            return 1.0 / (i + 1)
    
    return 0.0


def evaluate_search_engine(search_engine, k_values=[5, 10, 20]):
    """
    Evalúa el motor de búsqueda con las consultas de prueba.
    
    Returns:
        dict con métricas agregadas
    """
    print("\n" + "="*70)
    print("EVALUACIÓN DEL SISTEMA DE RECUPERACIÓN DE INFORMACIÓN")
    print("="*70)
    
    all_precisions = {k: [] for k in k_values}
    all_recalls = {k: [] for k in k_values}
    all_aps = []
    all_rrs = []
    
    for query_info in EVALUATION_QUERIES:
        query = query_info['query']
        print(f"\nConsulta: '{query}'")
        print(f"  Descripción: {query_info['description']}")
        
        # Ejecutar búsqueda
        results = search_engine.search(query, top_k=max(k_values))
        
        if not results:
            print("  Sin resultados")
            continue
        
        # Calcular métricas para cada k
        for k in k_values:
            p_at_k = precision_at_k(results, query_info, k)
            r_at_k = recall_at_k(results, query_info, k)
            all_precisions[k].append(p_at_k)
            all_recalls[k].append(r_at_k)
            print(f"  P@{k}: {p_at_k:.3f}, R@{k}: {r_at_k:.3f}")
        
        # AP y RR
        ap = average_precision(results, query_info)
        rr = reciprocal_rank(results, query_info)
        all_aps.append(ap)
        all_rrs.append(rr)
        print(f"  AP: {ap:.3f}, RR: {rr:.3f}")
    
    # Calcular promedios
    print("\n" + "-"*70)
    print("MÉTRICAS AGREGADAS:")
    print("-"*70)
    
    metrics = {}
    
    for k in k_values:
        if all_precisions[k]:
            mean_p = sum(all_precisions[k]) / len(all_precisions[k])
            mean_r = sum(all_recalls[k]) / len(all_recalls[k])
            metrics[f'Mean_P@{k}'] = mean_p
            metrics[f'Mean_R@{k}'] = mean_r
            print(f"  Mean P@{k}: {mean_p:.3f}")
            print(f"  Mean R@{k}: {mean_r:.3f}")
    
    if all_aps:
        map_score = sum(all_aps) / len(all_aps)
        metrics['MAP'] = map_score
        print(f"\n  MAP (Mean Average Precision): {map_score:.3f}")
    
    if all_rrs:
        mrr = sum(all_rrs) / len(all_rrs)
        metrics['MRR'] = mrr
        print(f"  MRR (Mean Reciprocal Rank): {mrr:.3f}")
    
    print("\n" + "="*70)
    
    return metrics


def generate_evaluation_report(metrics, output_path=None):
    """
    Genera un informe de evaluacion en formato texto.
    """
    report = []
    report.append("="*60)
    report.append("INFORME DE EVALUACIÓN - SISTEMA RI")
    report.append("="*60)
    report.append("")
    report.append("MÉTRICAS DE EVALUACIÓN:")
    report.append("-"*40)
    
    for metric, value in sorted(metrics.items()):
        report.append(f"  {metric}: {value:.4f}")
    
    report.append("")
    report.append("INTERPRETACION:")
    report.append("-"*40)
    
    map_score = metrics.get('MAP', 0)
    if map_score >= 0.5:
        report.append("  MAP >= 0.5: Rendimiento EXCELENTE")
    elif map_score >= 0.3:
        report.append("  MAP >= 0.3: Rendimiento BUENO")
    elif map_score >= 0.2:
        report.append("  MAP >= 0.2: Rendimiento ACEPTABLE")
    else:
        report.append("  MAP < 0.2: Rendimiento MEJORABLE")
    
    report.append("")
    report.append("="*60)
    
    report_text = "\n".join(report)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"Informe guardado en: {output_path}")
    
    return report_text


def evaluate_single_query(results, query, k_values=[5, 10, 20]):
    """
    Evalúa métricas para una consulta individual basándose en los resultados.
    
    Usa heurísticas basadas en:
    - Score BM25 del resultado
    - Número de términos coincidentes
    - Posición en el ranking
    
    Args:
        results: Lista de resultados de búsqueda
        query: La consulta original
        k_values: Valores de k para P@k y R@k
    
    Returns:
        dict con métricas calculadas para esta consulta
    """
    if not results:
        return {
            "precision": {f"P@{k}": 0.0 for k in k_values},
            "recall": {f"R@{k}": 0.0 for k in k_values},
            "average_precision": 0.0,
            "reciprocal_rank": 0.0,
            "relevant_found": 0,
            "total_results": 0,
            "relevance_details": []
        }
    
    # Determinar relevancia usando score y términos coincidentes
    # Un documento es "relevante" si tiene score > umbral Y coincide con suficientes términos
    query_terms = query.lower().split()
    num_query_terms = len(query_terms)
    
    relevance_details = []
    
    for i, result in enumerate(results):
        score = result.get('score', 0)
        matching_terms = result.get('matching_terms_count', 0)
        
        # Heurística de relevancia:
        # - Score alto (>30) con al menos 1 término = muy relevante
        # - Score medio (15-30) con términos = relevante
        # - Score bajo (<15) = probablemente no relevante
        
        if num_query_terms == 1:
            # Para consultas de 1 término, basarse principalmente en score
            is_relevant = score >= 15
            relevance_score = min(1.0, score / 50)
        else:
            # Para consultas multi-término
            term_ratio = matching_terms / max(1, num_query_terms)
            score_factor = min(1.0, score / 40)
            
            # Combinar factores
            combined = (term_ratio * 0.4) + (score_factor * 0.6)
            is_relevant = combined >= 0.35
            relevance_score = combined
        
        relevance_details.append({
            "position": i + 1,
            "doc_id": result.get('doc_id', ''),
            "title": result.get('title', '')[:50],
            "score": score,
            "matching_terms": matching_terms,
            "is_relevant": is_relevant,
            "relevance_score": round(relevance_score, 3)
        })
    
    # Calcular métricas basadas en relevancia determinada
    relevant_docs = [r for r in relevance_details if r['is_relevant']]
    total_relevant = max(len(relevant_docs), 1)  # Evitar división por 0
    
    # Precision@k y Recall@k
    precision_at_k = {}
    recall_at_k = {}
    
    for k in k_values:
        top_k = relevance_details[:k]
        relevant_in_k = sum(1 for r in top_k if r['is_relevant'])
        
        precision_at_k[f"P@{k}"] = round(relevant_in_k / k, 4) if k > 0 else 0
        recall_at_k[f"R@{k}"] = round(relevant_in_k / total_relevant, 4)
    
    # Average Precision
    relevant_count = 0
    precision_sum = 0.0
    
    for i, detail in enumerate(relevance_details):
        if detail['is_relevant']:
            relevant_count += 1
            precision_sum += relevant_count / (i + 1)
    
    ap = round(precision_sum / relevant_count, 4) if relevant_count > 0 else 0.0
    
    # Reciprocal Rank
    rr = 0.0
    for i, detail in enumerate(relevance_details):
        if detail['is_relevant']:
            rr = round(1.0 / (i + 1), 4)
            break
    
    return {
        "precision": precision_at_k,
        "recall": recall_at_k,
        "average_precision": ap,
        "reciprocal_rank": rr,
        "relevant_found": len(relevant_docs),
        "total_results": len(results),
        "relevance_details": relevance_details[:10]  # Solo top 10 para no saturar
    }


if __name__ == "__main__":
    # Ejemplo de uso standalone
    print("Este modulo debe importarse desde main.py o usarse con el SearchEngine.")
    print("Consultas de evaluacion disponibles:")
    for q in EVALUATION_QUERIES:
        print(f"  - {q['query']}: {q['description']}")
