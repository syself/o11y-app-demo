#!/usr/bin/env python3
"""
Simple Python application that generates OpenTelemetry traces
and sends them to a local collector via HTTP.
Also exposes Prometheus metrics on /metrics endpoint.
"""

import time
import random
import threading
import logging
import sys
import os
from flask import Flask, Response, request
from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from pythonjsonlogger import jsonlogger

# Get Kubernetes node name from environment variable
K8S_NODE_NAME = os.getenv('K8S_NODE_NAME', 'unknown')

# Configure JSON logging
logger = logging.getLogger()
logHandler = logging.StreamHandler(sys.stdout)

# Custom JSON formatter that includes k8s_node_name in all logs
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['k8s_node_name'] = K8S_NODE_NAME

formatter = CustomJsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s',
    timestamp=True
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Configure the tracer provider with service information
resource = Resource(attributes={
    "service.name": "trace-test-app",
    "service.version": "1.0.0"
})

tracer_provider = TracerProvider(resource=resource)

# Configure OTLP HTTP exporter
otlp_exporter = OTLPSpanExporter(
    endpoint="http://alloy.alloy.svc:4318/v1/traces",
)

# Add the span processor to the tracer provider
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

# Set the global tracer provider
trace.set_tracer_provider(tracer_provider)

# Get a tracer
tracer = trace.get_tracer(__name__)

# Create Flask app for metrics endpoint
app = Flask(__name__)

# Define Prometheus metrics
requests_total = Counter(
    'app_requests_total',
    'Total number of requests processed',
    ['method', 'endpoint', 'status']
)

items_processed = Counter(
    'app_items_processed_total',
    'Total number of items processed'
)

active_operations = Gauge(
    'app_active_operations',
    'Number of currently active operations'
)

processing_duration = Histogram(
    'app_processing_duration_seconds',
    'Time spent processing items',
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

request_latency = Summary(
    'app_request_latency_seconds',
    'Request latency in seconds'
)

cpu_usage = Gauge(
    'app_cpu_usage_percent',
    'Simulated CPU usage percentage'
)

memory_usage = Gauge(
    'app_memory_usage_bytes',
    'Simulated memory usage in bytes'
)

error_count = Counter(
    'app_errors_total',
    'Total number of errors',
    ['error_type']
)


@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint."""
    logger.info("Metrics endpoint accessed", extra={
        "endpoint": "/metrics",
        "method": request.method,
        "remote_addr": request.remote_addr
    })
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route('/health')
def health():
    """Health check endpoint."""
    logger.info("Health check endpoint accessed", extra={
        "endpoint": "/health",
        "method": request.method,
        "remote_addr": request.remote_addr,
        "status": "healthy"
    })
    return {'status': 'healthy'}, 200


@app.route('/')
def index():
    """Root endpoint."""
    requests_total.labels(method='GET', endpoint='/', status='200').inc()
    logger.info("Root endpoint accessed", extra={
        "endpoint": "/",
        "method": request.method,
        "remote_addr": request.remote_addr
    })
    return {'message': 'Metrics Demo App', 'metrics_endpoint': '/metrics', 'health_endpoint': '/health'}, 200


def process_data(item_id: int):
    """Simulates processing data with nested spans."""
    start_time = time.time()
    active_operations.inc()

    try:
        with tracer.start_as_current_span("process_data") as span:
            span.set_attribute("item.id", item_id)

            logger.debug("Starting data processing", extra={
                "item_id": item_id,
                "operation": "process_data",
                "trace_id": format(span.get_span_context().trace_id, '032x'),
                "span_id": format(span.get_span_context().span_id, '016x')
            })

            # Simulate some work
            duration = random.uniform(0.1, 0.3)
            time.sleep(duration)

            # Create a child span for validation
            with tracer.start_as_current_span("validate_data") as child_span:
                child_span.set_attribute("validation.result", "success")
                logger.debug("Validating data", extra={
                    "item_id": item_id,
                    "operation": "validate_data",
                    "validation_result": "success"
                })
                time.sleep(random.uniform(0.05, 0.15))

            # Create another child span for storage
            with tracer.start_as_current_span("store_data") as child_span:
                child_span.set_attribute("storage.type", "database")
                logger.debug("Storing data", extra={
                    "item_id": item_id,
                    "operation": "store_data",
                    "storage_type": "database"
                })
                time.sleep(random.uniform(0.05, 0.15))

            # Simulate occasional errors (5% chance)
            if random.random() < 0.05:
                error_count.labels(error_type='validation_error').inc()
                span.set_attribute("processing.status", "error")
                logger.error("Data processing failed", extra={
                    "item_id": item_id,
                    "operation": "process_data",
                    "error_type": "validation_error",
                    "processing_status": "error",
                    "trace_id": format(span.get_span_context().trace_id, '032x')
                })
            else:
                span.set_attribute("processing.status", "completed")
                items_processed.inc()
                logger.info("Data processing completed successfully", extra={
                    "item_id": item_id,
                    "operation": "process_data",
                    "processing_status": "completed",
                    "duration_seconds": time.time() - start_time
                })
    finally:
        active_operations.dec()
        processing_duration.observe(time.time() - start_time)
        request_latency.observe(time.time() - start_time)


def update_simulated_metrics():
    """Update simulated system metrics periodically."""
    logger.info("Starting simulated metrics updater", extra={
        "component": "metrics_updater",
        "interval_seconds": 5
    })
    while True:
        cpu = random.uniform(10, 90)
        memory = random.randint(100_000_000, 500_000_000)
        cpu_usage.set(cpu)
        memory_usage.set(memory)
        logger.debug("Updated simulated metrics", extra={
            "component": "metrics_updater",
            "cpu_percent": round(cpu, 2),
            "memory_bytes": memory
        })
        time.sleep(5)


def trace_worker():
    """Worker function that creates traces."""
    logger.info("Starting trace worker", extra={
        "component": "trace_worker",
        "otlp_endpoint": "http://alloy.alloy.svc:4318/v1/traces"
    })

    iteration = 0
    try:
        while True:
            iteration += 1
            with tracer.start_as_current_span("main_operation") as span:
                span.set_attribute("iteration", iteration)

                user_id = f"user_{random.randint(1, 100)}"
                logger.info("Processing item in main operation", extra={
                    "component": "trace_worker",
                    "iteration": iteration,
                    "user_id": user_id,
                    "environment": "development",
                    "trace_id": format(span.get_span_context().trace_id, '032x'),
                    "span_id": format(span.get_span_context().span_id, '016x')
                })

                process_data(iteration)

                # Add some random attributes
                span.set_attribute("environment", "development")
                span.set_attribute("user.id", user_id)

            time.sleep(1)

    except Exception as e:
        logger.error("Error in trace worker", extra={
            "component": "trace_worker",
            "error_type": "worker_error",
            "error_message": str(e),
            "iteration": iteration
        }, exc_info=True)
        error_count.labels(error_type='worker_error').inc()


def main():
    """Main function that starts the Flask server and trace worker."""
    logger.info("Starting metrics-demo application", extra={
        "service": "trace-test-app",
        "version": "1.0.0",
        "metrics_endpoint": "http://0.0.0.0:8000/metrics",
        "health_endpoint": "http://0.0.0.0:8000/health"
    })

    # Start metrics updater thread
    metrics_thread = threading.Thread(target=update_simulated_metrics, daemon=True)
    metrics_thread.start()
    logger.info("Metrics updater thread started", extra={
        "thread_name": "metrics_updater",
        "daemon": True
    })

    # Start trace worker thread
    trace_thread = threading.Thread(target=trace_worker, daemon=True)
    trace_thread.start()
    logger.info("Trace worker thread started", extra={
        "thread_name": "trace_worker",
        "daemon": True
    })

    # Start Flask server
    try:
        logger.info("Starting Flask server", extra={
            "host": "0.0.0.0",
            "port": 8000,
            "threaded": True
        })
        app.run(host='0.0.0.0', port=8000, threaded=True)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user", extra={
            "signal": "KeyboardInterrupt"
        })
    finally:
        logger.info("Waiting for traces to be exported", extra={
            "wait_seconds": 2
        })
        time.sleep(2)
        tracer_provider.shutdown()
        logger.info("Application finished", extra={
            "shutdown": "complete"
        })


if __name__ == "__main__":
    main()
