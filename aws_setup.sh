#!/bin/bash
# AWS EC2 Automated Setup Script for MBTA Dashboard
# Run this script on your EC2 instance after connecting via SSH

set -e

echo "MBTA Dashboard - AWS EC2 Setup"
echo "=============================="

# Check if running as ec2-user
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root"
   exit 1
fi

# Configuration
APP_DIR="/opt/mbta-pipeline"
DB_PASSWORD="mbta_secure_password_$(date +%s)"

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

# Update system packages
print_status "Updating system packages..."
sudo yum update -y

# Install required packages
print_status "Installing required packages..."
sudo yum install -y git python3 python3-pip postgresql postgresql-server postgresql-contrib nginx firewalld

# Setup PostgreSQL
print_status "Setting up PostgreSQL..."
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database user and database
print_status "Creating database user and database..."
sudo -u postgres psql -c "CREATE USER mbta_user WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE mbta_data OWNER mbta_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mbta_data TO mbta_user;"

# Configure PostgreSQL for external connections
print_status "Configuring PostgreSQL..."
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /var/lib/pgsql/data/postgresql.conf
echo "host    all             all             0.0.0.0/0               md5" | sudo tee -a /var/lib/pgsql/data/pg_hba.conf
sudo systemctl restart postgresql

# Clone application
print_status "Cloning application..."
cd /opt
sudo git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git mbta-pipeline
sudo chown -R ec2-user:ec2-user mbta-pipeline
cd mbta-pipeline

# Setup Python environment
print_status "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements_streamlit.txt

# Create environment file
print_status "Creating environment configuration..."
cp config.env.example .env

# Update .env with actual values
sed -i "s/your_secure_password_here/$DB_PASSWORD/g" .env
sed -i "s/YOUR_USERNAME\/YOUR_REPO/YOUR_ACTUAL_REPO/g" .env

print_status "Environment file created. Please edit .env with your MBTA API key:"
echo "MBTA_API_KEY=49ecfaf9e4034bb6a28df03836429f6e"
echo ""

# Create system services
print_status "Creating system services..."

# Pipeline service
sudo tee /etc/systemd/system/mbta-pipeline.service > /dev/null <<EOF
[Unit]
Description=MBTA Data Pipeline
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=ec2-user
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python start_pipeline.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Dashboard service
sudo tee /etc/systemd/system/mbta-dashboard.service > /dev/null <<EOF
[Unit]
Description=MBTA Streamlit Dashboard
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=ec2-user
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/streamlit run streamlit_dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
print_status "Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable mbta-pipeline
sudo systemctl enable mbta-dashboard

# Configure Nginx
print_status "Configuring Nginx..."
sudo tee /etc/nginx/conf.d/mbta-dashboard.conf > /dev/null <<EOF
server {
    listen 80;
    server_name _;

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

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Configure firewall
print_status "Configuring firewall..."
sudo systemctl start firewalld
sudo systemctl enable firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload

# Create health check script
print_status "Creating health check script..."
cat > $APP_DIR/health_check.sh << 'EOF'
#!/bin/bash
PIPELINE_STATUS=$(systemctl is-active mbta-pipeline)
DASHBOARD_STATUS=$(systemctl is-active mbta-dashboard)
DB_STATUS=$(systemctl is-active postgresql)

echo "Pipeline: $PIPELINE_STATUS"
echo "Dashboard: $DASHBOARD_STATUS"
echo "Database: $DB_STATUS"

if [ "$PIPELINE_STATUS" = "active" ] && [ "$DASHBOARD_STATUS" = "active" ] && [ "$DB_STATUS" = "active" ]; then
    echo "All services are running"
    exit 0
else
    echo "Some services are not running"
    exit 1
fi
EOF

chmod +x $APP_DIR/health_check.sh

# Get instance public IP
INSTANCE_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

print_status "Setup completed successfully!"
echo ""
echo "IMPORTANT: Before starting services, please:"
echo "1. Edit .env file with your MBTA API key:"
echo "   nano .env"
echo ""
echo "2. Update the git repository URL in the cloned directory"
echo "3. Start the services:"
echo "   sudo systemctl start mbta-pipeline"
echo "   sudo systemctl start mbta-dashboard"
echo ""
echo "Your dashboard will be available at:"
echo "http://$INSTANCE_IP"
echo ""
echo "Database password: $DB_PASSWORD"
echo "Save this password securely!"
echo ""
echo "Health check: $APP_DIR/health_check.sh"
echo "Service status: sudo systemctl status mbta-pipeline mbta-dashboard nginx"
