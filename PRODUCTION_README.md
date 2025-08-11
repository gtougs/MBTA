# MBTA Transit Analytics Dashboard - Production Setup Guide

## Overview

This guide provides comprehensive instructions for deploying the MBTA Transit Analytics Dashboard in a production environment. The system consists of two main components:

1. **Data Pipeline** - Continuous data collection from MBTA APIs
2. **Streamlit Dashboard** - Interactive analytics interface

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MBTA APIs     │    │  GTFS-RT Feeds  │    │  Cloud/Server   │
│   (REST/V3)     │    │   (Real-time)   │    │   Environment   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼───────┐    ┌─────────▼───────┐    ┌─────────▼───────┐
│   Data          │    │   Data          │    │   Data          │
│   Ingestion     │    │   Processing    │    │   Storage       │
│   (Background)  │    │   (Real-time)   │    │   (PostgreSQL)  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼───────┐    ┌─────────▼───────┐    ┌─────────▼───────┐
│   Analytics     │    │   Streamlit     │    │   Website       │
│   Engine        │    │   Dashboard     │    │   Embed         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Prerequisites

### System Requirements
- **Operating System**: Ubuntu 20.04 LTS or later
- **Python**: Python 3.8 or later
- **Memory**: Minimum 4GB RAM, recommended 8GB+
- **Storage**: Minimum 50GB available disk space
- **Network**: Stable internet connection for API access

### Software Dependencies
- PostgreSQL 12 or later
- Nginx (for reverse proxy)
- Git
- Python virtual environment tools

## Quick Start

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd MBTA
```

### 2. Run Production Deployment Script
```bash
chmod +x deploy_production.sh
./deploy_production.sh
```

### 3. Configure Environment
```bash
# Copy example configuration
cp config.env.example .env

# Edit with your actual values
nano .env
```

### 4. Start Services
```bash
sudo systemctl start mbta-pipeline
sudo systemctl start mbta-dashboard
```

## Manual Setup

### 1. System Preparation

#### Update System Packages
```bash
sudo apt update && sudo apt upgrade -y
```

#### Install Required Packages
```bash
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    nginx \
    supervisor \
    curl \
    git \
    build-essential \
    libpq-dev
```

### 2. Database Setup

#### Create Database User and Database
```bash
sudo -u postgres psql

CREATE USER mbta_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE mbta_data OWNER mbta_user;
GRANT ALL PRIVILEGES ON DATABASE mbta_data TO mbta_user;
\q
```

#### Configure PostgreSQL
```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```

Add/modify these lines:
```
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

#### Restart PostgreSQL
```bash
sudo systemctl restart postgresql
```

### 3. Application Setup

#### Create Application User
```bash
sudo useradd -r -s /bin/bash -d /opt/mbta-pipeline mbta
```

#### Clone Application
```bash
sudo -u mbta git clone <your-repo-url> /opt/mbta-pipeline
sudo chown -R mbta:mbta /opt/mbta-pipeline
```

#### Setup Python Environment
```bash
sudo -u mbta python3 -m venv /opt/mbta-pipeline/venv
sudo -u mbta /opt/mbta-pipeline/venv/bin/pip install --upgrade pip
sudo -u mbta /opt/mbta-pipeline/venv/bin/pip install -r /opt/mbta-pipeline/requirements.txt
```

### 4. Configuration

#### Environment Configuration
```bash
sudo -u mbta cp /opt/mbta-pipeline/config.env.example /opt/mbta-pipeline/.env
sudo -u mbta nano /opt/mbta-pipeline/.env
```

Required environment variables:
```bash
# MBTA API Configuration
MBTA_API_KEY=your_actual_api_key_here
MBTA_BASE_URL=https://api-v3.mbta.com
MBTA_GTFS_RT_BASE_URL=https://cdn.mbta.com/realtime

# Database Configuration
DATABASE_URL=postgresql://mbta_user:your_secure_password@localhost:5432/mbta_data
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Application Configuration
LOG_LEVEL=INFO
POLLING_INTERVAL_SECONDS=15
BATCH_SIZE=100
MAX_RETRIES=3
RETRY_DELAY_SECONDS=5

# Production Settings
DEBUG=false
ENVIRONMENT=production
```

### 5. Service Configuration

#### Create Pipeline Service
```bash
sudo tee /etc/systemd/system/mbta-pipeline.service > /dev/null <<EOF
[Unit]
Description=MBTA Data Pipeline
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=mbta
WorkingDirectory=/opt/mbta-pipeline
Environment=PATH=/opt/mbta-pipeline/venv/bin
ExecStart=/opt/mbta-pipeline/venv/bin/python start_pipeline.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### Create Dashboard Service
```bash
sudo tee /etc/systemd/system/mbta-dashboard.service > /dev/null <<EOF
[Unit]
Description=MBTA Streamlit Dashboard
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=mbta
WorkingDirectory=/opt/mbta-pipeline
Environment=PATH=/opt/mbta-pipeline/venv/bin
ExecStart=/opt/mbta-pipeline/venv/bin/streamlit run streamlit_dashboard.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### Enable and Start Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable mbta-pipeline
sudo systemctl enable mbta-dashboard
sudo systemctl start mbta-pipeline
sudo systemctl start mbta-dashboard
```

### 6. Nginx Configuration

#### Create Nginx Site Configuration
```bash
sudo tee /etc/nginx/sites-available/mbta-dashboard > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }
}
EOF
```

#### Enable Site and Restart Nginx
```bash
sudo ln -s /etc/nginx/sites-available/mbta-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. SSL Configuration (Optional but Recommended)

#### Install Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
```

#### Obtain SSL Certificate
```bash
sudo certbot --nginx -d your-domain.com
```

## Monitoring and Maintenance

### Service Status
```bash
# Check service status
sudo systemctl status mbta-pipeline
sudo systemctl status mbta-dashboard

# View logs
sudo journalctl -u mbta-pipeline -f
sudo journalctl -u mbta-dashboard -f
```

### Database Maintenance
```bash
# Connect to database
sudo -u postgres psql mbta_data

# Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# Check recent data
SELECT COUNT(*) FROM predictions WHERE timestamp >= NOW() - INTERVAL '1 hour';
```

### Health Checks
```bash
# Test database connection
sudo -u mbta /opt/mbta-pipeline/venv/bin/python -c "
from mbta_pipeline.storage.database import DatabaseManager
db = DatabaseManager()
print('Database connection:', 'OK' if db.test_connection() else 'FAILED')
"

# Test API connectivity
curl -H "Authorization: Bearer YOUR_API_KEY" https://api-v3.mbta.com/routes
```

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service logs
sudo journalctl -u mbta-pipeline -n 50
sudo journalctl -u mbta-dashboard -n 50

# Check permissions
sudo chown -R mbta:mbta /opt/mbta-pipeline
```

#### Database Connection Issues
```bash
# Test PostgreSQL connection
sudo -u postgres psql -d mbta_data -c "SELECT version();"

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

#### API Rate Limiting
- Check MBTA API key validity
- Verify rate limit settings in configuration
- Monitor API response codes in logs

### Performance Optimization

#### Database Tuning
```bash
# Add to postgresql.conf
shared_buffers = 25% of RAM
effective_cache_size = 75% of RAM
work_mem = 4MB
maintenance_work_mem = 64MB
```

#### Application Tuning
- Adjust `POLLING_INTERVAL_SECONDS` based on needs
- Optimize `BATCH_SIZE` for your system
- Monitor memory usage and adjust accordingly

## Security Considerations

### Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### API Key Security
- Store API keys securely in environment variables
- Never commit API keys to version control
- Rotate API keys regularly
- Use least-privilege access for API keys

### Database Security
- Use strong passwords for database users
- Limit database access to application servers only
- Enable SSL connections for database
- Regular security updates

## Backup and Recovery

### Database Backup
```bash
# Create backup script
sudo tee /opt/mbta-pipeline/backup_db.sh > /dev/null <<EOF
#!/bin/bash
BACKUP_DIR="/opt/mbta-pipeline/backups"
DATE=\$(date +%Y%m%d_%H%M%S)
sudo -u postgres pg_dump mbta_data > \$BACKUP_DIR/mbta_data_\$DATE.sql
find \$BACKUP_DIR -name "*.sql" -mtime +7 -delete
EOF

sudo chmod +x /opt/mbta-pipeline/backup_db.sh
sudo chown mbta:mbta /opt/mbta-pipeline/backup_db.sh

# Add to crontab for daily backups
sudo crontab -e
# Add: 0 2 * * * /opt/mbta-pipeline/backup_db.sh
```

### Application Backup
```bash
# Backup application code
sudo tar -czf /opt/mbta-pipeline/backups/app_$(date +%Y%m%d_%H%M%S).tar.gz \
    /opt/mbta-pipeline --exclude=/opt/mbta-pipeline/venv \
    --exclude=/opt/mbta-pipeline/backups
```

## Scaling Considerations

### Horizontal Scaling
- Run multiple pipeline instances
- Use load balancer for dashboard
- Implement database read replicas
- Use Redis for caching

### Vertical Scaling
- Increase server resources
- Optimize database queries
- Implement data partitioning
- Use connection pooling

## Support and Maintenance

### Regular Maintenance Tasks
- Monitor disk space usage
- Check service health daily
- Review error logs weekly
- Update system packages monthly
- Review performance metrics quarterly

### Monitoring Tools
- System monitoring: htop, iotop, nethogs
- Database monitoring: pg_stat_statements, pg_stat_monitor
- Application monitoring: Custom health checks
- Log monitoring: journalctl, logrotate

## Conclusion

This production setup provides a robust, scalable foundation for the MBTA Transit Analytics Dashboard. The system is designed to run continuously with minimal maintenance while providing real-time insights into transit performance.

For additional support or questions, please refer to the project documentation or contact the development team.
