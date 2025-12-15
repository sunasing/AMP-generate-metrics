from prometheus_client import Counter, Gauge, Histogram, Summary, Info, Enum, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.prometheus import PrometheusMetricReader
import random
import time
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

"""
Complete example with both Prometheus and OpenTelemetry metrics
"""

# ============================================================================
# PROMETHEUS METRICS SETUP
# ============================================================================

# Counters
prom_http_requests_total = Counter(
    name='http_requests_total',
    documentation='Total HTTP requests',
    labelnames=['method', 'endpoint', 'status']
)

prom_http_errors_total = Counter(
    name='http_errors_total',
    documentation='Total HTTP errors',
    labelnames=['method', 'endpoint', 'error_type']
)

prom_bytes_processed_total = Counter(
    name='bytes_processed_total',
    documentation='Total bytes processed',
    labelnames=['operation']
)

# Gauges
prom_active_connections = Gauge(
    name='active_connections',
    documentation='Number of active connections',
    labelnames=['protocol']
)

prom_memory_usage_bytes = Gauge(
    name='memory_usage_bytes',
    documentation='Current memory usage in bytes',
    labelnames=['region']
)

prom_queue_size = Gauge(
    name='queue_size',
    documentation='Current queue size',
    labelnames=['queue_name']
)

prom_cpu_usage_percent = Gauge(
    name='cpu_usage_percent',
    documentation='Current CPU usage percentage'
)

# Histograms
prom_http_request_duration_seconds = Histogram(
    name='http_request_duration_seconds',
    documentation='HTTP request duration in seconds',
    labelnames=['method', 'endpoint', 'status'],
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)

prom_db_query_duration_seconds = Histogram(
    name='db_query_duration_seconds',
    documentation='Database query duration in seconds',
    labelnames=['query_type', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

prom_response_size_bytes = Histogram(
    name='response_size_bytes',
    documentation='HTTP response size in bytes',
    labelnames=['endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000]
)

# Summaries
prom_request_duration_summary = Summary(
    name='request_duration_seconds_summary',
    documentation='Request duration summary with quantiles',
    labelnames=['method', 'endpoint']
)

prom_payload_size_summary = Summary(
    name='payload_size_bytes_summary',
    documentation='Payload size summary',
    labelnames=['direction']
)

# Info & Enum
prom_app_info = Info(
    name='app',
    documentation='Application information'
)
prom_app_info.info({
    'version': '1.2.3',
    'environment': 'production',
    'build_date': '2024-12-01',
    'git_commit': 'abc123def'
})

prom_app_state = Enum(
    name='app_state',
    documentation='Current application state',
    states=['starting', 'running', 'degraded', 'shutting_down']
)
prom_app_state.state('running')


# ============================================================================
# OPENTELEMETRY METRICS SETUP
# ============================================================================

# Create resource with service information
resource = Resource.create({
    "service.name": "prometheus-metrics-app",
    "service.version": "1.2.3",
    "service.instance.id": "instance-1",
    "deployment.environment": "production"
})

# Setup OTEL Meter Provider
meter_provider = MeterProvider(resource=resource)
metrics.set_meter_provider(meter_provider)

# Get a meter
meter = metrics.get_meter("prometheus-metrics-app", "1.2.3")

# OTEL Counters
otel_http_requests_counter = meter.create_counter(
    name="http_requests_total",
    description="Total HTTP requests",
    unit="1"
)

otel_http_errors_counter = meter.create_counter(
    name="http_errors_total",
    description="Total HTTP errors",
    unit="1"
)

otel_bytes_processed_counter = meter.create_counter(
    name="bytes_processed_total",
    description="Total bytes processed",
    unit="bytes"
)

# OTEL Gauges (using Observable Gauge)
# Store current values for observable gauges
otel_gauge_values = {
    'active_connections': {},
    'memory_usage': {},
    'queue_size': {},
    'cpu_usage': 0.0
}

def get_active_connections(options):
    """Callback for active connections gauge"""
    for protocol, value in otel_gauge_values['active_connections'].items():
        yield metrics.Observation(value, {"protocol": protocol})

def get_memory_usage(options):
    """Callback for memory usage gauge"""
    for region, value in otel_gauge_values['memory_usage'].items():
        yield metrics.Observation(value, {"region": region})

def get_queue_size(options):
    """Callback for queue size gauge"""
    for queue_name, value in otel_gauge_values['queue_size'].items():
        yield metrics.Observation(value, {"queue_name": queue_name})

def get_cpu_usage(options):
    """Callback for CPU usage gauge"""
    yield metrics.Observation(otel_gauge_values['cpu_usage'], {})

# Create observable gauges
otel_active_connections_gauge = meter.create_observable_gauge(
    name="active_connections",
    callbacks=[get_active_connections],
    description="Number of active connections",
    unit="1"
)

otel_memory_usage_gauge = meter.create_observable_gauge(
    name="memory_usage_bytes",
    callbacks=[get_memory_usage],
    description="Current memory usage in bytes",
    unit="bytes"
)

otel_queue_size_gauge = meter.create_observable_gauge(
    name="queue_size",
    callbacks=[get_queue_size],
    description="Current queue size",
    unit="1"
)

otel_cpu_usage_gauge = meter.create_observable_gauge(
    name="cpu_usage_percent",
    callbacks=[get_cpu_usage],
    description="Current CPU usage percentage",
    unit="%"
)

# OTEL Histograms
otel_http_request_duration = meter.create_histogram(
    name="http_request_duration_seconds",
    description="HTTP request duration in seconds",
    unit="s"
)

otel_db_query_duration = meter.create_histogram(
    name="db_query_duration_seconds",
    description="Database query duration in seconds",
    unit="s"
)

otel_response_size = meter.create_histogram(
    name="response_size_bytes",
    description="HTTP response size in bytes",
    unit="bytes"
)

otel_payload_size = meter.create_histogram(
    name="payload_size_bytes",
    description="Payload size",
    unit="bytes"
)


# ============================================================================
# METRIC GENERATION FUNCTIONS
# ============================================================================

def generate_prometheus_http_metrics(count=50):
    """Generate Prometheus HTTP request metrics"""
    methods = ['GET', 'POST', 'PUT', 'DELETE']
    endpoints = ['/users', '/orders', '/products', '/auth']
    
    for _ in range(count):
        method = random.choice(methods)
        endpoint = random.choice(endpoints)
        
        if random.random() < 0.9:
            status = '200'
            duration = random.uniform(0.05, 2.0)
        elif random.random() < 0.5:
            status = '404'
            duration = random.uniform(0.01, 0.1)
            prom_http_errors_total.labels(
                method=method, endpoint=endpoint, error_type='not_found'
            ).inc()
        else:
            status = '500'
            duration = random.uniform(0.5, 5.0)
            prom_http_errors_total.labels(
                method=method, endpoint=endpoint, error_type='internal_error'
            ).inc()
        
        prom_http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        prom_http_request_duration_seconds.labels(method=method, endpoint=endpoint, status=status).observe(duration)
        prom_request_duration_summary.labels(method=method, endpoint=endpoint).observe(duration)
        
        response_size = random.randint(100, 50000)
        prom_response_size_bytes.labels(endpoint=endpoint).observe(response_size)


def generate_otel_http_metrics(count=50):
    """Generate OpenTelemetry HTTP request metrics"""
    methods = ['GET', 'POST', 'PUT', 'DELETE']
    endpoints = ['/users', '/orders', '/products', '/auth']
    
    for _ in range(count):
        method = random.choice(methods)
        endpoint = random.choice(endpoints)
        
        if random.random() < 0.9:
            status = '200'
            duration = random.uniform(0.05, 2.0)
        elif random.random() < 0.5:
            status = '404'
            duration = random.uniform(0.01, 0.1)
            otel_http_errors_counter.add(1, {
                "method": method, "endpoint": endpoint, "error_type": "not_found"
            })
        else:
            status = '500'
            duration = random.uniform(0.5, 5.0)
            otel_http_errors_counter.add(1, {
                "method": method, "endpoint": endpoint, "error_type": "internal_error"
            })
        
        otel_http_requests_counter.add(1, {"method": method, "endpoint": endpoint, "status": status})
        otel_http_request_duration.record(duration, {"method": method, "endpoint": endpoint, "status": status})
        
        response_size = random.randint(100, 50000)
        otel_response_size.record(response_size, {"endpoint": endpoint})


def generate_prometheus_database_metrics(count=30):
    """Generate Prometheus database query metrics"""
    query_types = ['SELECT', 'INSERT', 'UPDATE', 'DELETE']
    tables = ['users', 'orders', 'products']
    
    for _ in range(count):
        query_type = random.choice(query_types)
        table = random.choice(tables)
        duration = random.uniform(0.001, 0.1) if query_type == 'SELECT' else random.uniform(0.005, 0.2)
        prom_db_query_duration_seconds.labels(query_type=query_type, table=table).observe(duration)


def generate_otel_database_metrics(count=30):
    """Generate OpenTelemetry database query metrics"""
    query_types = ['SELECT', 'INSERT', 'UPDATE', 'DELETE']
    tables = ['users', 'orders', 'products']
    
    for _ in range(count):
        query_type = random.choice(query_types)
        table = random.choice(tables)
        duration = random.uniform(0.001, 0.1) if query_type == 'SELECT' else random.uniform(0.005, 0.2)
        otel_db_query_duration.record(duration, {"query_type": query_type, "table": table})


def generate_prometheus_system_metrics():
    """Generate Prometheus system-level gauge metrics"""
    protocols = ['http', 'grpc', 'websocket']
    regions = ['heap', 'stack', 'cache']
    queues = ['high_priority', 'normal', 'low_priority']
    
    for protocol in protocols:
        prom_active_connections.labels(protocol=protocol).set(random.randint(10, 100))
    
    for region in regions:
        prom_memory_usage_bytes.labels(region=region).set(random.randint(1000000, 50000000))
    
    for queue_name in queues:
        prom_queue_size.labels(queue_name=queue_name).set(random.randint(0, 100))
    
    prom_cpu_usage_percent.set(random.uniform(10, 90))
    prom_bytes_processed_total.labels(operation='upload').inc(random.randint(100000, 1000000))
    prom_bytes_processed_total.labels(operation='download').inc(random.randint(500000, 5000000))


def generate_otel_system_metrics():
    """Generate OpenTelemetry system-level gauge metrics"""
    protocols = ['http', 'grpc', 'websocket']
    regions = ['heap', 'stack', 'cache']
    queues = ['high_priority', 'normal', 'low_priority']
    
    # Update gauge values (these will be read by callbacks)
    for protocol in protocols:
        otel_gauge_values['active_connections'][protocol] = random.randint(10, 100)
    
    for region in regions:
        otel_gauge_values['memory_usage'][region] = random.randint(1000000, 50000000)
    
    for queue_name in queues:
        otel_gauge_values['queue_size'][queue_name] = random.randint(0, 100)
    
    otel_gauge_values['cpu_usage'] = random.uniform(10, 90)
    
    # Update counters
    otel_bytes_processed_counter.add(random.randint(100000, 1000000), {"operation": "upload"})
    otel_bytes_processed_counter.add(random.randint(500000, 5000000), {"operation": "download"})


def generate_prometheus_payload_metrics(count=20):
    """Generate Prometheus payload size metrics"""
    for _ in range(count):
        prom_payload_size_summary.labels(direction='inbound').observe(random.randint(100, 10000))
        prom_payload_size_summary.labels(direction='outbound').observe(random.randint(500, 50000))


def generate_otel_payload_metrics(count=20):
    """Generate OpenTelemetry payload size metrics"""
    for _ in range(count):
        otel_payload_size.record(random.randint(100, 10000), {"direction": "inbound"})
        otel_payload_size.record(random.randint(500, 50000), {"direction": "outbound"})


def generate_all_prometheus_metrics():
    """Generate all Prometheus metrics at once"""
    print("Generating Prometheus metrics...")
    generate_prometheus_http_metrics(50)
    generate_prometheus_database_metrics(30)
    generate_prometheus_system_metrics()
    generate_prometheus_payload_metrics(20)
    print("Prometheus metrics generated successfully!")


def generate_all_otel_metrics():
    """Generate all OpenTelemetry metrics at once"""
    print("Generating OpenTelemetry metrics...")
    generate_otel_http_metrics(50)
    generate_otel_database_metrics(30)
    generate_otel_system_metrics()
    generate_otel_payload_metrics(20)
    print("OpenTelemetry metrics generated successfully!")


# ============================================================================
# HTTP SERVER WITH CUSTOM ENDPOINTS
# ============================================================================

class MetricsHandler(BaseHTTPRequestHandler):
    """Custom HTTP handler with multiple endpoints"""
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Prometheus & OTEL Metrics Simulator</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
                    .container { background-color: white; padding: 30px; border-radius: 8px; max-width: 900px; margin: 0 auto; }
                    h1 { color: #333; }
                    h2 { color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }
                    .endpoint { background-color: #e8f4f8; padding: 15px; margin: 10px 0; border-radius: 5px; }
                    .endpoint-url { color: #0066cc; font-weight: bold; font-size: 16px; }
                    .button-group { margin-top: 10px; }
                    button { background-color: #0066cc; color: white; padding: 10px 20px; 
                             border: none; border-radius: 5px; cursor: pointer; font-size: 14px; margin-right: 10px; }
                    button:hover { background-color: #0052a3; }
                    .otel-button { background-color: #28a745; }
                    .otel-button:hover { background-color: #218838; }
                    .info { background-color: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 20px; }
                    .comparison { background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin-top: 20px; }
                    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
                    th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
                    th { background-color: #0066cc; color: white; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎯 Prometheus & OpenTelemetry Metrics Simulator</h1>
                    <p>Generate metrics in both Prometheus and OpenTelemetry formats!</p>
                    
                    <h2>📊 Prometheus Endpoints</h2>
                    
                    <div class="endpoint">
                        <div class="endpoint-url">GET /generatemetrics</div>
                        <p>Generates Prometheus-format metrics</p>
                        <div class="button-group">
                            <button onclick="fetch('/generatemetrics').then(r => r.text()).then(alert)">
                                Generate Prometheus Metrics
                            </button>
                            <button onclick="window.open('/metrics', '_blank')">View Metrics</button>
                        </div>
                    </div>
                    
                    <div class="endpoint">
                        <div class="endpoint-url">GET /metrics</div>
                        <p>Returns all Prometheus metrics in exposition format</p>
                    </div>
                    
                    <h2>🔭 OpenTelemetry Endpoints</h2>
                    
                    <div class="endpoint">
                        <div class="endpoint-url">GET /generateotelmetrics</div>
                        <p>Generates OpenTelemetry-format metrics</p>
                        <div class="button-group">
                            <button class="otel-button" onclick="fetch('/generateotelmetrics').then(r => r.text()).then(alert)">
                                Generate OTEL Metrics
                            </button>
                            <button class="otel-button" onclick="window.open('/otelmetrics', '_blank')">View OTEL Metrics</button>
                        </div>
                    </div>
                    
                    <div class="endpoint">
                        <div class="endpoint-url">GET /otelmetrics</div>
                        <p>Returns OpenTelemetry metrics in JSON format</p>
                    </div>
                    
                    <div class="comparison">
                        <h3>📋 Key Differences</h3>
                        <table>
                            <tr>
                                <th>Aspect</th>
                                <th>Prometheus</th>
                                <th>OpenTelemetry</th>
                            </tr>
                            <tr>
                                <td><strong>Format</strong></td>
                                <td>Text-based exposition format</td>
                                <td>JSON/Protobuf (OTLP)</td>
                            </tr>
                            <tr>
                                <td><strong>Pull/Push</strong></td>
                                <td>Pull-based (scraping)</td>
                                <td>Push-based (export)</td>
                            </tr>
                            <tr>
                                <td><strong>Metric Types</strong></td>
                                <td>Counter, Gauge, Histogram, Summary</td>
                                <td>Counter, Gauge, Histogram</td>
                            </tr>
                            <tr>
                                <td><strong>Labels</strong></td>
                                <td>Key-value pairs</td>
                                <td>Attributes (key-value pairs)</td>
                            </tr>
                            <tr>
                                <td><strong>Best For</strong></td>
                                <td>Kubernetes, infrastructure monitoring</td>
                                <td>Distributed tracing, multi-vendor</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div class="info">
                        <strong>💡 How to use:</strong>
                        <ol>
                            <li><strong>Prometheus:</strong> Click "Generate Prometheus Metrics" then "View Metrics"</li>
                            <li><strong>OpenTelemetry:</strong> Click "Generate OTEL Metrics" then "View OTEL Metrics"</li>
                            <li>Compare the different formats!</li>
                        </ol>
                    </div>
                    
                    <h3>Metric Types Included:</h3>
                    <ul>
                        <li><strong>Counters:</strong> http_requests_total, http_errors_total, bytes_processed_total</li>
                        <li><strong>Gauges:</strong> active_connections, memory_usage_bytes, queue_size, cpu_usage_percent</li>
                        <li><strong>Histograms:</strong> http_request_duration_seconds, db_query_duration_seconds, response_size_bytes</li>
                    </ul>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            
        elif self.path == '/generatemetrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            
            generate_all_prometheus_metrics()
            
            response = """Prometheus metrics generated successfully!

Generated:
- 50 HTTP request samples
- 30 Database query samples
- System metrics (connections, memory, CPU, queues)
- 20 Payload size samples

View metrics at: http://localhost:8000/metrics
"""
            self.wfile.write(response.encode())
            
        elif self.path == '/generateotelmetrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            
            generate_all_otel_metrics()
            
            response = """OpenTelemetry metrics generated successfully!

Generated:
- 50 HTTP request samples (OTEL format)
- 30 Database query samples (OTEL format)
- System metrics (connections, memory, CPU, queues)
- 20 Payload size samples (OTEL format)

View metrics at: http://localhost:8000/otelmetrics

Note: OTEL metrics are shown in a simplified JSON format.
In production, these would be exported to an OTEL collector using OTLP protocol.
"""
            self.wfile.write(response.encode())
            
        elif self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())
            
        elif self.path == '/otelmetrics':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Generate a simplified JSON representation of OTEL metrics
            otel_metrics_summary = {
                "resource": {
                    "attributes": {
                        "service.name": "prometheus-metrics-app",
                        "service.version": "1.2.3",
                        "service.instance.id": "instance-1",
                        "deployment.environment": "production"
                    }
                },
                "scope_metrics": [
                    {
                        "scope": {
                            "name": "prometheus-metrics-app",
                            "version": "1.2.3"
                        },
                        "metrics": [
                            {
                                "name": "http_requests_total",
                                "description": "Total HTTP requests",
                                "unit": "1",
                                "type": "Counter",
                                "note": "Actual values tracked internally"
                            },
                            {
                                "name": "http_errors_total",
                                "description": "Total HTTP errors",
                                "unit": "1",
                                "type": "Counter"
                            },
                            {
                                "name": "bytes_processed_total",
                                "description": "Total bytes processed",
                                "unit": "bytes",
                                "type": "Counter"
                            },
                            {
                                "name": "active_connections",
                                "description": "Number of active connections",
                                "unit": "1",
                                "type": "Observable Gauge",
                                "current_values": otel_gauge_values['active_connections']
                            },
                            {
                                "name": "memory_usage_bytes",
                                "description": "Current memory usage in bytes",
                                "unit": "bytes",
                                "type": "Observable Gauge",
                                "current_values": otel_gauge_values['memory_usage']
                            },
                            {
                                "name": "queue_size",
                                "description": "Current queue size",
                                "unit": "1",
                                "type": "Observable Gauge",
                                "current_values": otel_gauge_values['queue_size']
                            },
                            {
                                "name": "cpu_usage_percent",
                                "description": "Current CPU usage percentage",
                                "unit": "%",
                                "type": "Observable Gauge",
                                "current_value": otel_gauge_values['cpu_usage']
                            },
                            {
                                "name": "http_request_duration_seconds",
                                "description": "HTTP request duration in seconds",
                                "unit": "s",
                                "type": "Histogram"
                            },
                            {
                                "name": "db_query_duration_seconds",
                                "description": "Database query duration in seconds",
                                "unit": "s",
                                "type": "Histogram"
                            },
                            {
                                "name": "response_size_bytes",
                                "description": "HTTP response size in bytes",
                                "unit": "bytes",
                                "type": "Histogram"
                            },
                            {
                                "name": "payload_size_bytes",
                                "description": "Payload size",
                                "unit": "bytes",
                                "type": "Histogram"
                            }
                        ]
                    }
                ],
                "note": "This is a simplified representation. In production, OTEL metrics would be exported to an OTEL collector via OTLP protocol (gRPC or HTTP)."
            }
            
            self.wfile.write(json.dumps(otel_metrics_summary, indent=2).encode())
            
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'404 - Not Found')
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(port=8000):
    """Run the HTTP server"""
    server = HTTPServer(('', port), MetricsHandler)
    print("\n" + "="*70)
    print("PROMETHEUS & OPENTELEMETRY METRICS SIMULATOR")
    print("="*70)
    print(f"\n🚀 Server started on http://localhost:{port}")
    print("\nAvailable endpoints:")
    print(f"  🏠 Home:                    http://localhost:{port}/")
    print(f"  📊 Generate Prom metrics:   http://localhost:{port}/generatemetrics")
    print(f"  📈 View Prom metrics:       http://localhost:{port}/metrics")
    print(f"  🔭 Generate OTEL metrics:   http://localhost:{port}/generateotelmetrics")
    print(f"  📉 View OTEL metrics:       http://localhost:{port}/otelmetrics")
    print("\n" + "="*70)
    print("\nWaiting for requests... (Press Ctrl+C to stop)\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        prom_app_state.state('shutting_down')
        server.shutdown()


if __name__ == '__main__':
    # Initialize some baseline metrics
    generate_prometheus_system_metrics()
    generate_otel_system_metrics()
    
    # Start the server
    run_server(port=8000)