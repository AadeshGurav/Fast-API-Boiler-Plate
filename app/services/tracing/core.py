"""Core tracing functionality using OpenTelemetry."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

if TYPE_CHECKING:
    from app.services.logger import Logger
    from config import Config


class TracingCore:
    """Core tracing functionality using OpenTelemetry."""

    def __init__(
        self: TracingCore,
        config: Config,
        logger: Logger,
        *args: dict[str, Any],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize tracing core.

        Args:
        ----
            config: Configuration object.
            logger: Logger instance.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        """
        self.config = config
        self.logger = logger
        self.enabled = config.get("tracing_enabled", True)
        self.service_name = config.get("app_title", "fastapi-app")
        self.environment = config.get("environment", "development")
        self.sample_rate = config.get("tracing_sample_rate", 1.0)
        self.tracer: trace.Tracer | None = None
        self._console_stream = None

        if self.enabled:
            try:
                self._setup_tracing()
            except Exception as e:  # noqa: BLE001
                self.logger.error(f"Failed to setup tracing: {str(e)}")

    def _setup_tracing(self) -> None:
        """Set up OpenTelemetry tracing."""
        self.logger.info("Setting up OpenTelemetry tracing")

        resource = Resource.create(
            {
                "service.name": self.service_name,
                "service.version": self.config.get("app_version", "1.0.0"),
                "deployment.environment": self.environment,
                "host.name": self.config.get("hostname", "unknown"),
            }
        )

        provider = TracerProvider(resource=resource)
        exporters = []

        # OTLP exporter for external backends
        otlp_endpoint = self.config.get("otlp_endpoint")
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                headers=self.config.get("otlp_headers", {}),
                insecure=self.config.get("otlp_insecure", True),
            )
            exporters.append(otlp_exporter)
            self.logger.info(f"OTLP exporter configured: {otlp_endpoint}")

        # Console exporter for debugging
        if self.config.get("tracing_console_export", False):
            # Redirect console exporter to a dedicated file instead of stdout
            try:
                logs_path = self.config.get("logs_path", "logs")
                trace_log_path = self.config.get(
                    "tracing_console_export_path",
                    str(Path(logs_path) / "otel_traces.log"),
                )
                Path(trace_log_path).parent.mkdir(parents=True, exist_ok=True)
                self._console_stream = open(trace_log_path, mode="a", buffering=1)
                exporters.append(ConsoleSpanExporter(out=self._console_stream))
                self.logger.info(
                    "Console exporter redirected to file",
                    extra={"trace_log_path": trace_log_path},
                )
            except Exception as e:  # noqa: BLE001
                self.logger.error(f"Failed to open trace log file: {e}")

        for exporter in exporters:
            provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer(
            __name__, self.config.get("app_version", "1.0.0")
        )

        self.logger.info(
            f"Tracing initialized for service '{self.service_name}'",
            extra={"exporters_count": len(exporters), "sample_rate": self.sample_rate},
        )

    def get_trace_id(self) -> str | None:
        """Get the current trace ID.

        Returns
        -------
            The current trace ID.

        """
        if not self.enabled:
            return None
        current_span = trace.get_current_span()
        if current_span:
            ctx = current_span.get_span_context()
            if ctx and ctx.is_valid:
                return format(ctx.trace_id, "032x")
        return None

    def get_span_id(self) -> str | None:
        """Get the current span ID.

        Returns
        -------
            The current span ID.

        """
        if not self.enabled:
            return None
        current_span = trace.get_current_span()
        if current_span:
            ctx = current_span.get_span_context()
            if ctx and ctx.is_valid:
                return format(ctx.span_id, "016x")
        return None

    def close(self) -> None:
        """Close tracing resources (file streams, etc.)."""
        try:
            if self._console_stream:
                try:
                    self._console_stream.flush()
                except Exception:
                    pass
                self._console_stream.close()
                self._console_stream = None
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Failed to close tracing resources: {e}")


__all__ = ["TracingCore"]
__all__ = ["TracingCore"]
