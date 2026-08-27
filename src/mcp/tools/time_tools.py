"""
时间工具
提供时间相关操作
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from ..base import ToolResult, ToolStatus


class TimeTools:
    """
    时间工具

    提供:
    - current_time: 获取当前时间
    - format_time: 格式化时间
    - parse_time: 解析时间
    - time_diff: 计算时间差
    - convert_timezone: 时区转换
    """

    def __init__(self, default_timezone: str = "Asia/Shanghai"):
        self.default_timezone = default_timezone

    def get_handlers(self) -> Dict[str, Callable]:
        """获取工具处理器"""
        return {
            "time_now": self.current_time,
            "time_format": self.format_time,
            "time_parse": self.parse_time,
            "time_diff": self.time_diff,
            "time_convert": self.convert_timezone,
            "time_sleep": self.time_sleep,
        }

    async def current_time(
        self,
        timezone_name: Optional[str] = None,
        format_str: str = "%Y-%m-%d %H:%M:%S",
    ) -> ToolResult:
        """
        获取当前时间

        Args:
            timezone_name: 时区名称
            format_str: 格式化字符串
        """
        try:
            tz_name = timezone_name or self.default_timezone

            # 获取时区
            try:
                import zoneinfo
                tz = zoneinfo.ZoneInfo(tz_name)
            except Exception:
                # 回退到固定偏移
                tz = timezone(timedelta(hours=8))

            now = datetime.now(tz)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "timestamp": time.time(),
                    "datetime": now.strftime(format_str),
                    "iso": now.isoformat(),
                    "timezone": tz_name,
                    "year": now.year,
                    "month": now.month,
                    "day": now.day,
                    "hour": now.hour,
                    "minute": now.minute,
                    "second": now.second,
                    "weekday": now.strftime("%A"),
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def format_time(
        self,
        timestamp: Optional[float] = None,
        format_str: str = "%Y-%m-%d %H:%M:%S",
        timezone_name: Optional[str] = None,
    ) -> ToolResult:
        """
        格式化时间

        Args:
            timestamp: Unix 时间戳，默认当前时间
            format_str: 格式化字符串
            timezone_name: 时区名称
        """
        try:
            tz_name = timezone_name or self.default_timezone

            try:
                import zoneinfo
                tz = zoneinfo.ZoneInfo(tz_name)
            except Exception:
                tz = timezone(timedelta(hours=8))

            if timestamp is None:
                dt = datetime.now(tz)
            else:
                dt = datetime.fromtimestamp(timestamp, tz=tz)

            formatted = dt.strftime(format_str)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "timestamp": timestamp or time.time(),
                    "formatted": formatted,
                    "format": format_str,
                    "timezone": tz_name,
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def parse_time(
        self,
        time_str: str,
        format_str: Optional[str] = None,
        timezone_name: Optional[str] = None,
    ) -> ToolResult:
        """
        解析时间字符串

        Args:
            time_str: 时间字符串
            format_str: 格式化字符串（可选）
            timezone_name: 时区名称
        """
        try:
            tz_name = timezone_name or self.default_timezone

            # 尝试自动解析
            if format_str:
                dt = datetime.strptime(time_str, format_str)
            else:
                # 尝试多种格式
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d",
                    "%d/%m/%Y",
                    "%m/%d/%Y",
                ]

                dt = None
                for fmt in formats:
                    try:
                        dt = datetime.strptime(time_str, fmt)
                        break
                    except ValueError:
                        continue

                if dt is None:
                    # 尝试 ISO 格式
                    try:
                        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass

                if dt is None:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"Failed to parse time: {time_str}",
                    )

            # 添加时区
            if dt.tzinfo is None:
                try:
                    import zoneinfo
                    tz = zoneinfo.ZoneInfo(tz_name)
                    dt = dt.replace(tzinfo=tz)
                except Exception:
                    dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))

            timestamp = dt.timestamp()

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "original": time_str,
                    "timestamp": timestamp,
                    "iso": dt.isoformat(),
                    "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "timezone": tz_name,
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def time_diff(
        self,
        start: str,
        end: Optional[str] = None,
        unit: str = "seconds",  # seconds, minutes, hours, days
    ) -> ToolResult:
        """
        计算时间差

        Args:
            start: 开始时间
            end: 结束时间（默认当前时间）
            unit: 返回单位
        """
        try:
            # 解析开始时间
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))

            # 解析结束时间
            if end:
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            else:
                end_dt = datetime.now(timezone.utc)

            # 计算差值
            diff = end_dt - start_dt
            total_seconds = diff.total_seconds()

            # 转换单位
            if unit == "seconds":
                value = total_seconds
            elif unit == "minutes":
                value = total_seconds / 60
            elif unit == "hours":
                value = total_seconds / 3600
            elif unit == "days":
                value = total_seconds / 86400
            else:
                value = total_seconds

            # 格式化输出
            days = int(total_seconds // 86400)
            hours = int((total_seconds % 86400) // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "diff_seconds": total_seconds,
                    "diff": {
                        "days": days,
                        "hours": hours,
                        "minutes": minutes,
                        "seconds": seconds,
                    },
                    "value": value,
                    "unit": unit,
                    "human_readable": f"{days}d {hours}h {minutes}m {seconds}s",
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def convert_timezone(
        self,
        time_str: str,
        from_tz: str,
        to_tz: str,
    ) -> ToolResult:
        """
        时区转换

        Args:
            time_str: 时间字符串
            from_tz: 源时区
            to_tz: 目标时区
        """
        try:
            import zoneinfo

            # 解析时间
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))

            # 添加源时区
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=zoneinfo.ZoneInfo(from_tz))

            # 转换时区
            target_tz = zoneinfo.ZoneInfo(to_tz)
            converted = dt.astimezone(target_tz)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "original": time_str,
                    "original_timezone": from_tz,
                    "converted": converted.isoformat(),
                    "converted_timezone": to_tz,
                    "converted_formatted": converted.strftime("%Y-%m-%d %H:%M:%S"),
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def time_sleep(self, seconds: float) -> ToolResult:
        """
        休眠

        Args:
            seconds: 休眠秒数
        """
        try:
            import asyncio
            await asyncio.sleep(seconds)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "slept": seconds,
                    "completed_at": time.time(),
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )
