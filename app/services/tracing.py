"""OpenTelemetry tracing: SDK setup plus the official instrumentation libraries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.services.base_service import BaseService

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.services.logger import Logger
    from config import Config


class TracingService(BaseService):
    """Exports traces to an OTLP collector (``otlp_endpoint``) and instruments the app."""

    def __init__(self, logger: Logger, config: Config) -> None:
        super().__init__(config, logger)
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": config["app_title"],
                    "service.version": config["app_version"],
                    "deployment.environment": config["environment"],
                }
            ),
            sampler=ParentBased(TraceIdRatioBased(config["tracing_sample_rate"])),
        )
        endpoint = config["otlp_endpoint"]
        if endpoint:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=endpoint, insecure=config["otlp_insecure"])
                )
            )
        else:
            logger.warning("tracing_service is on but otlp_endpoint is not set: spans are dropped")
        self.provider = provider

    def instrument_app(self, app: FastAPI) -> None:
        """Trace incoming requests and outgoing HTTP / Redis / MongoDB calls."""
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=self.provider,
            excluded_urls="/api/v1/health,/api/v1/live,/api/v1/ready",
        )
        HTTPXClientInstrumentor().instrument(tracer_provider=self.provider)
        if self.config["tracing_redis"]:
            from opentelemetry.instrumentation.redis import RedisInstrumentor

            RedisInstrumentor().instrument(tracer_provider=self.provider)
        if self.config["tracing_mongodb"]:
            from opentelemetry.instrumentation.pymongo import PymongoInstrumentor

            PymongoInstrumentor().instrument(tracer_provider=self.provider)

    def get_trace_id(self) -> str | None:
        """Hex trace id of the active span, for correlating logs."""
        context = trace.get_current_span().get_span_context()
        return format(context.trace_id, "032x") if context.is_valid else None

    def shutdown(self) -> None:
        """Flush pending spans."""
        self.provider.shutdown()


__all__ = ["TracingService"]
