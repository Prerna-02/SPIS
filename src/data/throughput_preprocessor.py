"""
Supply Chain Preprocessor for Port Throughput Prediction
Prepares data for 7-day ahead throughput forecasting.
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, Dict
import os


class ThroughputPreprocessor:
    """Preprocessor for port throughput prediction."""
    
    def __init__(
        self,
        data_path: str = 'data/raw/dynamic_supply_chain_logistics_dataset.csv',
        window_size: int = 7,  # 7 days lookback
        forecast_horizon: int = 7  # Predict next 7 days
    ):
        self.data_path = data_path
        self.window_size = window_size
        self.forecast_horizon = forecast_horizon
        self.scaler_features = MinMaxScaler()
        self.scaler_target = MinMaxScaler()
        
        # Port-relevant features only
        self.feature_cols = [
            'port_congestion_level',
            'warehouse_inventory_level',
            'handling_equipment_availability',
            'loading_unloading_time',
            'weather_condition_severity',
            'delay_probability'
        ]
        self.target_col = 'historical_demand'
        
    def load_data(self) -> pd.DataFrame:
        """Load and prepare daily aggregated data."""
        print("=" * 60)
        print("THROUGHPUT PREPROCESSING PIPELINE")
        print("=" * 60)
        
        df = pd.read_csv(self.data_path)
        print(f"✅ Loaded {len(df):,} records")
        
        # Parse timestamp and aggregate to daily
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        
        # Daily aggregation
        agg_funcs = {col: 'mean' for col in self.feature_cols}
        agg_funcs[self.target_col] = 'sum'  # Total demand per day
        
        daily_df = df.groupby('date').agg(agg_funcs).reset_index()
        daily_df = daily_df.sort_values('date').reset_index(drop=True)
        
        print(f"✅ Aggregated to {len(daily_df)} daily records")
        print(f"   Date range: {daily_df['date'].min()} to {daily_df['date'].max()}")
        
        return daily_df
    
    def create_sequences(
        self, 
        data: np.ndarray, 
        target: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM."""
        X, y = [], []
        
        for i in range(len(data) - self.window_size - self.forecast_horizon + 1):
            # Input: window_size days of features
            X.append(data[i:i + self.window_size])
            # Output: next forecast_horizon days of demand
            y.append(target[i + self.window_size:i + self.window_size + self.forecast_horizon])
        
        return np.array(X), np.array(y)
    
    def prepare_data(self, train_ratio: float = 0.7, val_ratio: float = 0.15) -> Dict:
        """Full preprocessing pipeline."""
        # Load and aggregate
        daily_df = self.load_data()
        
        # Extract features and target
        features = daily_df[self.feature_cols].values
        target = daily_df[[self.target_col]].values
        
        # Scale
        features_scaled = self.scaler_features.fit_transform(features)
        target_scaled = self.scaler_target.fit_transform(target).flatten()
        
        print(f"\n📦 Creating sequences...")
        print(f"   Window size: {self.window_size} days")
        print(f"   Forecast horizon: {self.forecast_horizon} days")
        
        # Create sequences
        X, y = self.create_sequences(features_scaled, target_scaled)
        print(f"✅ Created {len(X)} sequences")
        print(f"   X shape: {X.shape} (samples, window, features)")
        print(f"   y shape: {y.shape} (samples, forecast_days)")
        
        # Split data (time-based, no shuffle)
        n = len(X)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        X_train, y_train = X[:train_end], y[:train_end]
        X_val, y_val = X[train_end:val_end], y[train_end:val_end]
        X_test, y_test = X[val_end:], y[val_end:]
        
        print(f"\n✂️ Split data:")
        print(f"   Train: {len(X_train)} sequences")
        print(f"   Val:   {len(X_val)} sequences")
        print(f"   Test:  {len(X_test)} sequences")
        
        return {
            'train': (X_train, y_train),
            'val': (X_val, y_val),
            'test': (X_test, y_test),
            'daily_df': daily_df
        }
    
    def denormalize(self, y_scaled: np.ndarray) -> np.ndarray:
        """Convert scaled predictions back to actual demand values."""
        if y_scaled.ndim == 1:
            y_scaled = y_scaled.reshape(-1, 1)
        return self.scaler_target.inverse_transform(y_scaled).flatten()


if __name__ == '__main__':
    preprocessor = ThroughputPreprocessor()
    data = preprocessor.prepare_data()
    print("\n✅ Preprocessor ready!")
