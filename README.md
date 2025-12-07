# Trace Test App

Simple Python application that generates OpenTelemetry traces and sends them to a local collector via HTTP. Also generates structured JSON logs that can be collected by Grafana Alloy and sent to Loki.

## Requirements

- Python 3.7+
- OpenTelemetry collector or compatible backend running on `127.0.0.1:4318`

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python app.py
```

The app will:
- Generate 5 traces with nested spans
- Send traces to `http://127.0.0.1:4318/v1/traces` via HTTP
- Each trace includes multiple operations (validation, storage)
- Add random attributes to simulate real-world scenarios

## Output

The application outputs structured JSON logs to stdout. Example log entries:

```json
{"asctime": "2025-12-03 10:15:23,456", "name": "root", "levelname": "INFO", "message": "Starting metrics-demo application", "service": "trace-test-app", "version": "1.0.0"}
{"asctime": "2025-12-03 10:15:23,457", "name": "root", "levelname": "INFO", "message": "Processing item in main operation", "component": "trace_worker", "iteration": 1, "trace_id": "a1b2c3d4e5f6...", "span_id": "1234567890abcdef"}
{"asctime": "2025-12-03 10:15:23,500", "name": "root", "levelname": "INFO", "message": "Data processing completed successfully", "item_id": 1, "operation": "process_data", "processing_status": "completed", "duration_seconds": 0.345}
```

## Configuration

To change the collector endpoint, modify the `endpoint` parameter in `app.py`:

```python
otlp_exporter = OTLPSpanExporter(
    endpoint="http://your-collector:4318/v1/traces",
)
```

## Testing with OpenTelemetry Collector

To test with a local collector, you can use Docker:

```bash
docker run -p 4318:4318 -p 4317:4317 \
  otel/opentelemetry-collector:latest
```

## JSON Logs with Grafana Alloy and Loki

The application outputs structured JSON logs that can be collected by Grafana Alloy and sent to Loki for observability.

### Log Structure

Each log entry includes:
- `timestamp`: ISO formatted timestamp
- `level`: Log level (INFO, DEBUG, ERROR, etc.)
- `message`: Human-readable message
- `component`: Application component (e.g., trace_worker, metrics_updater)
- `operation`: Specific operation being performed
- `trace_id` and `span_id`: OpenTelemetry correlation IDs
- Additional contextual fields (item_id, user_id, error_type, etc.)

### Alloy Configuration

A sample Alloy configuration is provided in `alloy-logs-config.alloy`. This configuration:

1. Discovers Kubernetes pods with the `app=trace-test` label
2. Collects logs from stdout
3. Parses JSON log entries
4. Extracts structured fields as Loki labels
5. Forwards logs to Loki

To use this configuration:

```bash
# Deploy Alloy with this configuration
kubectl apply -f alloy-logs-config.alloy
```

Key features of the Alloy configuration:
- Automatic JSON parsing
- Extracts important fields as labels (level, component, operation)
- Includes trace_id and span_id for correlation with traces
- Adds external labels for multi-cluster deployments

### Querying Logs in Loki

Example LogQL queries:

```logql
# All logs from trace-test-app
{job="trace-test-app"}

# Only error logs
{job="trace-test-app"} |= `"level":"error"`

# Logs for a specific trace
{job="trace-test-app"} | json | trace_id="a1b2c3d4e5f6..."

# Logs from trace_worker component
{job="trace-test-app"} | json | component="trace_worker"

# Processing errors
{job="trace-test-app"} | json | error_type="validation_error"
```

### Log Level Configuration

By default, the application logs at INFO level. To enable DEBUG logs for more detailed information, modify `app.py`:

```python
logger.setLevel(logging.DEBUG)
```
