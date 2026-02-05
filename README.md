# Smart Port Intelligence System (SPIS)

An integrated smart port intelligence system for forecasting throughput, anomaly detection, predictive maintenance, and berth optimization.

## Features

1. **Port Throughput Forecasting** - LSTM-based time series prediction
2. **Anomaly Detection + Chatbot** - Autoencoder + BERT intent classification
3. **Predictive Maintenance** - Multi-task LSTM (RUL + Failure Mode)
4. **Berth Scheduling** - Route optimization (Phase II)

## Project Structure

```
├── data/
│   ├── raw/                 # Original datasets
│   ├── processed/           # Cleaned data
│   └── synthetic/           # Generated data
├── notebooks/               # EDA and experiments
├── src/
│   ├── data/               # Data loading utilities
│   ├── models/             # PyTorch model definitions
│   ├── training/           # Training pipelines
│   ├── inference/          # Prediction pipelines
│   └── utils/              # Helper functions
└── tests/                  # Unit tests
```

## Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Tech Stack

- **Deep Learning**: PyTorch
- **Backend**: FastAPI
- **Frontend**: React + TailwindCSS
- **Database**: PostgreSQL
- **Deployment**: Docker

## Datasets

| Dataset | Records | Purpose |
|---------|---------|---------|
| Supply Chain Logistics | 32,065 | Throughput & Anomaly |
| Port Maintenance | 172,800 | Predictive Maintenance |
