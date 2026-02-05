"""
Feature 1: Port Throughput Forecasting API
==========================================
FastAPI service for 7-day port demand predictions.

Endpoints:
- GET /health - Health check
- GET /forecast - Run forecast with date range
- GET /metrics - Get model performance metrics
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import random

app = FastAPI(
    title="SPIS Feature 1 - Demand Forecasting",
    description="Port throughput predictions using TCN and LightGBM",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# MODELS
# ============================================================

class ForecastRow(BaseModel):
    date: str
    actual_port_calls: int
    pred_port_calls: int
    actual_throughput: int
    pred_throughput: int

class Metrics(BaseModel):
    r2: float
    mae: float
    rmse: float
    smape: float

class ForecastResponse(BaseModel):
    model: str
    start_date: str
    end_date: str
    forecasts: List[ForecastRow]
    port_calls_metrics: Metrics
    throughput_metrics: Metrics

# ============================================================
# SAMPLE DATA (Replace with actual model inference)
# ============================================================

# Model performance metrics from training
PORT_CALLS_METRICS = Metrics(r2=0.749, mae=3.2, rmse=4.1, smape=5.76)
THROUGHPUT_METRICS = Metrics(r2=0.721, mae=412, rmse=523, smape=6.24)

def generate_forecast_data(start_date: str, end_date: str) -> List[ForecastRow]:
    """Generate sample forecast data for date range."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    forecasts = []
    current = start
    
    while current <= end:
        # Base values with some weekly patterns
        day_of_week = current.weekday()
        base_calls = 185 + (day_of_week % 3) * 5  # Weekend dip
        base_throughput = 26000 + (day_of_week % 3) * 500
        
        # Add some randomness
        actual_calls = base_calls + random.randint(-8, 12)
        pred_calls = base_calls + random.randint(-5, 5)
        actual_tp = base_throughput + random.randint(-800, 1200)
        pred_tp = base_throughput + random.randint(-400, 600)
        
        forecasts.append(ForecastRow(
            date=current.strftime("%Y-%m-%d"),
            actual_port_calls=actual_calls,
            pred_port_calls=pred_calls,
            actual_throughput=actual_tp,
            pred_throughput=pred_tp
        ))
        current += timedelta(days=1)
    
    return forecasts

# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "feature1-forecasting"}

@app.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    model: str = Query("tcn", description="Model type: tcn or lightgbm")
):
    """
    Run forecast for the specified date range.
    
    Returns actual vs predicted values for port_calls and throughput.
    """
    forecasts = generate_forecast_data(start_date, end_date)
    
    return ForecastResponse(
        model=model,
        start_date=start_date,
        end_date=end_date,
        forecasts=forecasts,
        port_calls_metrics=PORT_CALLS_METRICS,
        throughput_metrics=THROUGHPUT_METRICS
    )

@app.get("/metrics")
async def get_metrics():
    """Get model performance metrics."""
    return {
        "model_info": {
            "tcn": {
                "name": "Temporal Convolutional Network",
                "encoder_length": 56,
                "forecast_horizon": 7
            },
            "lightgbm": {
                "name": "LightGBM Gradient Boosting",
                "n_estimators": 500,
                "max_depth": 8
            }
        },
        "port_calls": PORT_CALLS_METRICS.model_dump(),
        "throughput": THROUGHPUT_METRICS.model_dump()
    }

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
