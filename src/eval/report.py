"""
评估报告
生成评估结果报告
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class EvaluationReport:
    """评估报告"""

    # 基本信息
    report_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 评估样本数
    total_samples: int = 0

    # 平均分数
    avg_faithfulness: float = 0.0
    avg_answer_relevancy: float = 0.0
    avg_context_recall: float = 0.0
    avg_context_precision: float = 0.0
    avg_overall: float = 0.0

    # 分数分布
    score_distribution: Dict[str, List[float]] = field(default_factory=dict)

    # 详细结果
    details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
            "total_samples": self.total_samples,
            "averages": {
                "faithfulness": round(self.avg_faithfulness, 3),
                "answer_relevancy": round(self.avg_answer_relevancy, 3),
                "context_recall": round(self.avg_context_recall, 3),
                "context_precision": round(self.avg_context_precision, 3),
                "overall": round(self.avg_overall, 3),
            },
            "score_distribution": self.score_distribution,
            "details": self.details,
        }

    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


def generate_report(
    results: List[Any],
    report_id: Optional[str] = None,
) -> EvaluationReport:
    """
    生成评估报告

    Args:
        results: 评估结果列表
        report_id: 报告 ID

    Returns:
        EvaluationReport
    """
    import uuid

    report = EvaluationReport(
        report_id=report_id or str(uuid.uuid4()),
        total_samples=len(results),
    )

    if not results:
        return report

    # 计算平均分数
    faithfulness_scores = []
    relevancy_scores = []
    recall_scores = []
    precision_scores = []
    overall_scores = []

    for result in results:
        faithfulness_scores.append(result.faithfulness)
        relevancy_scores.append(result.answer_relevancy)
        recall_scores.append(result.context_recall)
        precision_scores.append(result.context_precision)
        overall_scores.append(result.overall_score)

        # 添加详细信息
        report.details.append({
            "query": result.query,
            "scores": {
                "faithfulness": result.faithfulness,
                "answer_relevancy": result.answer_relevancy,
                "context_recall": result.context_recall,
                "context_precision": result.context_precision,
                "overall": result.overall_score,
            },
            "latency_ms": result.latency_ms,
        })

    # 计算平均值
    report.avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores)
    report.avg_answer_relevancy = sum(relevancy_scores) / len(relevancy_scores)
    report.avg_context_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
    report.avg_context_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0.0
    report.avg_overall = sum(overall_scores) / len(overall_scores)

    # 分数分布
    report.score_distribution = {
        "faithfulness": faithfulness_scores,
        "answer_relevancy": relevancy_scores,
        "context_recall": recall_scores,
        "context_precision": precision_scores,
        "overall": overall_scores,
    }

    return report


def generate_markdown_report(report: EvaluationReport) -> str:
    """
    生成 Markdown 格式的报告

    Args:
        report: 评估报告

    Returns:
        Markdown 文本
    """
    md = f"""# RAG 评估报告

**报告 ID**: {report.report_id}
**生成时间**: {report.created_at}
**样本数量**: {report.total_samples}

## 总体评估

| 指标 | 平均分数 |
|------|----------|
| 忠实度 (Faithfulness) | {report.avg_faithfulness:.3f} |
| 答案相关性 (Answer Relevancy) | {report.avg_answer_relevancy:.3f} |
| 上下文召回 (Context Recall) | {report.avg_context_recall:.3f} |
| 上下文精确度 (Context Precision) | {report.avg_context_precision:.3f} |
| **综合分数** | **{report.avg_overall:.3f}** |

## 评估等级

| 分数范围 | 等级 | 描述 |
|----------|------|------|
| 0.8 - 1.0 | 优秀 | 回答质量高，完全满足用户需求 |
| 0.6 - 0.8 | 良好 | 回答质量较好，基本满足用户需求 |
| 0.4 - 0.6 | 一般 | 回答质量一般，部分满足用户需求 |
| 0.0 - 0.4 | 较差 | 回答质量较差，需要改进 |

## 改进建议

"""

    # 根据分数给出建议
    if report.avg_faithfulness < 0.6:
        md += "- **忠实度较低**: 建议改进检索质量，确保检索内容与问题相关\n"

    if report.avg_answer_relevancy < 0.6:
        md += "- **相关性较低**: 建议优化 Prompt，确保回答直接针对问题\n"

    if report.avg_context_recall < 0.6:
        md += "- **召回率较低**: 建议增加检索数量或优化查询扩展\n"

    if report.avg_context_precision < 0.6:
        md += "- **精确度较低**: 建议优化检索排序或添加重排序步骤\n"

    return md
