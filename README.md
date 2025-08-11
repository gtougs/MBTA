# MBTA Data Pipeline

A real-time data engineering pipeline for ingesting, processing, and analyzing MBTA (Massachusetts Bay Transportation Authority) transit data. This project demonstrates modern data engineering practices including real-time ingestion, streaming, and analytics.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MBTA V3 API  │    │   GTFS-RT Feeds │    │   Local Dev     │
│   (REST JSON)  │    │   (Protobuf)    │    │   Environment   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Ingestion Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ V3 REST        │  │ GTFS-RT         │  │ Rate Limiting   │ │
│  │ Ingestor       │  │ Ingestor        │  │ & Retry Logic   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          │                      │
          ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Streaming Layer (Kafka)                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ mbta.predictions│  │ mbta.vehicles   │  │ mbta.alerts     │ │
│  │ .raw            │  │ .raw            │  │ .raw            │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          │                      │
          ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Warehouse (BigQuery)                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ dim_route       │  │ fact_predictions│  │ fact_vehicles   │ │
│  │ dim_stop        │  │ fact_trip_updates│  │ fact_alerts     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          │                      │
          ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Analytics & Visualization                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ On-time         │  │ Headway         │  │ Vehicle         │ │
│  │ Performance     │  │ Analysis        │  │ Location Map    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Features

- **Dual Data Sources**: 
  - MBTA V3 REST API (JSON) for predictions and vehicle data
  - GTFS-RT protobuf feeds for real-time updates
- **Real-time Ingestion**: Polling-based ingestion with configurable intervals
- **Streaming Architecture**: Kafka integration for event-driven processing
- **Data Validation**: Pydantic models with comprehensive validation
- **Rate Limiting**: Built-in rate limiting and retry logic
- **Monitoring**: Health checks, metrics, and structured logging
- **Containerized**: Docker support for easy deployment
- **Async Processing**: High-performance async/await architecture

## 📋 Prerequisites

- Python 3.9+
- Docker and Docker Compose
- MBTA API key (request at [MBTA Developer Portal](https://api-v3.mbta.com/))
- Google Cloud account (for BigQuery)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd mbta-data-pipeline
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install with development extras
pip install -e ".[dev]"
```

### 3. Environment Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env with your configuration
MBTA_API_KEY=your_mbta_api_key_here
BIGQUERY_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
```

### 4. Start Local Infrastructure

```bash
# Start Kafka, Zookeeper, and other services
docker-compose up -d

# Verify services are running
docker-compose ps
```

## 🚀 Usage

### Running the Pipeline

```bash
# Run the main pipeline
python -m src.main

# Or run with Docker
docker-compose up mbta-pipeline
```

### Development Mode

```bash
# Run with hot reload (if using development tools)
pip install -e ".[dev]"
python -m src.main --dev
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test files
pytest tests/test_ingestion.py
```

## 📊 Data Models

### Core Entities

- **Prediction**: Real-time arrival/departure predictions
- **VehiclePosition**: Current vehicle locations and status
- **TripUpdate**: Real-time trip modifications and delays
- **Alert**: Service alerts and disruptions
- **Route**: Transit route information
- **Stop**: Station and stop information

### Analytics Models

- **HeadwayAnalysis**: Time between consecutive vehicles
- **OnTimePerformance**: Delay and punctuality metrics
- **AnomalyDetection**: Unusual patterns and outliers

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MBTA_API_KEY` | MBTA V3 API key | Required |
| `MBTA_BASE_URL` | MBTA API base URL | `https://api-v3.mbta.com` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker addresses | `localhost:9092` |
| `BIGQUERY_PROJECT_ID` | Google Cloud project ID | Required |
| `POLLING_INTERVAL_SECONDS` | Data ingestion frequency | `15` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

### Configuration Files

- `config/settings.py`: Main configuration management
- `config/pipeline.yaml`: Pipeline-specific settings
- `docker-compose.yml`: Local development services

## 📈 Monitoring & Observability

### Health Checks

```bash
# Check pipeline health
curl http://localhost:8080/health

# Check individual ingestor status
curl http://localhost:8080/ingestors/v3_rest/health
```

### Metrics

- Records ingested per second
- API response times
- Error rates and failure counts
- Data freshness indicators

### Logging

Structured logging with:
- Request/response correlation
- Performance timing
- Error context and stack traces
- JSON output in production

## 🚀 Deployment

### Production Deployment

```bash
# Build production image
docker build -t mbta-pipeline:latest .

# Run with production config
docker run -d \
  --name mbta-pipeline \
  --env-file .env.prod \
  mbta-pipeline:latest
```

### Kubernetes

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -l app=mbta-pipeline
```

## 🔍 Troubleshooting

### Common Issues

1. **API Rate Limiting**: Check MBTA API limits and adjust polling intervals
2. **GTFS-RT Parsing Errors**: Verify protobuf feed format and version
3. **Kafka Connection Issues**: Check broker connectivity and topic configuration
4. **BigQuery Authentication**: Verify service account credentials and permissions

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python -m src.main --debug
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install

# Run code quality checks
black src/
flake8 src/
mypy src/
```

## 📚 Documentation

- [API Reference](docs/api.md)
- [Data Schema](docs/schema.md)
- [Deployment Guide](docs/deployment.md)
- [Troubleshooting](docs/troubleshooting.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [MBTA](https://www.mbta.com/) for providing the transit data APIs
- [GTFS-RT](https://developers.google.com/transit/gtfs-realtime) specification
- [Confluent](https://www.confluent.io/) for Kafka tooling
- [Google Cloud](https://cloud.google.com/) for BigQuery

## 📞 Support

For questions and support:
- Create an issue in this repository
- Check the [troubleshooting guide](docs/troubleshooting.md)
- Review the [MBTA API documentation](https://api-v3.mbta.com/docs/swagger/index.html)
