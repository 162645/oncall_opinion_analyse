"""
知识图谱查询模块
"""

from typing import Any, Dict, List, Optional
from .builder import KnowledgeGraph


class GraphQuery:
    """图谱查询器"""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def find_similar_faults(
        self,
        symptoms: List[str],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        根据症状查找相似故障

        Args:
            symptoms: 症状列表
            top_k: 返回数量

        Returns:
            相似故障列表
        """
        if not self.graph._driver:
            return []

        query = """
        MATCH (s:Symptom)
        WHERE any(symptom_name IN $symptoms WHERE s.name CONTAINS symptom_name)
        MATCH (f:Fault)-[:CAUSES]->(s)
        WITH f, count(s) as matched_symptoms
        MATCH (f)-[:CAUSES]->(all_s:Symptom)
        WITH f, matched_symptoms, count(all_s) as total_symptoms
        RETURN f.id as fault_id,
               f.title as title,
               f.category as category,
               matched_symptoms,
               total_symptoms,
               toFloat(matched_symptoms) / total_symptoms as similarity
        ORDER BY similarity DESC
        LIMIT $top_k
        """

        with self.graph._get_session() as session:
            result = session.run(
                query,
                symptoms=symptoms,
                top_k=top_k,
            )
            return [dict(record) for record in result]

    def get_solution_path(
        self,
        fault_id: str,
    ) -> List[Dict[str, Any]]:
        """
        获取解决方案路径

        返回从故障到解决方案的完整路径
        """
        if not self.graph._driver:
            return []

        query = """
        MATCH path = (f:Fault {id: $fault_id})-[:FIXED_BY]->(sol:Solution)
        RETURN [node in nodes(path) | {
            type: labels(node)[0],
            id: node.id,
            properties: properties(node)
        }] as solution_path
        ORDER BY sol.effectiveness DESC
        LIMIT 1
        """

        with self.graph._get_session() as session:
            result = session.run(query, fault_id=fault_id)
            record = result.single()
            if record:
                return record["solution_path"]
            return []

    def analyze_fault_pattern(
        self,
        category: Optional[str] = None,
        time_range_days: int = 30,
    ) -> Dict[str, Any]:
        """
        分析故障模式

        统计:
        - 最常见症状
        - 最有效解决方案
        - 故障趋势
        """
        if not self.graph._driver:
            return {}

        # 最常见症状
        symptom_query = """
        MATCH (f:Fault)-[:CAUSES]->(s:Symptom)
        WHERE $category IS NULL OR f.category = $category
        RETURN s.name as symptom, count(f) as count
        ORDER BY count DESC
        LIMIT 10
        """

        # 最有效解决方案
        solution_query = """
        MATCH (f:Fault)-[r:FIXED_BY]->(sol:Solution)
        WHERE $category IS NULL OR f.category = $category
        RETURN sol.title as solution,
               avg(r.effectiveness) as avg_effectiveness,
               count(f) as usage_count
        ORDER BY avg_effectiveness DESC, usage_count DESC
        LIMIT 10
        """

        results = {}

        with self.graph._get_session() as session:
            # 症状统计
            symptom_result = session.run(
                symptom_query,
                category=category,
            )
            results["top_symptoms"] = [dict(r) for r in symptom_result]

            # 解决方案统计
            solution_result = session.run(
                solution_query,
                category=category,
            )
            results["top_solutions"] = [dict(r) for r in solution_result]

        return results

    def get_fault_impact(
        self,
        fault_id: str,
    ) -> Dict[str, Any]:
        """
        获取故障影响范围

        分析:
        - 影响的服务
        - 影响的区域
        - 关联的告警
        """
        if not self.graph._driver:
            return {}

        query = """
        MATCH (f:Fault {id: $fault_id})
        OPTIONAL MATCH (f)-[:AFFECTS]->(svc:Service)
        OPTIONAL MATCH (f)-[:LOCATED_IN]->(reg:Region)
        OPTIONAL MATCH (f)-[:CAUSES]->(s:Symptom)
        RETURN f as fault,
               collect(DISTINCT svc) as affected_services,
               collect(DISTINCT reg) as affected_regions,
               count(DISTINCT s) as symptom_count
        """

        with self.graph._get_session() as session:
            result = session.run(query, fault_id=fault_id)
            record = result.single()

            if not record:
                return {}

            return {
                "fault": dict(record["fault"]),
                "affected_services": [dict(s) for s in record["affected_services"] if s],
                "affected_regions": [dict(r) for r in record["affected_regions"] if r],
                "symptom_count": record["symptom_count"],
            }

    def recommend_solution(
        self,
        symptoms: List[str],
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        推荐解决方案

        基于症状匹配和解决方案有效性
        """
        # 找相似故障
        similar_faults = self.find_similar_faults(symptoms, top_k=3)

        if not similar_faults:
            return {
                "recommendation": None,
                "confidence": 0.0,
                "similar_cases": [],
            }

        # 获取最佳解决方案
        best_fault_id = similar_faults[0]["fault_id"]
        solution_path = self.get_solution_path(best_fault_id)

        return {
            "recommendation": solution_path[-1] if solution_path else None,
            "confidence": similar_faults[0]["similarity"],
            "similar_cases": similar_faults,
        }
