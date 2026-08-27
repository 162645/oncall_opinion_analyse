"""
云平台工具插件
"""

from ..base import BaseTool, ToolMetadata, ToolResult, ToolCategory


class AWSDescribeInstancesTool(BaseTool):
    """AWS EC2 实例查询工具"""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="aws_describe_instances",
            description="查询 AWS EC2 实例信息",
            category=ToolCategory.CLOUD,
            parameters={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "AWS 区域",
                    },
                    "instance_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "实例ID列表",
                    },
                },
                "required": [],
            },
            tags=["cloud", "aws", "ec2"],
        )

    async def execute(
        self,
        region: str = "us-east-1",
        instance_ids: list = None,
        **kwargs,
    ) -> ToolResult:
        return ToolResult(
            success=True,
            data={
                "region": region,
                "instances": [
                    {
                        "instance_id": "i-1234567890",
                        "state": "running",
                        "instance_type": "t2.micro",
                    }
                ],
            },
        )


class CloudMetricsTool(BaseTool):
    """云平台指标查询工具"""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="query_cloud_metrics",
            description="查询云平台监控指标 (AWS CloudWatch / 飞书云监控)",
            category=ToolCategory.CLOUD,
            parameters={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "服务名称",
                    },
                    "metric_name": {
                        "type": "string",
                        "description": "指标名称",
                    },
                    "namespace": {
                        "type": "string",
                        "description": "命名空间",
                    },
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                },
                "required": ["service", "metric_name"],
            },
            tags=["cloud", "metrics", "monitoring"],
        )

    async def execute(
        self,
        service: str,
        metric_name: str,
        namespace: str = "",
        start_time: str = "",
        end_time: str = "",
        **kwargs,
    ) -> ToolResult:
        return ToolResult(
            success=True,
            data={
                "service": service,
                "metric_name": metric_name,
                "datapoints": [
                    {
                        "timestamp": start_time,
                        "value": 50.0,
                        "unit": "Percent",
                    }
                ],
            },
        )
