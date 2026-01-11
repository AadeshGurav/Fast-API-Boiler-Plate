# Logger Usage Guide

## Overview

This FastAPI application uses an advanced logging system that provides structured JSON logging, async file writes, request tracing, and comprehensive observability features.

## Features

### 1. Structured JSON Logging
- **NDJSON format** for easy ingestion into ELK stack, Datadog, or other log management systems
- **Standardized fields**: timestamp, hostname, service, level, logger_name, request_id
- **Custom fields**: Add any additional context via `extra` parameter

### 2. Async File Logging
- **Non-blocking writes** using `asyncio.Queue` and background tasks
- **Level-specific files**: Separate files for DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Automatic rotation** with configurable size limits and backup retention
- **Sync fallback** for CLI tools and non-async contexts

### 3. Request Tracing
- **Request ID propagation** via `contextvars` throughout the request lifecycle
- **Trace ID correlation** with OpenTelemetry tracing when enabled
- **Automatic context** attached to all log entries within a request

### 4. Sampling
- **Configurable sampling** for DEBUG/INFO levels to reduce log volume
- **Always logs errors** and higher severity messages regardless of sampling
- **Performance optimization** without losing critical information

## Configuration

### Logger Configuration File
Located at `config.d/app-logs-config-global.json`:

```json
{
  "logs_path": "logs",
  "log_level": 10,
  "log_formatter_text": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  "log_max_bytes": 5242880,
  "log_backup_count": 3,
  "log_sample_rate": 1.0,
  "log_console_formatter_text": "%(levelname)s | %(asctime)s | %(name)s:%(lineno)d | %(message)s",
  "log_file_formatter_text": "%(message)s",
  "log_enable_request_id_propagation": true,
  "log_enable_trace_correlation": true,
  "log_request_id_header": "X-Request-ID"
}
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `logs_path` | string | "logs" | Directory for log files |
| `log_level` | int | 10 (DEBUG) | Minimum log level (10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR, 50=CRITICAL) |
| `log_max_bytes` | int | 5242880 | Maximum file size before rotation (5MB) |
| `log_backup_count` | int | 3 | Number of rotated files to retain |
| `log_sample_rate` | float | 1.0 | Sampling probability for DEBUG/INFO (0.0-1.0) |
| `log_console_formatter_text` | string | "%(levelname)s \| %(asctime)s \| %(name)s:%(lineno)d \| %(message)s" | Console log format |
| `log_file_formatter_text` | string | "%(message)s" | File log format (JSON) |
| `log_enable_request_id_propagation` | bool | true | Enable request ID propagation via contextvars |
| `log_enable_trace_correlation` | bool | true | Enable trace ID correlation with OpenTelemetry |
| `log_request_id_header` | string | "X-Request-ID" | HTTP header name for request ID |

## Usage Examples

### Basic Logging

```python
from app.services.logger import Logger

logger = Logger()

# Simple logging
logger.info("User logged in")
logger.error("Database connection failed")
logger.debug("Processing request data")

# With exception info
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed", exc_info=e)
```

### Structured Logging with Context

```python
from app.services.logger import Logger, create_log_context

logger = Logger()

# Using create_log_context helper
logger.info(
    "User action completed",
    extra=create_log_context(
        user_id="12345",
        username="john_doe",
        action="file_upload",
        resource="document.pdf",
        status_code=200,
        duration=1.23,
    ),
)

# Direct extra dict
logger.warning(
    "Rate limit exceeded",
    extra={
        "user_id": "12345",
        "endpoint": "/api/upload",
        "requests_per_minute": 150,
        "limit": 100,
    },
)
```

### Request Context (Automatic)

Request IDs are automatically propagated via middleware. All logs within a request will include the request ID:

```python
# In any service or route handler
logger.info("Processing user data")  # Automatically includes request_id
logger.error("Validation failed")     # Automatically includes request_id
```

### Trace Correlation (When Enabled)

When OpenTelemetry tracing is enabled, trace IDs are automatically correlated:

```python
# Logs will include both request_id and trace_id
logger.info("Database query executed")  # Includes: request_id, trace_id
```

## Lifecycle Management

### Application Startup
The logger automatically enables async mode during FastAPI startup:

```python
# In app/utils/utils.py lifespan function
logger.enable_async()  # Automatically called
```

### Application Shutdown
The logger gracefully shuts down during application shutdown:

```python
# In app/utils/utils.py lifespan function
await logger.shutdown()  # Automatically called
```

## Log File Structure

### Console Output
Human-readable, color-coded logs:
```
INFO     | 14:30:25 | app.services.auth:45 | User authentication successful
ERROR    | 14:30:26 | app.api.routes:123 | Database connection failed
```

### File Output (JSON)
Structured NDJSON format:
```json
{"timestamp": "2024-01-15T14:30:25.123Z", "hostname": "server-01", "service": "fastapi-app", "level": "INFO", "logger_name": "app.services.auth", "request_id": "req-abc123", "message": "User authentication successful", "user_id": "12345"}
{"timestamp": "2024-01-15T14:30:26.456Z", "hostname": "server-01", "service": "fastapi-app", "level": "ERROR", "logger_name": "app.api.routes", "request_id": "req-abc123", "message": "Database connection failed", "error_code": "CONN_TIMEOUT"}
```

### File Organization
```
logs/
├── debug_log.jsonl      # DEBUG level logs
├── info_log.jsonl       # INFO level logs
├── warning_log.jsonl    # WARNING level logs
├── error_log.jsonl      # ERROR level logs
└── critical_log.jsonl   # CRITICAL level logs
```

## Best Practices

### 1. Use Structured Logging
Always include relevant context in your logs:

```python
# Good
logger.info(
    "Payment processed",
    extra=create_log_context(
        user_id=user.id,
        amount=payment.amount,
        currency=payment.currency,
        payment_method=payment.method,
        transaction_id=payment.id,
    ),
)

# Avoid
logger.info(f"Payment processed for {user.id}")
```

### 2. Consistent Field Names
Use standardized field names across the application:

- `user_id`, `username` - User identification
- `request_id`, `trace_id` - Request/trace correlation
- `action`, `resource` - What was performed and on what
- `method`, `path` - HTTP request details
- `status_code`, `duration` - Response metrics
- `ip`, `user_agent` - Client information

### 3. Appropriate Log Levels
- **DEBUG**: Detailed information for debugging
- **INFO**: General information about application flow
- **WARNING**: Something unexpected happened but application continues
- **ERROR**: Error occurred but application can continue
- **CRITICAL**: Serious error that may cause application to stop

### 4. Exception Handling
Always use `logger.exception()` for caught exceptions:

```python
try:
    risky_operation()
except Exception as e:
    logger.exception(
        "Operation failed",
        extra=create_log_context(
            operation="risky_operation",
            user_id=user.id,
        ),
    )
```

### 5. Performance Considerations
- Use sampling for high-volume DEBUG/INFO logs
- Avoid logging in tight loops without sampling
- Use `create_log_context()` to filter out None values
- Prefer structured logging over string formatting

## Integration with Monitoring

### ELK Stack
The NDJSON format is perfect for Logstash ingestion:

```ruby
# logstash.conf
input {
  file {
    path => "/path/to/logs/*.jsonl"
    codec => "json_lines"
  }
}
```

### Datadog
Configure Datadog to parse JSON logs:

```yaml
# datadog.yaml
logs_config:
  logs_dd_url: https://http-intake.logs.datadoghq.com
  processing_rules:
    - type: exclude_at_match
      name: exclude_health_checks
      pattern: "health"
```

### Grafana Loki
Use JSON parser for structured logs:

```yaml
# promtail.yaml
pipeline_stages:
  - json:
      expressions:
        timestamp: timestamp
        level: level
        message: message
        request_id: request_id
```

## Troubleshooting

### Common Issues

1. **Logs not appearing**: Check log level configuration
2. **Missing request IDs**: Ensure RequestIDMiddleware is enabled
3. **High disk usage**: Adjust `log_max_bytes` and `log_backup_count`
4. **Performance issues**: Enable sampling with `log_sample_rate`

### Debug Mode
Enable debug logging by setting log level to 10:

```json
{
  "log_level": 10
}
```

### Log Rotation
Monitor disk usage and adjust rotation settings:

```json
{
  "log_max_bytes": 10485760,  // 10MB
  "log_backup_count": 5       // Keep 5 rotated files
}
```

## Migration from Standard Logging

If migrating from Python's standard logging:

1. Replace `logging.getLogger()` with `Logger()` instance
2. Use `create_log_context()` for structured logging
3. Remove manual request ID passing (now automatic)
4. Update log format strings to use JSON structure
5. Enable async mode for better performance

## Advanced Features

### Custom Formatters
You can extend the logging system with custom formatters:

```python
from app.services.logger import Logger

class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Custom formatting logic
        return super().format(record)

logger = Logger()
# Add custom formatter to handlers
```

### Sampling Strategies
Implement custom sampling logic:

```python
def should_log_debug(user_id: str) -> bool:
    # Log debug for specific users only
    return user_id in ["admin", "developer"]
```

### Log Aggregation
For distributed systems, ensure consistent log formats across services and use correlation IDs for tracing requests across service boundaries.
