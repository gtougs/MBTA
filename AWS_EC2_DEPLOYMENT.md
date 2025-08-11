# AWS EC2 Deployment Guide for MBTA Transit Dashboard

## 🚀 **Quick Start: AWS EC2 Free Tier**

### **Prerequisites**
- AWS account with credit card verification
- Basic familiarity with AWS console
- Your MBTA API key ready

### **Step 1: Launch EC2 Instance**

#### **1.1 Navigate to EC2 Console**
- Go to [AWS Console](https://console.aws.amazon.com)
- Search for "EC2" and click on it
- Click "Launch Instance"

#### **1.2 Configure Instance Details**
```
Name: mbta-dashboard
AMI: Amazon Linux 2023 (Free tier eligible)
Instance type: t2.micro (Free tier eligible)
Key pair: Create new key pair (download the .pem file)
Network settings: Allow HTTP/HTTPS traffic from internet
Storage: 20 GB gp3 (Free tier eligible)
```

#### **1.3 Security Group Configuration**
```
Type: SSH
Protocol: TCP
Port: 22
Source: My IP (for security)

Type: HTTP
Protocol: TCP
Port: 80
Source: 0.0.0.0/0

Type: Custom TCP
Protocol: TCP
Port: 8501
Source: 0.0.0.0/0 (for Streamlit dashboard)
```

### **Step 2: Connect to Your Instance**

#### **2.1 Download Key Pair**
- Download the .pem file when prompted
- Store it securely (e.g., `~/Downloads/mbta-dashboard.pem`)

#### **2.2 Connect via SSH**
```bash
# Make key file secure
chmod 400 ~/Downloads/mbta-dashboard.pem

# Connect to your instance (replace with your actual IP)
ssh -i ~/Downloads/mbta-dashboard.pem ec2-user@YOUR_INSTANCE_PUBLIC_IP
```

### **Step 3: Server Setup**

#### **3.1 Update System**
```bash
# For Amazon Linux 2023 (use dnf instead of yum)
sudo dnf update -y
sudo dnf install -y git python3 python3-pip postgresql postgresql-server postgresql-contrib nginx

# Alternative: If dnf doesn't work, try yum (for older Amazon Linux)
# sudo yum update -y
# sudo yum install -y git python3 python3-pip postgresql postgresql-server postgresql-contrib nginx
```

#### **3.2 Setup PostgreSQL**
```bash
# Initialize PostgreSQL
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database user
sudo -u postgres psql
CREATE USER mbta_user WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE mbta_data OWNER mbta_user;
GRANT ALL PRIVILEGES ON DATABASE mbta_data TO mbta_user;
\q

# Configure PostgreSQL for external connections
sudo nano /var/lib/pgsql/data/postgresql.conf
# Add/modify: listen_addresses = '*'

sudo nano /var/lib/pgsql/data/pg_hba.conf
# Add: host    all             all             0.0.0.0/0               md5

sudo systemctl restart postgresql
```

#### **3.2.1 PostgreSQL Troubleshooting**
If PostgreSQL commands are not found, try these steps:

```bash
# Check if PostgreSQL is installed
rpm -qa | grep postgresql

# Check PostgreSQL service status
sudo systemctl status postgresql

# Find PostgreSQL binaries
find /usr -name "psql" 2>/dev/null
find /usr -name "postgresql-setup" 2>/dev/null

# Check PATH
echo $PATH

# If binaries exist but not in PATH, add them
export PATH=$PATH:/usr/bin:/usr/local/bin
echo 'export PATH=$PATH:/usr/bin:/usr/local/bin' >> ~/.bashrc

# Alternative: Use full paths
sudo /usr/bin/postgresql-setup initdb
sudo /usr/bin/systemctl start postgresql
sudo /usr/bin/systemctl enable postgresql

# Check if service exists
sudo systemctl list-unit-files | grep postgresql
```

#### **3.3 Clone Application**
```bash
cd /opt
sudo git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git mbta-pipeline
sudo chown -R ec2-user:ec2-user mbta-pipeline
cd mbta-pipeline
```

#### **3.4 Setup Python Environment**
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements_streamlit.txt
```

### **Step 4: Configuration**

#### **4.1 Create Environment File**
```bash
cp config.env.example .env
nano .env
```

#### **4.2 Update .env with Your Values**
```bash
# MBTA API Configuration
MBTA_API_KEY=49ecfaf9e4034bb6a28df03836429f6e

# Database Configuration (use your instance's private IP)
DATABASE_URL=postgresql://mbta_user:your_secure_password_here@localhost:5432/mbta_data
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Application Configuration
LOG_LEVEL=INFO
POLLING_INTERVAL_SECONDS=15
BATCH_SIZE=50
MAX_RETRIES=3
RETRY_DELAY_SECONDS=5

# Production Settings
DEBUG=false
ENVIRONMENT=production
```

### **Step 5: Create System Services**

#### **5.1 Pipeline Service**
```bash
sudo tee /etc/systemd/system/mbta-pipeline.service > /dev/null <<EOF
[Unit]
Description=MBTA Data Pipeline
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=ec2-user
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

#### **5.2 Dashboard Service**
```bash
sudo tee /etc/systemd/system/mbta-dashboard.service > /dev/null <<EOF
[Unit]
Description=MBTA Streamlit Dashboard
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/mbta-pipeline
Environment=PATH=/opt/mbta-pipeline/venv/bin
ExecStart=/opt/mbta-pipeline/venv/bin/streamlit run streamlit_dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### **5.3 Enable and Start Services**
```bash
sudo systemctl daemon-reload
sudo systemctl enable mbta-pipeline
sudo systemctl enable mbta-dashboard
sudo systemctl start mbta-pipeline
sudo systemctl start mbta-dashboard
```

### **Step 6: Nginx Configuration**

#### **6.1 Create Nginx Site Config**
```bash
sudo tee /etc/nginx/conf.d/mbta-dashboard.conf > /dev/null <<EOF
server {
    listen 80;
    server_name _;  # Accept any hostname

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

#### **6.2 Start Nginx**
```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

### **Step 7: Test Your Deployment**

#### **7.1 Check Services**
```bash
sudo systemctl status mbta-pipeline
sudo systemctl status mbta-dashboard
sudo systemctl status nginx
```

#### **7.2 Test Dashboard**
- Open your browser and go to: `http://YOUR_INSTANCE_PUBLIC_IP`
- You should see the MBTA dashboard!

#### **7.3 Check Logs**
```bash
# Pipeline logs
sudo journalctl -u mbta-pipeline -f

# Dashboard logs
sudo journalctl -u mbta-dashboard -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
```

### **Step 8: Security & Monitoring**

#### **8.1 Setup Firewall**
```bash
# Allow only necessary ports
sudo dnf install -y firewalld
sudo systemctl start firewalld
sudo systemctl enable firewalld

sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload
```

#### **8.2 Health Check Script**
```bash
cat > /opt/mbta-pipeline/health_check.sh << 'EOF'
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

chmod +x /opt/mbta-pipeline/health_check.sh
```

### **Step 9: Website Integration**

#### **9.1 Get Your Dashboard URL**
Your dashboard will be available at:
```
http://YOUR_INSTANCE_PUBLIC_IP
```

#### **9.2 Embed in Your Website**
```html
<!-- Option 1: Direct iframe embedding -->
<iframe 
    src="http://YOUR_INSTANCE_PUBLIC_IP" 
    width="100%" 
    height="800px" 
    frameborder="0">
</iframe>

<!-- Option 2: Link to dashboard -->
<a href="http://YOUR_INSTANCE_PUBLIC_IP" target="_blank">
    View MBTA Transit Analytics
</a>
```

### **Step 10: Maintenance**

#### **10.1 Regular Updates**
```bash
# Update system packages
sudo dnf update -y

# Update application
cd /opt/mbta-pipeline
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements_streamlit.txt

# Restart services
sudo systemctl restart mbta-pipeline
sudo systemctl restart mbta-dashboard
```

#### **10.2 Monitor Resources**
```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check running processes
htop
```

## 🎯 **Cost Breakdown (Free Tier)**

### **First 12 Months: FREE**
- EC2 t2.micro: $0/month
- Storage (20GB): $0/month
- Data transfer: $0/month (15GB included)

### **After 12 Months: ~$10-15/month**
- EC2 t2.micro: ~$8-10/month
- Storage: ~$2-3/month
- Data transfer: ~$1-2/month

## 🚨 **Important Notes**

1. **Free Tier Limits**: 750 hours/month = 31.25 days (perfect for continuous operation)
2. **Instance Type**: t2.micro has 1GB RAM - sufficient for your dashboard
3. **Storage**: 20GB is enough for several months of transit data
4. **Backup**: Consider setting up automated backups after free tier expires

## 🔧 **Troubleshooting**

### **Common Issues**
- **Can't connect via SSH**: Check security group and key file permissions
- **Dashboard not loading**: Check service status and firewall settings
- **Database connection failed**: Verify PostgreSQL configuration and credentials

### **Get Help**
- Check service logs: `sudo journalctl -u service-name -f`
- Verify network connectivity: `curl -I http://localhost:8501`
- Test database: `psql -h localhost -U mbta_user -d mbta_data`

## 🎉 **You're Ready!**

Once you complete these steps, you'll have:
✅ **Professional MBTA dashboard** running 24/7  
✅ **Continuous data collection** from MBTA APIs  
✅ **Public URL** for website embedding  
✅ **Production-grade** infrastructure  
✅ **Free hosting** for 12 months!  

**Next step**: Launch your EC2 instance and follow this guide step by step!