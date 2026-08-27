"""
知识图谱模块
使用 Neo4j 实现故障关联图谱
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class NodeType(Enum):
    """节点类型"""
    FAULT = "Fault"
    SYMPTOM = "Symptom"
    ROOT_CAUSE = "RootCause"
    SOLUTION = "Solution"
    SERVICE = "Service"
    REGION = "Region"


class RelationType(Enum):
    """关系类型"""
    CAUSES = "CAUSES"          # 故障导致症状
    HAS_ROOT_CAUSE = "HAS_ROOT_CAUSE"  # 故障的根因
    FIXED_BY = "FIXED_BY"      # 解决方案修复
    AFFECTS = "AFFECTS"        # 影响服务
    LOCATED_IN = "LOCATED_IN"  # 位于区域
    RELATED_TO = "RELATED_TO"  # 相关联


@dataclass
class GraphNode:
    """图谱节点"""
    id: str
    type: NodeType
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_cypher(self) -> str:
        """生成 Cypher 创建语句"""
        props = ", ".join(
            f"{k}: '{v}'" if isinstance(v, str) else f"{k}: {v}"
            for k, v in self.properties.items()
        )
        return f"CREATE (:{self.type.value} {{id: '{self.id}', {props}}})"


@dataclass
class GraphEdge:
    """图谱边"""
    source_id: str
    target_id: str
    type: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """
    知识图谱

    存储:
    - 故障节点
    - 症状节点
    - 根因节点
    - 解决方案节点

    关系:
    - Fault -[CAUSES]-> Symptom
    - Fault -[HAS_ROOT_CAUSE]-> RootCause
    - RootCause -[FIXED_BY]-> Solution
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "",
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None

    def connect(self):
        """连接 Neo4j"""
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
        except ImportError:
            raise ImportError("请安装 neo4j: pip install neo4j")

    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()

    def _get_session(self):
        """获取会话"""
        if not self._driver:
            self.connect()
        return self._driver.session()

    def add_fault(
        self,
        fault_id: str,
        title: str,
        category: str,
        description: str = "",
        severity: str = "medium",
    ) -> bool:
        """添加故障节点"""
        query = """
        MERGE (f:Fault {id: $fault_id})
        SET f.title = $title,
            f.category = $category,
            f.description = $description,
            f.severity = $severity,
            f.created_at = datetime()
        RETURN f
        """

        with self._get_session() as session:
            result = session.run(
                query,
                fault_id=fault_id,
                title=title,
                category=category,
                description=description,
                severity=severity,
            )
            return result.single() is not None

    def add_symptom(
        self,
        symptom_id: str,
        name: str,
        description: str = "",
    ) -> bool:
        """添加症状节点"""
        query = """
        MERGE (s:Symptom {id: $symptom_id})
        SET s.name = $name,
            s.description = $description
        RETURN s
        """

        with self._get_session() as session:
            result = session.run(
                query,
                symptom_id=symptom_id,
                name=name,
                description=description,
            )
            return result.single() is not None

    def add_solution(
        self,
        solution_id: str,
        title: str,
        steps: List[str],
        effectiveness: float = 0.0,
    ) -> bool:
        """添加解决方案节点"""
        query = """
        MERGE (sol:Solution {id: $solution_id})
        SET sol.title = $title,
            sol.steps = $steps,
            sol.effectiveness = $effectiveness
        RETURN sol
        """

        with self._get_session() as session:
            result = session.run(
                query,
                solution_id=solution_id,
                title=title,
                steps=steps,
                effectiveness=effectiveness,
            )
            return result.single() is not None

    def link_fault_to_symptom(
        self,
        fault_id: str,
        symptom_id: str,
    ) -> bool:
        """关联故障和症状"""
        query = """
        MATCH (f:Fault {id: $fault_id})
        MATCH (s:Symptom {id: $symptom_id})
        MERGE (f)-[:CAUSES]->(s)
        RETURN f, s
        """

        with self._get_session() as session:
            result = session.run(
                query,
                fault_id=fault_id,
                symptom_id=symptom_id,
            )
            return result.single() is not None

    def link_fault_to_solution(
        self,
        fault_id: str,
        solution_id: str,
        effectiveness: float = 0.0,
    ) -> bool:
        """关联故障和解决方案"""
        query = """
        MATCH (f:Fault {id: $fault_id})
        MATCH (sol:Solution {id: $solution_id})
        MERGE (f)-[:FIXED_BY {effectiveness: $effectiveness}]->(sol)
        RETURN f, sol
        """

        with self._get_session() as session:
            result = session.run(
                query,
                fault_id=fault_id,
                solution_id=solution_id,
                effectiveness=effectiveness,
            )
            return result.single() is not None

    def find_related_faults(
        self,
        fault_id: str,
        max_depth: int = 2,
    ) -> List[Dict[str, Any]]:
        """查找相关故障"""
        query = f"""
        MATCH (f:Fault {{id: $fault_id}})-[:CAUSES]->(s:Symptom)
        MATCH (other:Fault)-[:CAUSES]->(s)
        WHERE other <> f
        RETURN other.id as fault_id,
               other.title as title,
               other.category as category,
               count(s) as shared_symptoms
        ORDER BY shared_symptoms DESC
        LIMIT 10
        """

        with self._get_session() as session:
            result = session.run(query, fault_id=fault_id)
            return [dict(record) for record in result]

    def find_solutions_for_symptom(
        self,
        symptom_name: str,
    ) -> List[Dict[str, Any]]:
        """根据症状查找解决方案"""
        query = """
        MATCH (s:Symptom)
        WHERE s.name CONTAINS $symptom_name
        MATCH (f:Fault)-[:CAUSES]->(s)
        MATCH (f)-[r:FIXED_BY]->(sol:Solution)
        RETURN sol.id as solution_id,
               sol.title as title,
               sol.steps as steps,
               r.effectiveness as effectiveness
        ORDER BY effectiveness DESC
        LIMIT 5
        """

        with self._get_session() as session:
            result = session.run(query, symptom_name=symptom_name)
            return [dict(record) for record in result]

    def get_fault_chain(
        self,
        fault_id: str,
    ) -> Dict[str, Any]:
        """获取故障链（故障-症状-根因-解决方案）"""
        query = """
        MATCH (f:Fault {id: $fault_id})
        OPTIONAL MATCH (f)-[:CAUSES]->(s:Symptom)
        OPTIONAL MATCH (f)-[:FIXED_BY]->(sol:Solution)
        RETURN f as fault,
               collect(DISTINCT s) as symptoms,
               collect(DISTINCT sol) as solutions
        """

        with self._get_session() as session:
            result = session.run(query, fault_id=fault_id)
            record = result.single()

            if not record:
                return {}

            return {
                "fault": dict(record["fault"]),
                "symptoms": [dict(s) for s in record["symptoms"] if s],
                "solutions": [dict(sol) for sol in record["solutions"] if sol],
            }

    def get_statistics(self) -> Dict[str, int]:
        """获取图谱统计"""
        query = """
        MATCH (f:Fault) RETURN count(f) as fault_count
        UNION
        MATCH (s:Symptom) RETURN count(s) as symptom_count
        UNION
        MATCH (sol:Solution) RETURN count(sol) as solution_count
        """

        with self._get_session() as session:
            results = list(session.run(query))
            return {
                "faults": results[0]["fault_count"] if len(results) > 0 else 0,
                "symptoms": results[1]["symptom_count"] if len(results) > 1 else 0,
                "solutions": results[2]["solution_count"] if len(results) > 2 else 0,
            }


class GraphBuilder:
    """图谱构建器"""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def build_from_case(self, case: Dict[str, Any]) -> bool:
        """从案例构建图谱"""
        # 1. 创建故障节点
        fault_id = case.get("id", case.get("ticket_id", ""))
        self.graph.add_fault(
            fault_id=fault_id,
            title=case.get("title", ""),
            category=case.get("category", "unknown"),
            description=case.get("description", ""),
            severity=case.get("severity", "medium"),
        )

        # 2. 创建症状节点并关联
        symptoms = case.get("symptoms", [])
        for i, symptom in enumerate(symptoms):
            symptom_id = f"{fault_id}_symptom_{i}"
            self.graph.add_symptom(
                symptom_id=symptom_id,
                name=symptom.get("name", symptom) if isinstance(symptom, dict) else symptom,
                description=symptom.get("description", "") if isinstance(symptom, dict) else "",
            )
            self.graph.link_fault_to_symptom(fault_id, symptom_id)

        # 3. 创建解决方案节点并关联
        solution = case.get("solution", case.get("resolution", ""))
        if solution:
            solution_id = f"{fault_id}_solution"
            steps = solution if isinstance(solution, list) else [solution]
            self.graph.add_solution(
                solution_id=solution_id,
                title=f"解决方案 for {fault_id}",
                steps=steps,
                effectiveness=case.get("effectiveness", 0.8),
            )
            self.graph.link_fault_to_solution(
                fault_id,
                solution_id,
                case.get("effectiveness", 0.8),
            )

        return True

    def build_from_cases(self, cases: List[Dict[str, Any]]) -> int:
        """批量构建"""
        count = 0
        for case in cases:
            try:
                if self.build_from_case(case):
                    count += 1
            except Exception:
                pass
        return count
