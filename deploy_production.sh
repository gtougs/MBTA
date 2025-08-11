#!/bin/bash
# Production Deployment Script for MBTA Data Pipeline
# This script sets up the pipeline for continuous data collection in production

set -e

echo "MBTA Data Pipeline - Production Deployment"
echo "=========================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root"
   exit 1
fi

# Configuration
PIPELINE_USER="mbta"
PIPELINE_DIR="/opt/mbta-pipeline"
SERVICE_NAME="mbta-pipeline"
DASHBOARD_SERVICE_NAME="mbta-dashboard"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3.8+ is required but not installed"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ $(echo "$PYTHON_VERSION >= 3.8" | bc -l) -eq 0 ]]; then
        print_error "Python 3.8+ is required, found $PYTHON_VERSION"
        exit 1
    fi
    
    # Check if PostgreSQL is running
    if ! systemctl is-active --quiet postgresql; then
        print_warning "PostgreSQL is not running. Please start it first."
        print_status "You can start it with: sudo systemctl start postgresql"
    fi
    
    print_status "System requirements check completed"
}

# Create pipeline user
create_user() {
    print_status "Creating pipeline user..."
    
    if id "$PIPELINE_USER" &>/dev/null; then
        print_status "User $PIPELINE_USER already exists"
    else
        sudo useradd -r -s /bin/bash -d $PIPELINE_DIR $PIPELINE_USER
        print_status "User $PIPELINE_USER created"
    fi
}

# Install system dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    # Update package list
    sudo apt-get update
    
    # Install required packages
    sudo apt-get install -y \
        python3-pip \
        python3-venv \
        postgresql-client \
        nginx \
        supervisor \
        curl \
        git
}

# Setup Python environment
setup_python_env() {
    print_status "Setting up Python environment..."
    
    # Create virtual environment
    sudo -u $PIPELINE_USER python3 -m venv $PIPELINE_DIR/venv
    
    # Activate virtual environment and install requirements
    sudo -u $PIPELINE_USER $PIPELINE_DIR/venv/bin/pip install --upgrade pip
    sudo -u $PIPELINE_USER $PIPELINE_DIR/venv/bin/pip install -r $PIPELINE_DIR/requirements.txt
}

# Create systemd service for pipeline
create_pipeline_service() {
    print_status "Creating systemd service for data pipeline..."
    
    cat << EOF | sudo tee /etc/systemd/system/$SERVICE_NAME.service
[Unit]
Description=MBTA Data Pipeline
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$PIPELINE_USER
WorkingDirectory=$PIPELINE_DIR
Environment=PATH=$PIPELINE_DIR/venv/bin
ExecStart=$PIPELINE_DIR/venv/bin/python start_pipeline.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
    print_status "Pipeline service created and enabled"
}

# Create systemd service for dashboard
create_dashboard_service() {
    print_status "Creating systemd service for dashboard..."
    
    cat << EOF | sudo tee /etc/systemd/system/$DASHBOARD_SERVICE_NAME.service
[Unit]
Description=MBTA Dashboard
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$PIPELINE_USER
WorkingDirectory=$PIPELINE_DIR
Environment=PATH=$PIPELINE_DIR/venv/bin
ExecStart=$PIPELINE_DIR/venv/bin/python start_dashboard.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable $DASHBOARD_SERVICE_NAME
    print_status "Dashboard service created and enabled"
}

# Setup logging
setup_logging() {
    print_status "Setting up logging..."
    
    # Create log directory
    sudo mkdir -p /var/log/mbta-pipeline
    sudo chown $PIPELINE_USER:$PIPELINE_USER /var/log/mbta-pipeline
    
    # Create logrotate configuration
    cat << EOF | sudo tee /etc/logrotate.d/mbta-pipeline
/var/log/mbta-pipeline/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $PIPELINE_USER $PIPELINE_USER
    postrotate
        systemctl reload $SERVICE_NAME
        systemctl reload $DASHBOARD_SERVICE_NAME
    endscript
}
EOF
}

# Setup monitoring
setup_monitoring() {
    print_status "Setting up basic monitoring..."
    
    # Create health check script
    cat << 'EOF' | sudo tee $PIPELINE_DIR/health_check.sh
#!/bin/bash
# Health check script for MBTA Pipeline

PIPELINE_STATUS=$(systemctl is-active mbta-pipeline)
DASHBOARD_STATUS=$(systemctl is-active mbta-dashboard)
DB_STATUS=$(systemctl is-active postgresql)

echo "Pipeline Status: $PIPELINE_STATUS"
echo "Dashboard Status: $DASHBOARD_STATUS"
echo "Database Status: $DB_STATUS"

if [ "$PIPELINE_STATUS" = "active" ] && [ "$DASHBOARD_STATUS" = "active" ] && [ "$DB_STATUS" = "active" ]; then
    exit 0
else
    exit 1
fi
EOF

    sudo chmod +x $PIPELINE_DIR/health_check.sh
    sudo chown $PIPELINE_USER:$PIPELINE_USER $PIPELINE_DIR/health_check.sh
}

# Main deployment function
main() {
    echo "Starting production deployment..."
    
    check_requirements
    create_user
    install_dependencies
    setup_python_env
    create_pipeline_service
    create_dashboard_service
    setup_logging
    setup_monitoring
    
    print_status "Production deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Copy your .env file to $PIPELINE_DIR/"
    echo "2. Start the services:"
    echo "   sudo systemctl start $SERVICE_NAME"
    echo "   sudo systemctl start $DASHBOARD_SERVICE_NAME"
    echo "3. Check status:"
    echo "   sudo systemctl status $SERVICE_NAME"
    echo "   sudo systemctl status $DASHBOARD_SERVICE_NAME"
    echo "4. View logs:"
    echo "   sudo journalctl -u $SERVICE_NAME -f"
    echo "   sudo journalctl -u $DASHBOARD_SERVICE_NAME -f"
}

# Run main function
main "$@"
