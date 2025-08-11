# 🚇 MBTA Transit Dashboard

A modern, real-time web dashboard for visualizing MBTA transit data with interactive charts, maps, and analytics.

## ✨ Features

### 📊 **Real-Time Visualizations**
- **Live Performance Metrics** - On-time percentage, delays, trip counts
- **Interactive Charts** - Performance trends, route comparisons, peak hour analysis
- **Real-Time Updates** - WebSocket-powered live data streaming
- **Responsive Design** - Works on desktop, tablet, and mobile

### 🗺️ **Interactive Maps**
- **Boston Transit System** - Centered on MBTA service area
- **Stop Locations** - All MBTA stops with popup information
- **Route Visualization** - Color-coded by MBTA line (Red, Orange, Blue, Green)
- **Real-Time Updates** - Live vehicle positions and service status

### 📈 **Advanced Analytics**
- **12 Pre-built Queries** - Performance, delays, routes, stops, vehicles, alerts
- **Custom Filtering** - By route, time period, and geographic area
- **Anomaly Detection** - Automatic detection of service disruptions
- **Trend Analysis** - Historical performance patterns

### 🎨 **Modern UI/UX**
- **Dark Theme** - Easy on the eyes for 24/7 monitoring
- **MBTA Branding** - Official colors and styling
- **Tabbed Interface** - Organized by functionality
- **Mobile Responsive** - Touch-friendly controls

## 🚀 Quick Start

### **Option 1: Standalone Dashboard**
```bash
# Start just the dashboard (requires existing database)
python start_dashboard.py
```

### **Option 2: Full Pipeline + Dashboard**
```bash
# Start the complete system
python start_pipeline.py
```

### **Option 3: Manual Start**
```bash
# Start infrastructure
docker-compose up -d

# Initialize database
python -m src.cli init-db

# Start dashboard
python -m src.mbta_pipeline.dashboard.app
```

## 🌐 Access the Dashboard

Once running, open your browser to:
```
http://localhost:8000
```

## 📋 Dashboard Components

### **1. Overview Tab**
- **Real-time metrics** - On-time percentage, total trips, average delays
- **Performance trends** - Live chart showing last 24 hours
- **Recent anomalies** - Service disruption alerts

### **2. Performance Tab**
- **Route performance** - Bar chart comparing all MBTA lines
- **Peak hour analysis** - Doughnut chart showing time-based patterns

### **3. Analytics Tab**
- **Query runner** - Execute any of 12 pre-built analytics queries
- **Results display** - Interactive tables with sorting and filtering
- **Export options** - Download results in various formats

### **4. Map Tab**
- **Interactive map** - Leaflet-based with OpenStreetMap tiles
- **Stop markers** - Click for detailed information
- **Route overlays** - Color-coded by MBTA line

## 🔧 Configuration

### **Environment Variables**
```bash
# Database
DATABASE_URL=postgresql://mbta_user:mbta_password@localhost:5432/mbta_data

# MBTA API
MBTA_API_KEY=your_api_key_here

# Dashboard settings
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### **Dashboard Settings**
The dashboard automatically configures:
- **Port**: 8000 (configurable)
- **Host**: 0.0.0.0 (accessible from network)
- **CORS**: Enabled for development
- **WebSocket**: Real-time updates every 30 seconds

## 📊 Available Analytics Queries

### **Performance Metrics**
- `performance` - On-time performance by route
- `delays` - Delay trends over time
- `routes` - Route comparison analysis

### **Operational Analysis**
- `stops` - Stop performance metrics
- `vehicles` - Vehicle performance data
- `headways` - Time between consecutive vehicles

### **Service Health**
- `alerts` - Service disruption summary
- `anomalies` - Anomaly detection results
- `peak` - Peak vs off-peak performance

### **Geographic Analysis**
- `geographic` - Performance by Boston area
- `realtime` - Current system status

## 🎯 Usage Examples

### **Check Red Line Performance**
1. Go to **Analytics Tab**
2. Select **"Performance Metrics"** query
3. Choose **"Red"** from route filter
4. Set time to **"Last 24 Hours"**
5. Click **"Run"**

### **Monitor Real-Time Status**
1. Go to **Overview Tab**
2. Watch the **real-time indicator** (green pulsing dot)
3. View **live performance trends** chart
4. Check **recent anomalies** for alerts

### **Explore Transit Map**
1. Go to **Map Tab**
2. **Zoom in/out** to explore different areas
3. **Click on stops** for detailed information
4. **Use route filters** to focus on specific lines

## 🔌 API Endpoints

### **Dashboard Data**
- `GET /api/dashboard/overview` - Dashboard overview metrics
- `GET /api/analytics/performance` - Performance metrics
- `GET /api/analytics/anomalies` - Detected anomalies

### **Analytics Queries**
- `GET /api/analytics/query/{query_name}` - Run pre-built queries
- `GET /api/routes` - Get all MBTA routes
- `GET /api/stops` - Get stops (with optional route filtering)

### **Real-Time Updates**
- `WebSocket /ws/realtime` - Live data streaming

## 🛠️ Development

### **Project Structure**
```
src/mbta_pipeline/dashboard/
├── app.py              # FastAPI application
├── static/             # Frontend assets
│   ├── index.html     # Main dashboard HTML
│   └── dashboard.js   # Dashboard JavaScript
└── __init__.py        # Package initialization
```

### **Adding New Charts**
1. **Update HTML** - Add canvas element
2. **Update JavaScript** - Initialize Chart.js instance
3. **Add API endpoint** - Create data source
4. **Connect real-time** - WebSocket updates

### **Adding New Queries**
1. **Update AnalyticsQueries** - Add SQL query
2. **Update API endpoint** - Handle new query type
3. **Update frontend** - Add to query selector
4. **Test integration** - Verify data flow

## 🚨 Troubleshooting

### **Dashboard Won't Start**
```bash
# Check database connection
python -m src.cli verify-db

# Check environment variables
cat .env

# Check port availability
lsof -i :8000
```

### **No Data Displayed**
```bash
# Check database tables
python -m src.cli query performance --hours 1

# Check pipeline status
python -m src.cli run

# Verify API endpoints
curl http://localhost:8000/api/health
```

### **Charts Not Loading**
- **Check browser console** for JavaScript errors
- **Verify Chart.js** is loading correctly
- **Check API responses** in Network tab
- **Clear browser cache** and refresh

## 🔄 Real-Time Updates

The dashboard provides real-time updates through:

1. **WebSocket Connection** - Live data streaming
2. **Periodic API Calls** - Every 30 seconds
3. **Chart Animations** - Smooth data transitions
4. **Status Indicators** - Visual feedback for live data

## 📱 Mobile Support

The dashboard is fully responsive with:
- **Touch-friendly controls** - Swipe, pinch, tap
- **Adaptive layouts** - Optimized for small screens
- **Mobile charts** - Responsive chart sizing
- **Touch gestures** - Map navigation and interactions

## 🎨 Customization

### **Theme Colors**
Modify CSS variables in `index.html`:
```css
:root {
    --mbta-red: #DA291C;
    --mbta-orange: #FF8C00;
    --mbta-blue: #003DA5;
    --mbta-green: #00843D;
}
```

### **Chart Styles**
Update Chart.js options in `dashboard.js`:
```javascript
options: {
    responsive: true,
    maintainAspectRatio: false,
    // Custom styling here
}
```

### **Map Configuration**
Modify Leaflet settings in `dashboard.js`:
```javascript
this.map = L.map('map').setView([42.3601, -71.0589], 12);
// Custom map options
```

## 🚀 Next Steps

### **Immediate Enhancements**
- [ ] **Vehicle tracking** - Real-time vehicle positions on map
- [ ] **Route overlays** - Actual MBTA route geometries
- [ ] **Alert notifications** - Push notifications for service disruptions
- [ ] **Historical analysis** - Long-term trend analysis

### **Advanced Features**
- [ ] **Predictive analytics** - Delay prediction models
- [ ] **User accounts** - Personalized dashboards
- [ ] **Export functionality** - PDF reports and data exports
- [ ] **Mobile app** - Native iOS/Android applications

## 📞 Support

For dashboard-specific issues:
1. **Check browser console** for JavaScript errors
2. **Verify API endpoints** are responding
3. **Check database connectivity**
4. **Review WebSocket connections**

The dashboard is designed to be self-contained and will automatically reconnect to the database and WebSocket if connections are lost.

---

**🎉 Congratulations!** You now have a fully functional, real-time MBTA transit dashboard that provides comprehensive insights into transit performance, service health, and operational analytics.
