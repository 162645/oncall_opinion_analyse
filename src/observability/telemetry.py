"""OpenTelemetry bootstrap with safe local fallback and metric helpers."""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, SimpleLogRecordProcessor, InMemoryLogRecordExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter


@dataclass(frozen=True)
class TelemetryConfig:
    service_name: str = "oncall-agent-harness"
    service_version: str = "5.0.0"
    environment: str = "local"
    otlp_endpoint: Optional[str] = None
    insecure: bool = True
    enable_log_bridge: bool = False


class Telemetry:
    def __init__(self, config: Optional[TelemetryConfig] = None):
        self.config = config or TelemetryConfig(
            otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        )
        self.memory_exporter: Optional[InMemorySpanExporter] = None
        self.memory_log_exporter: Optional[InMemoryLogRecordExporter] = None
        resource = Resource.create({
            "service.name": self.config.service_name,
            "service.version": self.config.service_version,
            "deployment.environment.name": self.config.environment,
        })
        provider = TracerProvider(resource=resource)
        if self.config.otlp_endpoint:
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
                endpoint=self.config.otlp_endpoint, insecure=self.config.insecure
            )))
        else:
            self.memory_exporter = InMemorySpanExporter()
            provider.add_span_processor(SimpleSpanProcessor(self.memory_exporter))
        self.provider = provider
        self.tracer = provider.get_tracer(self.config.service_name)

        if self.config.otlp_endpoint:
            reader = PeriodicExportingMetricReader(OTLPMetricExporter(
                endpoint=self.config.otlp_endpoint, insecure=self.config.insecure
            ))
            self.meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        else:
            self.meter_provider = MeterProvider(resource=resource)
        self.meter = self.meter_provider.get_meter(self.config.service_name)
        self.run_counter = self.meter.create_counter("agent.runs")
        self.tool_counter = self.meter.create_counter("agent.tool.calls")
        self.latency = self.meter.create_histogram("agent.run.duration", unit="ms")

        self.logger_provider = LoggerProvider(resource=resource)
        if self.config.otlp_endpoint:
            self.logger_provider.add_log_record_processor(BatchLogRecordProcessor(
                OTLPLogExporter(endpoint=self.config.otlp_endpoint, insecure=self.config.insecure)
            ))
        else:
            self.memory_log_exporter = InMemoryLogRecordExporter()
            self.logger_provider.add_log_record_processor(SimpleLogRecordProcessor(self.memory_log_exporter))
        self.logging_handler = LoggingHandler(level=logging.NOTSET, logger_provider=self.logger_provider)
        if self.config.enable_log_bridge:
            logging.getLogger().addHandler(self.logging_handler)

    def finished_spans(self):
        return list(self.memory_exporter.get_finished_spans()) if self.memory_exporter else []

    def finished_logs(self):
        return list(self.memory_log_exporter.get_finished_logs()) if self.memory_log_exporter else []

    def shutdown(self):
        self.provider.shutdown()
        self.meter_provider.shutdown()
        self.logger_provider.shutdown()


_telemetry: Optional[Telemetry] = None


def get_telemetry() -> Telemetry:
    global _telemetry
    if _telemetry is None:
        _telemetry = Telemetry(TelemetryConfig(
            otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            environment=os.getenv("ENVIRONMENT", "local"),
            enable_log_bridge=True,
        ))
    return _telemetry
