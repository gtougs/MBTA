/**
 * MBTA Transit Dashboard JavaScript
 * Handles real-time updates, charts, maps, and analytics
 */

class MBTADashboard {
    constructor() {
        this.charts = {};
        this.map = null;
        this.websocket = null;
        this.updateInterval = null;
        this.routes = [];
        this.stops = [];
        
        this.init();
    }
    
    async init() {
        console.log('Initializing MBTA Dashboard...');
        
        // Initialize components
        await this.loadRoutes();
        await this.loadStops();
        this.initCharts();
        this.initMap();
        this.initWebSocket();
        this.initEventListeners();
        
        // Load initial data
        await this.loadDashboardData();
        await this.loadPerformanceData();
        await this.loadAnomalies();
        
        // Start periodic updates
        this.startPeriodicUpdates();
        
        console.log('Dashboard initialized successfully');
    }
    
    async loadRoutes() {
        try {
            const response = await fetch('/api/routes');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.routes = data.data;
                
                // Populate route filter
                const routeFilter = document.getElementById('route-filter');
                routeFilter.innerHTML = '<option value="">All Routes</option>';
                
                this.routes.forEach(route => {
                    const option = document.createElement('option');
                    option.value = route.id;
                    option.textContent = route.name;
                    routeFilter.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading routes:', error);
        }
    }
    
    async loadStops() {
        try {
            const response = await fetch('/api/stops');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.stops = data.data;
            }
        } catch (error) {
            console.error('Error loading stops:', error);
        }
    }
    
    initCharts() {
        // Performance Trends Chart
        const performanceCtx = document.getElementById('performanceChart');
        if (performanceCtx) {
            this.charts.performance = new Chart(performanceCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'On-Time Percentage',
                        data: [],
                        borderColor: '#DA291C',
                        backgroundColor: 'rgba(218, 41, 28, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Average Delay (min)',
                        data: [],
                        borderColor: '#FF8C00',
                        backgroundColor: 'rgba(255, 140, 0, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: 'On-Time %'
                            }
                        },
                        y1: {
                            position: 'right',
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Delay (min)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#ffffff'
                            }
                        }
                    }
                }
            });
        }
        
        // Route Performance Chart
        const routeCtx = document.getElementById('routePerformanceChart');
        if (routeCtx) {
            this.charts.routePerformance = new Chart(routeCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'On-Time Percentage',
                        data: [],
                        backgroundColor: [
                            '#DA291C', '#FF8C00', '#003DA5', '#00843D',
                            '#6f42c1', '#e83e8c', '#fd7e14', '#20c997'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: 'On-Time %'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }
        
        // Peak Hour Chart
        const peakCtx = document.getElementById('peakHourChart');
        if (peakCtx) {
            this.charts.peakHour = new Chart(peakCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Morning Peak', 'Midday', 'Evening Peak', 'Evening', 'Late Night'],
                    datasets: [{
                        data: [],
                        backgroundColor: [
                            '#DA291C', '#FF8C00', '#003DA5', '#00843D', '#6f42c1'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: '#ffffff'
                            }
                        }
                    }
                }
            });
        }
    }
    
    initMap() {
        const mapContainer = document.getElementById('map');
        if (!mapContainer) return;
        
        // Initialize Leaflet map centered on Boston
        this.map = L.map('map').setView([42.3601, -71.0589], 12);
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
        
        // Add MBTA route overlays (placeholder for now)
        this.addRouteOverlays();
    }
    
    addRouteOverlays() {
        // This would be populated with actual MBTA route data
        // For now, we'll add some sample markers
        if (this.stops.length > 0) {
            this.stops.slice(0, 20).forEach(stop => {
                if (stop.latitude && stop.longitude) {
                    const marker = L.marker([stop.latitude, stop.longitude])
                        .addTo(this.map)
                        .bindPopup(`<b>${stop.name}</b><br>Stop ID: ${stop.id}`);
                }
            });
        }
    }
    
    initWebSocket() {
        try {
            this.websocket = new WebSocket(`ws://${window.location.host}/ws/realtime`);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'realtime_update') {
                        this.handleRealtimeUpdate(data.data);
                    }
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                // Try to reconnect after 5 seconds
                setTimeout(() => this.initWebSocket(), 5000);
            };
            
        } catch (error) {
            console.error('Error initializing WebSocket:', error);
        }
    }
    
    initEventListeners() {
        // Run query button
        const runQueryBtn = document.getElementById('run-query');
        if (runQueryBtn) {
            runQueryBtn.addEventListener('click', () => this.runAnalyticsQuery());
        }
        
        // Tab change events
        const tabs = document.querySelectorAll('[data-bs-toggle="tab"]');
        tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', (event) => {
                this.handleTabChange(event.target.id);
            });
        });
    }
    
    async loadDashboardData() {
        try {
            const response = await fetch('/api/dashboard/overview');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.updateDashboardMetrics(data.data);
            }
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }
    
    async loadPerformanceData() {
        try {
            // Load route performance
            const routeResponse = await fetch('/api/analytics/query/routes?hours=24');
            const routeData = await routeResponse.json();
            
            if (routeData.status === 'success' && this.charts.routePerformance) {
                this.updateRoutePerformanceChart(routeData.data);
            }
            
            // Load peak hour analysis
            const peakResponse = await fetch('/api/analytics/query/peak?hours=24');
            const peakData = await peakResponse.json();
            
            if (peakData.status === 'success' && this.charts.peakHour) {
                this.updatePeakHourChart(peakData.data);
            }
            
        } catch (error) {
            console.error('Error loading performance data:', error);
        }
    }
    
    async loadAnomalies() {
        try {
            const response = await fetch('/api/analytics/anomalies?hours=24');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.updateAnomaliesList(data.data);
            }
        } catch (error) {
            console.error('Error loading anomalies:', error);
        }
    }
    
    updateDashboardMetrics(data) {
        const { performance, overview } = data;
        
        // Update metric cards
        document.getElementById('on-time-percentage').textContent = 
            `${performance.on_time_percentage.toFixed(1)}%`;
        
        document.getElementById('total-trips').textContent = 
            performance.total_trips.toLocaleString();
        
        document.getElementById('avg-delay').textContent = 
            performance.average_delay_minutes.toFixed(1);
        
        const statusElement = document.getElementById('service-status');
        statusElement.textContent = overview.overall_status.toUpperCase();
        statusElement.className = `metric-value status-${overview.overall_status}`;
        
        // Update last update time
        document.getElementById('last-update').textContent = 
            `Last update: ${new Date().toLocaleTimeString()}`;
    }
    
    updateRoutePerformanceChart(data) {
        const chart = this.charts.routePerformance;
        if (!chart) return;
        
        const labels = data.map(row => row.route_name || row.route_id);
        const values = data.map(row => parseFloat(row.on_time_percentage) || 0);
        
        chart.data.labels = labels;
        chart.data.datasets[0].data = values;
        chart.update();
    }
    
    updatePeakHourChart(data) {
        const chart = this.charts.peakHour;
        if (!chart) return;
        
        const values = data.map(row => parseInt(row.total_predictions) || 0);
        
        chart.data.datasets[0].data = values;
        chart.update();
    }
    
    updateAnomaliesList(anomalies) {
        const container = document.getElementById('anomalies-list');
        if (!container) return;
        
        if (anomalies.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">No anomalies detected</div>';
            return;
        }
        
        const anomaliesHtml = anomalies.map(anomaly => `
            <div class="mb-3 p-3 border border-warning rounded">
                <div class="d-flex justify-content-between align-items-start">
                    <strong class="text-warning">${anomaly.type}</strong>
                    <span class="badge bg-${anomaly.severity === 'high' ? 'danger' : 'warning'}">${anomaly.severity}</span>
                </div>
                <div class="mt-2">${anomaly.description}</div>
                <div class="mt-2 small text-muted">
                    Confidence: ${(anomaly.confidence_score * 100).toFixed(0)}%
                </div>
            </div>
        `).join('');
        
        container.innerHTML = anomaliesHtml;
    }
    
    async runAnalyticsQuery() {
        const queryType = document.getElementById('query-selector').value;
        const routeFilter = document.getElementById('route-filter').value;
        const timeFilter = document.getElementById('time-filter').value;
        
        const resultsContainer = document.getElementById('query-results');
        resultsContainer.innerHTML = '<div class="loading">Running query...</div>';
        
        try {
            let url = `/api/analytics/query/${queryType}?hours=${timeFilter}`;
            if (routeFilter) {
                url += `&route_id=${routeFilter}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.status === 'success') {
                this.displayQueryResults(data);
            } else {
                resultsContainer.innerHTML = `<div class="error">Error: ${data.detail || 'Unknown error'}</div>`;
            }
        } catch (error) {
            console.error('Error running query:', error);
            resultsContainer.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        }
    }
    
    displayQueryResults(data) {
        const container = document.getElementById('query-results');
        
        if (!data.data || data.data.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">No data returned</div>';
            return;
        }
        
        // Create table
        const columns = Object.keys(data.data[0]);
        const tableHtml = `
            <div class="table-responsive">
                <table class="table table-dark table-striped">
                    <thead>
                        <tr>
                            ${columns.map(col => `<th>${col.replace(/_/g, ' ').toUpperCase()}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${data.data.map(row => `
                            <tr>
                                ${columns.map(col => `<td>${row[col] || ''}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            <div class="mt-3 text-muted">
                Showing ${data.data.length} of ${data.row_count} total rows
            </div>
        `;
        
        container.innerHTML = tableHtml;
    }
    
    handleRealtimeUpdate(data) {
        // Update performance chart with new data
        if (this.charts.performance) {
            const now = new Date();
            const timeLabel = now.toLocaleTimeString();
            
            // Add new data point (limit to last 24 points)
            const chart = this.charts.performance;
            chart.data.labels.push(timeLabel);
            chart.data.datasets[0].data.push(data.performance.on_time_percentage);
            chart.data.datasets[1].data.push(data.performance.average_delay_minutes);
            
            // Remove old data points if we have more than 24
            if (chart.data.labels.length > 24) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
                chart.data.datasets[1].data.shift();
            }
            
            chart.update('none'); // Update without animation for real-time
        }
        
        // Update dashboard metrics
        this.updateDashboardMetrics({
            performance: data.performance,
            overview: data
        });
    }
    
    handleTabChange(tabId) {
        // Load data specific to the selected tab
        switch (tabId) {
            case 'performance-tab':
                this.loadPerformanceData();
                break;
            case 'map-tab':
                if (this.map) {
                    this.map.invalidateSize();
                }
                break;
        }
    }
    
    startPeriodicUpdates() {
        // Update dashboard data every 30 seconds
        this.updateInterval = setInterval(() => {
            this.loadDashboardData();
        }, 30000);
    }
    
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.websocket) {
            this.websocket.close();
        }
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mbtaDashboard = new MBTADashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.mbtaDashboard) {
        window.mbtaDashboard.destroy();
    }
});
