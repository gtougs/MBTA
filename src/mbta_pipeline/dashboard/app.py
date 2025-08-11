"""MBTA Dashboard - FastAPI application for transit data visualization."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from ..processing.analytics import transit_analytics
from ..processing.analytics_queries import AnalyticsQueries
from ..storage.database import DatabaseManager
from ..config.settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return
        
        # Remove disconnected clients
        self.active_connections = [
            conn for conn in self.active_connections 
            if not conn.client_state.disconnected
        ]
        
        # Broadcast to remaining clients
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                # Remove failed connection
                self.active_connections.remove(connection)


# Global connection manager
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting MBTA Dashboard...")
    
    # Start background task for real-time updates
    asyncio.create_task(broadcast_realtime_data())
    
    yield
    
    # Shutdown
    logger.info("Shutting down MBTA Dashboard...")


# Create FastAPI app
app = FastAPI(
    title="MBTA Transit Dashboard",
    description="Real-time visualization and analytics for MBTA transit data",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount static files
app.mount("/static", StaticFiles(directory="src/mbta_pipeline/dashboard/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Serve the main dashboard HTML."""
    with open("src/mbta_pipeline/dashboard/static/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "MBTA Dashboard"
    }


@app.get("/api/dashboard/overview")
async def get_dashboard_overview():
    """Get dashboard overview data."""
    try:
        # Get real-time summary
        summary = await transit_analytics.generate_service_summary(
            time_window=timedelta(hours=1)
        )
        
        # Get recent performance metrics
        performance = await transit_analytics.analyze_performance(
            time_window=timedelta(hours=1)
        )
        
        return {
            "status": "success",
            "data": {
                "overview": summary,
                "performance": {
                    "on_time_percentage": performance.on_time_percentage,
                    "average_delay_minutes": performance.average_delay / 60,
                    "total_trips": performance.total_trips,
                    "delayed_trips": performance.delayed_trips
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/performance")
async def get_performance_metrics(
    hours: int = 24,
    route_id: Optional[str] = None
):
    """Get performance metrics."""
    try:
        metrics = await transit_analytics.analyze_performance(
            route_id=route_id,
            time_window=timedelta(hours=hours)
        )
        
        return {
            "status": "success",
            "data": {
                "on_time_percentage": metrics.on_time_percentage,
                "average_delay": metrics.average_delay,
                "delay_std_dev": metrics.delay_std_dev,
                "total_trips": metrics.total_trips,
                "delayed_trips": metrics.delayed_trips,
                "severely_delayed_trips": metrics.severely_delayed_trips,
                "timestamp": metrics.timestamp.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/anomalies")
async def get_anomalies(hours: int = 24):
    """Get detected anomalies."""
    try:
        anomalies = await transit_analytics.detect_anomalies(
            time_window=timedelta(hours=hours)
        )
        
        return {
            "status": "success",
            "data": [
                {
                    "type": a.anomaly_type,
                    "severity": a.severity,
                    "description": a.description,
                    "affected_routes": a.affected_routes,
                    "affected_stops": a.affected_stops,
                    "confidence_score": a.confidence_score,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in anomalies
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/query/{query_name}")
async def run_analytics_query(
    query_name: str,
    hours: int = 24,
    route_id: Optional[str] = None
):
    """Run pre-built analytics queries."""
    try:
        db_manager = DatabaseManager()
        session = db_manager.get_session()
        
        try:
            # Get the SQL query
            if query_name == 'performance':
                sql = AnalyticsQueries.get_performance_metrics(hours, route_id)
            elif query_name == 'delays':
                sql = AnalyticsQueries.get_delay_trends(hours, route_id)
            elif query_name == 'routes':
                sql = AnalyticsQueries.get_route_comparison(hours)
            elif query_name == 'stops':
                sql = AnalyticsQueries.get_stop_performance(hours, route_id)
            elif query_name == 'vehicles':
                sql = AnalyticsQueries.get_vehicle_performance(hours)
            elif query_name == 'alerts':
                sql = AnalyticsQueries.get_service_alerts_summary(hours)
            elif query_name == 'headways':
                sql = AnalyticsQueries.get_headway_analysis(hours, route_id)
            elif query_name == 'peak':
                sql = AnalyticsQueries.get_peak_hour_analysis(hours)
            elif query_name == 'anomalies':
                sql = AnalyticsQueries.get_anomaly_detection(hours)
            elif query_name == 'realtime':
                sql = AnalyticsQueries.get_realtime_dashboard_data()
            elif query_name == 'geographic':
                sql = AnalyticsQueries.get_geographic_performance(hours)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown query: {query_name}")
            
            # Execute query
            from sqlalchemy import text
            result = session.execute(text(sql))
            rows = result.fetchall()
            
            # Convert to list of dicts
            columns = result.keys()
            data = [
                {str(col): str(val) for col, val in zip(columns, row)}
                for row in rows
            ]
            
            return {
                "status": "success",
                "query": query_name,
                "data": data,
                "row_count": len(data)
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error running query {query_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/routes")
async def get_routes():
    """Get all MBTA routes."""
    try:
        db_manager = DatabaseManager()
        session = db_manager.get_session()
        
        try:
            from ..models.database import Route
            routes = session.query(Route).all()
            
            return {
                "status": "success",
                "data": [
                    {
                        "id": route.id,
                        "name": route.route_name,
                        "type": route.route_type,
                        "color": route.route_color,
                        "text_color": route.route_text_color
                    }
                    for route in routes
                ]
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting routes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stops")
async def get_stops(route_id: Optional[str] = None):
    """Get stops, optionally filtered by route."""
    try:
        db_manager = DatabaseManager()
        session = db_manager.get_session()
        
        try:
            from ..models.database import Stop, Prediction
            
            if route_id:
                # Get stops for specific route
                stops = session.query(Stop)\
                    .join(Prediction, Stop.id == Prediction.stop_id)\
                    .filter(Prediction.route_id == route_id)\
                    .distinct()\
                    .all()
            else:
                # Get all stops
                stops = session.query(Stop).all()
            
            return {
                "status": "success",
                "data": [
                    {
                        "id": stop.id,
                        "name": stop.stop_name,
                        "latitude": stop.stop_lat,
                        "longitude": stop.stop_lon,
                        "wheelchair_boarding": stop.wheelchair_boarding
                    }
                    for stop in stops
                ]
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting stops: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def broadcast_realtime_data():
    """Background task to broadcast real-time data updates."""
    while True:
        try:
            # Get real-time data every 30 seconds
            summary = await transit_analytics.generate_service_summary(
                time_window=timedelta(hours=1)
            )
            
            # Broadcast to all connected clients
            await manager.broadcast({
                "type": "realtime_update",
                "timestamp": datetime.utcnow().isoformat(),
                "data": summary
            })
            
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error broadcasting real-time data: {e}")
            await asyncio.sleep(60)  # Wait longer on error


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
