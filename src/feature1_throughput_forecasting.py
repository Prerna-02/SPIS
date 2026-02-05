"""
Feature 1: Port Throughput Forecasting for Port of Tallinn
============================================================
Forecast port_calls and throughput_containers for the next 7 days.

Models:
- Model A: LightGBM (7 horizon-specific models per target)
- Model B: TCN (Temporal Convolutional Network)

Evaluation: Horizon-wise (H1..H7) metrics

Author: SPIS Team
"""

import os
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Tuple, Dict, List, Optional
import pickle
import json

# ML Libraries
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import lightgbm as lgb

# Deep Learning
import tensorflow as tf
from tensorflow.keras import layers, Model, callbacks

# Set seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_PATH = 'data/raw/tallinn_feature1_daily_v2.csv'
OUTPUT_DIR = 'data/processed/feature1_outputs'
MODEL_DIR = 'models/feature1'

ENCODER_LENGTH = 56  # 8 weeks of history
FORECAST_HORIZON = 7  # Predict next 7 days
TRAIN_RATIO = 0.80
BATCH_SIZE = 32

# Feature columns (exogenous - known at prediction time)
EXOG_FEATURES = [
    'weather_condition_severity',
    'port_congestion_level',
    'delay_probability',
    'handling_equipment_availability',
    'warehouse_inventory_level',
    'loading_unloading_time_hours',
    'food_share',
    'pharma_share',
    'electronics_share',
    'other_share',
    'position_accuracy_m',
    'year',
    'month',
    'day',
    'day_of_week',
    'day_of_year'
]

# Target columns
TARGET_COLS = ['port_calls', 'throughput_containers']

# Lag configurations for LightGBM
LAGS = [1, 7, 14, 28]
ROLLING_WINDOWS = [7, 14, 28]


# =============================================================================
# 1) DATA LOADING AND CLEANING
# =============================================================================

def load_and_clean_data(data_path: str) -> pd.DataFrame:
    """Load and preprocess the Tallinn dataset."""
    print("=" * 70)
    print("1) LOADING AND CLEANING DATA")
    print("=" * 70)
    
    df = pd.read_csv(data_path)
    print(f"[OK] Loaded {len(df):,} records")
    
    # Parse date
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    print(f"[DATE] Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"[STATS] Total days: {len(df)}")
    
    # Check for missing values
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print(f"[WARN] Missing values found:")
        print(missing[missing > 0])
        df = df.fillna(method='ffill').fillna(method='bfill')
        print("[OK] Missing values filled with forward/backward fill")
    else:
        print("[OK] No missing values")
    
    # Print target statistics
    print(f"\n[STATS] Target Statistics:")
    for col in TARGET_COLS:
        print(f"   {col}: mean={df[col].mean():.2f}, std={df[col].std():.2f}, "
              f"min={df[col].min():.2f}, max={df[col].max():.2f}")
    
    return df


# =============================================================================
# 2) FEATURE ENGINEERING (LAG FEATURES FOR LIGHTGBM)
# =============================================================================

def create_lag_features(df: pd.DataFrame, target_cols: List[str], 
                        lags: List[int], rolling_windows: List[int]) -> pd.DataFrame:
    """
    Create lag and rolling features for LightGBM.
    IMPORTANT: All features use ONLY past data (shift >= 1) to avoid leakage.
    """
    df = df.copy()
    
    for col in target_cols:
        # Lag features (shifted by at least 1 to avoid leakage)
        for lag in lags:
            df[f'{col}_lag_{lag}'] = df[col].shift(lag)
        
        # Rolling statistics (computed on past values only)
        for window in rolling_windows:
            # shift(1) ensures we don't include current day
            df[f'{col}_rolling_mean_{window}'] = df[col].shift(1).rolling(window, min_periods=1).mean()
            df[f'{col}_rolling_std_{window}'] = df[col].shift(1).rolling(window, min_periods=1).std()
            df[f'{col}_rolling_min_{window}'] = df[col].shift(1).rolling(window, min_periods=1).min()
            df[f'{col}_rolling_max_{window}'] = df[col].shift(1).rolling(window, min_periods=1).max()
    
    return df


def get_lgb_feature_cols(target_cols: List[str], exog_features: List[str],
                         lags: List[int], rolling_windows: List[int]) -> List[str]:
    """Get list of all feature columns for LightGBM."""
    feature_cols = exog_features.copy()
    
    for col in target_cols:
        for lag in lags:
            feature_cols.append(f'{col}_lag_{lag}')
        for window in rolling_windows:
            feature_cols.append(f'{col}_rolling_mean_{window}')
            feature_cols.append(f'{col}_rolling_std_{window}')
            feature_cols.append(f'{col}_rolling_min_{window}')
            feature_cols.append(f'{col}_rolling_max_{window}')
    
    return feature_cols


# =============================================================================
# 3) WINDOW CREATION FOR DIRECT MULTI-STEP FORECASTING
# =============================================================================

def make_windows_lgb(df: pd.DataFrame, feature_cols: List[str], target_col: str,
                     horizon: int, min_history: int = 28) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Create training samples for LightGBM for a specific horizon.
    
    For horizon H, we predict Y[t+H] using features at time t.
    X[i] = features at day i
    Y[i] = target at day i + horizon
    
    Returns: X, Y, dates (as-of dates)
    """
    # Drop rows with NaN in features
    valid_mask = df[feature_cols].notna().all(axis=1)
    
    X_list, Y_list, dates_list = [], [], []
    
    for i in range(len(df) - horizon):
        if not valid_mask.iloc[i]:
            continue
        if i < min_history:  # Need minimum history for lag features
            continue
            
        X_list.append(df[feature_cols].iloc[i].values)
        Y_list.append(df[target_col].iloc[i + horizon])
        dates_list.append(df['date'].iloc[i])
    
    return np.array(X_list), np.array(Y_list), np.array(dates_list)


def make_windows_dl(df: pd.DataFrame, feature_cols: List[str], target_cols: List[str],
                    encoder_length: int, forecast_horizon: int) -> Dict:
    """
    Create sequences for deep learning model (TCN).
    
    For each sample:
    - X: features from [t-encoder_length+1 .. t] (shape: encoder_length x n_features)
    - Y: targets from [t+1 .. t+forecast_horizon] (shape: forecast_horizon x n_targets)
    
    No future target values are used as input features.
    """
    features = df[feature_cols].values
    targets = df[target_cols].values
    dates = df['date'].values
    
    X_list, Y_list, dates_list = [], [], []
    
    for i in range(encoder_length - 1, len(df) - forecast_horizon):
        # Input: past encoder_length days of exogenous features + past targets
        X_seq = features[i - encoder_length + 1:i + 1]  # [t-55..t]
        
        # Output: next forecast_horizon days of targets
        Y_seq = targets[i + 1:i + 1 + forecast_horizon]  # [t+1..t+7]
        
        X_list.append(X_seq)
        Y_list.append(Y_seq)
        dates_list.append(dates[i])  # as-of date is t
    
    return {
        'X': np.array(X_list),
        'Y': np.array(Y_list),
        'dates': np.array(dates_list)
    }


# =============================================================================
# 4) TRAIN/VAL/TEST SPLIT (TIME-BASED)
# =============================================================================

def split_data_time(X: np.ndarray, Y: np.ndarray, dates: np.ndarray,
                    train_ratio: float = 0.8, val_ratio: float = 0.1) -> Dict:
    """
    Time-based split: Train -> Val -> Test
    No shuffling to preserve temporal order.
    """
    n = len(X)
    train_end = int(n * train_ratio)
    val_size = int(train_end * val_ratio)
    val_start = train_end - val_size
    
    return {
        'X_train': X[:val_start],
        'Y_train': Y[:val_start],
        'dates_train': dates[:val_start],
        'X_val': X[val_start:train_end],
        'Y_val': Y[val_start:train_end],
        'dates_val': dates[val_start:train_end],
        'X_test': X[train_end:],
        'Y_test': Y[train_end:],
        'dates_test': dates[train_end:]
    }


# =============================================================================
# 5) METRICS CALCULATION
# =============================================================================

def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Symmetric Mean Absolute Percentage Error."""
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2
    denominator = np.where(denominator == 0, 1, denominator)
    return np.mean(np.abs(y_true - y_pred) / denominator) * 100


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
    """Calculate all metrics for a single horizon."""
    return {
        'MAE': mean_absolute_error(y_true, y_pred),
        'RMSE': np.sqrt(mean_squared_error(y_true, y_pred)),
        'sMAPE': smape(y_true, y_pred),
        'R2': r2_score(y_true, y_pred)
    }


def calculate_horizon_metrics(Y_true: np.ndarray, Y_pred: np.ndarray, 
                              target_name: str) -> pd.DataFrame:
    """
    Calculate metrics for each horizon H1..H7.
    Y_true, Y_pred: shape (n_samples, 7)
    """
    rows = []
    
    for h in range(FORECAST_HORIZON):
        y_true_h = Y_true[:, h]
        y_pred_h = Y_pred[:, h]
        metrics = calculate_metrics(y_true_h, y_pred_h)
        metrics['Horizon'] = f'H{h+1}'
        metrics['Target'] = target_name
        rows.append(metrics)
    
    # Overall (mean across horizons)
    y_true_flat = Y_true.flatten()
    y_pred_flat = Y_pred.flatten()
    overall_metrics = calculate_metrics(y_true_flat, y_pred_flat)
    overall_metrics['Horizon'] = 'Overall'
    overall_metrics['Target'] = target_name
    rows.append(overall_metrics)
    
    return pd.DataFrame(rows)


# =============================================================================
# 6) MODEL A: LIGHTGBM (7 HORIZON-SPECIFIC MODELS PER TARGET)
# =============================================================================

def train_lightgbm_horizon(X_train: np.ndarray, Y_train: np.ndarray,
                           X_val: np.ndarray, Y_val: np.ndarray,
                           target_name: str, horizon: int) -> lgb.Booster:
    """Train LightGBM for a specific horizon."""
    
    train_data = lgb.Dataset(X_train, label=Y_train)
    val_data = lgb.Dataset(X_val, label=Y_val, reference=train_data)
    
    params = {
        'objective': 'regression',
        'metric': 'mae',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
        'seed': 42
    }
    
    model = lgb.train(
        params,
        train_data,
        num_boost_round=500,
        valid_sets=[val_data],
        valid_names=['val'],
        callbacks=[
            lgb.early_stopping(stopping_rounds=30),
            lgb.log_evaluation(period=0)  # Silent
        ]
    )
    
    return model


def train_lightgbm_all_horizons(df: pd.DataFrame, feature_cols: List[str],
                                 target_col: str, train_ratio: float = 0.8) -> Dict:
    """
    Train 7 LightGBM models for horizons H1..H7 for one target.
    """
    print(f"\n[LGB] Training LightGBM for {target_col}...")
    
    models = {}
    predictions = {}
    
    for h in range(1, FORECAST_HORIZON + 1):
        # Create training data for this horizon
        X, Y, dates = make_windows_lgb(df, feature_cols, target_col, horizon=h)
        
        # Split
        split = split_data_time(X, Y, dates, train_ratio)
        
        if h == 1:
            print(f"   Train: {len(split['X_train'])}, Val: {len(split['X_val'])}, Test: {len(split['X_test'])}")
        
        # Train
        model = train_lightgbm_horizon(
            split['X_train'], split['Y_train'],
            split['X_val'], split['Y_val'],
            target_col, h
        )
        models[h] = model
        
        # Predict on test
        Y_pred = model.predict(split['X_test'])
        predictions[h] = {
            'Y_true': split['Y_test'],
            'Y_pred': Y_pred,
            'dates': split['dates_test']
        }
    
    print(f"[OK] LightGBM trained for {target_col}: 7 horizon models")
    return {'models': models, 'predictions': predictions}


def evaluate_lightgbm(df: pd.DataFrame) -> Dict:
    """Train and evaluate LightGBM for both targets."""
    print("\n" + "=" * 70)
    print("5A) MODEL A: LIGHTGBM (7 HORIZON-SPECIFIC MODELS)")
    print("=" * 70)
    
    # Create lag features
    df_features = create_lag_features(df, TARGET_COLS, LAGS, ROLLING_WINDOWS)
    feature_cols = get_lgb_feature_cols(TARGET_COLS, EXOG_FEATURES, LAGS, ROLLING_WINDOWS)
    
    results = {}
    
    for target_col in TARGET_COLS:
        target_results = train_lightgbm_all_horizons(df_features, feature_cols, target_col, TRAIN_RATIO)
        
        # Organize predictions into (n_samples, 7) arrays
        # Align by as-of date (find common test dates across all horizons)
        all_dates = [set(target_results['predictions'][h]['dates'].astype(str)) for h in range(1, 8)]
        common_dates = set.intersection(*all_dates)
        common_dates = sorted(common_dates)
        
        Y_true_aligned = []
        Y_pred_aligned = []
        dates_aligned = []
        
        for date_str in common_dates:
            Y_true_row = []
            Y_pred_row = []
            for h in range(1, 8):
                pred_data = target_results['predictions'][h]
                idx = np.where(pred_data['dates'].astype(str) == date_str)[0]
                if len(idx) > 0:
                    Y_true_row.append(pred_data['Y_true'][idx[0]])
                    Y_pred_row.append(pred_data['Y_pred'][idx[0]])
            if len(Y_true_row) == 7:
                Y_true_aligned.append(Y_true_row)
                Y_pred_aligned.append(Y_pred_row)
                dates_aligned.append(pd.to_datetime(date_str))
        
        Y_true_aligned = np.array(Y_true_aligned)
        Y_pred_aligned = np.array(Y_pred_aligned)
        
        # Calculate horizon-wise metrics
        metrics_df = calculate_horizon_metrics(Y_true_aligned, Y_pred_aligned, target_col)
        
        results[target_col] = {
            'models': target_results['models'],
            'Y_true': Y_true_aligned,
            'Y_pred': Y_pred_aligned,
            'dates': dates_aligned,
            'metrics': metrics_df
        }
        
        print(f"\n[METRICS] {target_col} - LightGBM Horizon-wise:")
        print(metrics_df.to_string(index=False))
    
    return results


# =============================================================================
# 7) MODEL B: TCN (TEMPORAL CONVOLUTIONAL NETWORK)
# =============================================================================

class ResidualBlock(layers.Layer):
    """Residual block for TCN with causal convolutions."""
    
    def __init__(self, filters, kernel_size, dilation_rate, dropout_rate=0.1, **kwargs):
        super().__init__(**kwargs)
        self.filters = filters
        self.kernel_size = kernel_size
        self.dilation_rate = dilation_rate
        self.dropout_rate = dropout_rate
        
    def build(self, input_shape):
        self.conv1 = layers.Conv1D(
            self.filters, self.kernel_size, 
            padding='causal', dilation_rate=self.dilation_rate,
            activation='relu'
        )
        self.dropout1 = layers.Dropout(self.dropout_rate)
        self.conv2 = layers.Conv1D(
            self.filters, self.kernel_size,
            padding='causal', dilation_rate=self.dilation_rate,
            activation='relu'
        )
        self.dropout2 = layers.Dropout(self.dropout_rate)
        
        # Skip connection
        if input_shape[-1] != self.filters:
            self.skip_conv = layers.Conv1D(self.filters, 1, padding='same')
        else:
            self.skip_conv = None
        
        self.layer_norm = layers.LayerNormalization()
        super().build(input_shape)
        
    def call(self, x, training=None):
        residual = x
        
        out = self.conv1(x)
        out = self.dropout1(out, training=training)
        out = self.conv2(out)
        out = self.dropout2(out, training=training)
        
        if self.skip_conv is not None:
            residual = self.skip_conv(residual)
        
        return self.layer_norm(out + residual)
    
    def get_config(self):
        config = super().get_config()
        config.update({
            'filters': self.filters,
            'kernel_size': self.kernel_size,
            'dilation_rate': self.dilation_rate,
            'dropout_rate': self.dropout_rate
        })
        return config


def build_tcn_model(
    input_length: int,
    n_features: int,
    output_length: int,
    n_targets: int = 1,
    filters: int = 64,
    kernel_size: int = 3,
    dilations: List[int] = [1, 2, 4, 8, 16],
    dropout_rate: float = 0.1,
    learning_rate: float = 0.001
) -> Model:
    """
    Build TCN model for multi-horizon forecasting.
    
    Architecture:
        Input (56 days x features)
        -> Stacked Residual Blocks with increasing dilations
        -> GlobalAveragePooling
        -> Dense layers
        -> Output (7 days)
    """
    inputs = layers.Input(shape=(input_length, n_features), name='tcn_input')
    
    x = inputs
    
    # Stack of residual blocks with increasing dilation
    for dilation in dilations:
        x = ResidualBlock(filters, kernel_size, dilation, dropout_rate)(x)
    
    # Output projection
    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dense(128, activation='relu')(x)
    x = layers.Dropout(dropout_rate)(x)
    x = layers.Dense(64, activation='relu')(x)
    
    # Multi-horizon output
    output = layers.Dense(output_length * n_targets, activation='linear', name='forecast_output')(x)
    
    if n_targets > 1:
        output = layers.Reshape((output_length, n_targets), name='reshape_output')(output)
    
    model = Model(inputs=inputs, outputs=output, name='TCN_Forecaster')
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss='mse',
        metrics=['mae']
    )
    
    return model


def train_tcn(model: Model, X_train: np.ndarray, Y_train: np.ndarray,
              X_val: np.ndarray, Y_val: np.ndarray,
              epochs: int = 100, batch_size: int = 32,
              model_name: str = 'tcn') -> callbacks.History:
    """Train TCN model with early stopping."""
    
    early_stop = callbacks.EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True,
        verbose=1
    )
    
    lr_scheduler = callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=5,
        min_lr=1e-6,
        verbose=1
    )
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    checkpoint = callbacks.ModelCheckpoint(
        filepath=os.path.join(MODEL_DIR, f'{model_name}_best.keras'),
        monitor='val_loss',
        save_best_only=True,
        verbose=0
    )
    
    history = model.fit(
        X_train, Y_train,
        validation_data=(X_val, Y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stop, lr_scheduler, checkpoint],
        verbose=1
    )
    
    return history


def evaluate_tcn(df: pd.DataFrame) -> Dict:
    """Train and evaluate TCN for both targets."""
    print("\n" + "=" * 70)
    print("5B) MODEL B: TCN (TEMPORAL CONVOLUTIONAL NETWORK)")
    print("=" * 70)
    
    # Prepare features: exogenous + past targets as time series
    all_features = EXOG_FEATURES + TARGET_COLS
    
    # Scale features
    scaler = StandardScaler()
    df_scaled = df.copy()
    df_scaled[all_features] = scaler.fit_transform(df[all_features])
    
    # Create windows
    data = make_windows_dl(df_scaled, all_features, TARGET_COLS, ENCODER_LENGTH, FORECAST_HORIZON)
    
    print(f"[OK] Created {len(data['X']):,} sequences")
    print(f"   X shape: {data['X'].shape}")
    print(f"   Y shape: {data['Y'].shape}")
    
    # Split
    split = split_data_time(data['X'], data['Y'], data['dates'], TRAIN_RATIO)
    
    print(f"\n[SPLIT] Train: {len(split['X_train'])}, Val: {len(split['X_val'])}, Test: {len(split['X_test'])}")
    
    results = {}
    
    # Train separate model for each target (cleaner approach)
    for target_idx, target_col in enumerate(TARGET_COLS):
        print(f"\n[TCN] Training TCN for {target_col}...")
        
        # Extract single target
        Y_train = split['Y_train'][:, :, target_idx]
        Y_val = split['Y_val'][:, :, target_idx]
        Y_test = split['Y_test'][:, :, target_idx]
        
        # Build model
        model = build_tcn_model(
            input_length=ENCODER_LENGTH,
            n_features=len(all_features),
            output_length=FORECAST_HORIZON,
            n_targets=1,
            filters=64,
            kernel_size=3,
            dilations=[1, 2, 4, 8, 16],
            dropout_rate=0.1,
            learning_rate=0.001
        )
        
        print(f"   Model parameters: {model.count_params():,}")
        
        # Train
        history = train_tcn(
            model, split['X_train'], Y_train,
            split['X_val'], Y_val,
            epochs=100, batch_size=BATCH_SIZE,
            model_name=f'tcn_{target_col}'
        )
        
        # Predict
        Y_pred_scaled = model.predict(split['X_test'], verbose=0)
        
        # Inverse transform predictions
        # We need to denormalize only the target column
        target_mean = scaler.mean_[EXOG_FEATURES.__len__() + target_idx]
        target_std = scaler.scale_[EXOG_FEATURES.__len__() + target_idx]
        
        Y_pred = Y_pred_scaled * target_std + target_mean
        Y_true = Y_test * target_std + target_mean
        
        # Calculate horizon-wise metrics
        metrics_df = calculate_horizon_metrics(Y_true, Y_pred, target_col)
        
        results[target_col] = {
            'model': model,
            'Y_true': Y_true,
            'Y_pred': Y_pred,
            'dates': split['dates_test'],
            'metrics': metrics_df,
            'history': history
        }
        
        print(f"\n[METRICS] {target_col} - TCN Horizon-wise:")
        print(metrics_df.to_string(index=False))
    
    # Save scaler
    scaler_path = os.path.join(MODEL_DIR, 'tcn_scaler.pkl')
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"\n[OK] Saved scaler: {scaler_path}")
    
    return results


# =============================================================================
# 8) ACTUAL vs PREDICTED TABLE
# =============================================================================

def create_pred_vs_actual_table(lgb_results: Dict, tcn_results: Dict, df: pd.DataFrame) -> pd.DataFrame:
    """Create detailed prediction vs actual table."""
    rows = []
    
    for target_col in TARGET_COLS:
        # LightGBM predictions
        lgb_dates = lgb_results[target_col]['dates']
        lgb_Y_true = lgb_results[target_col]['Y_true']
        lgb_Y_pred = lgb_results[target_col]['Y_pred']
        
        for i, as_of_date in enumerate(lgb_dates):
            for h in range(FORECAST_HORIZON):
                pred_date = as_of_date + timedelta(days=h+1)
                actual = lgb_Y_true[i, h]
                predicted = lgb_Y_pred[i, h]
                abs_error = abs(predicted - actual)
                pct_error = 2 * abs_error / (abs(actual) + abs(predicted) + 1e-8) * 100
                
                rows.append({
                    'model': 'LightGBM',
                    'target': target_col,
                    'as_of_date': as_of_date.strftime('%Y-%m-%d'),
                    'horizon': h + 1,
                    'date_predicted_for': pred_date.strftime('%Y-%m-%d'),
                    'actual_value': actual,
                    'predicted_value': predicted,
                    'absolute_error': abs_error,
                    'percent_error': pct_error
                })
        
        # TCN predictions
        tcn_dates = tcn_results[target_col]['dates']
        tcn_Y_true = tcn_results[target_col]['Y_true']
        tcn_Y_pred = tcn_results[target_col]['Y_pred']
        
        for i, as_of_date in enumerate(tcn_dates):
            as_of_date = pd.to_datetime(as_of_date)
            for h in range(FORECAST_HORIZON):
                pred_date = as_of_date + timedelta(days=h+1)
                actual = tcn_Y_true[i, h]
                predicted = tcn_Y_pred[i, h]
                abs_error = abs(predicted - actual)
                pct_error = 2 * abs_error / (abs(actual) + abs(predicted) + 1e-8) * 100
                
                rows.append({
                    'model': 'TCN',
                    'target': target_col,
                    'as_of_date': as_of_date.strftime('%Y-%m-%d'),
                    'horizon': h + 1,
                    'date_predicted_for': pred_date.strftime('%Y-%m-%d'),
                    'actual_value': actual,
                    'predicted_value': predicted,
                    'absolute_error': abs_error,
                    'percent_error': pct_error
                })
    
    return pd.DataFrame(rows)


def create_summary_table(lgb_results: Dict, tcn_results: Dict) -> pd.DataFrame:
    """Create summary metrics table by model and target."""
    rows = []
    
    for target_col in TARGET_COLS:
        # LightGBM
        lgb_metrics = lgb_results[target_col]['metrics']
        lgb_overall = lgb_metrics[lgb_metrics['Horizon'] == 'Overall'].iloc[0]
        rows.append({
            'Model': 'LightGBM',
            'Target': target_col,
            'MAE': lgb_overall['MAE'],
            'RMSE': lgb_overall['RMSE'],
            'sMAPE (%)': lgb_overall['sMAPE'],
            'R2': lgb_overall['R2']
        })
        
        # TCN
        tcn_metrics = tcn_results[target_col]['metrics']
        tcn_overall = tcn_metrics[tcn_metrics['Horizon'] == 'Overall'].iloc[0]
        rows.append({
            'Model': 'TCN',
            'Target': target_col,
            'MAE': tcn_overall['MAE'],
            'RMSE': tcn_overall['RMSE'],
            'sMAPE (%)': tcn_overall['sMAPE'],
            'R2': tcn_overall['R2']
        })
    
    return pd.DataFrame(rows)


# =============================================================================
# 9) VISUALIZATION
# =============================================================================

def plot_horizon_comparison(lgb_results: Dict, tcn_results: Dict, output_dir: str):
    """Create visualization plots for each target and horizon."""
    print("\n" + "=" * 70)
    print("8) CREATING VISUALIZATIONS")
    print("=" * 70)
    
    os.makedirs(output_dir, exist_ok=True)
    
    for target_col in TARGET_COLS:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'{target_col} - Model Comparison', fontsize=14, fontweight='bold')
        
        # LightGBM data
        lgb_Y_true = lgb_results[target_col]['Y_true']
        lgb_Y_pred = lgb_results[target_col]['Y_pred']
        
        # TCN data
        tcn_Y_true = tcn_results[target_col]['Y_true']
        tcn_Y_pred = tcn_results[target_col]['Y_pred']
        
        n_samples = min(150, len(lgb_Y_true), len(tcn_Y_true))
        
        # Plot 1: Horizon 1 (easiest)
        ax1 = axes[0, 0]
        ax1.plot(range(n_samples), lgb_Y_true[:n_samples, 0], 'b-', label='Actual', alpha=0.7, linewidth=1)
        ax1.plot(range(n_samples), lgb_Y_pred[:n_samples, 0], 'r--', label='LightGBM', alpha=0.7, linewidth=1)
        ax1.plot(range(n_samples), tcn_Y_pred[:n_samples, 0], 'g--', label='TCN', alpha=0.7, linewidth=1)
        ax1.set_title('Horizon H1 (1-day ahead): Actual vs Predicted')
        ax1.set_xlabel('Test Sample Index')
        ax1.set_ylabel(target_col)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Horizon 7 (hardest)
        ax2 = axes[0, 1]
        ax2.plot(range(n_samples), lgb_Y_true[:n_samples, 6], 'b-', label='Actual', alpha=0.7, linewidth=1)
        ax2.plot(range(n_samples), lgb_Y_pred[:n_samples, 6], 'r--', label='LightGBM', alpha=0.7, linewidth=1)
        ax2.plot(range(n_samples), tcn_Y_pred[:n_samples, 6], 'g--', label='TCN', alpha=0.7, linewidth=1)
        ax2.set_title('Horizon H7 (7-day ahead): Actual vs Predicted')
        ax2.set_xlabel('Test Sample Index')
        ax2.set_ylabel(target_col)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Residuals H1
        ax3 = axes[1, 0]
        lgb_residuals_h1 = lgb_Y_pred[:n_samples, 0] - lgb_Y_true[:n_samples, 0]
        tcn_residuals_h1 = tcn_Y_pred[:n_samples, 0] - tcn_Y_true[:n_samples, 0]
        ax3.scatter(range(n_samples), lgb_residuals_h1, alpha=0.5, s=10, c='red', label='LightGBM')
        ax3.scatter(range(n_samples), tcn_residuals_h1, alpha=0.5, s=10, c='green', label='TCN')
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax3.set_title('Residuals H1 (Predicted - Actual)')
        ax3.set_xlabel('Test Sample Index')
        ax3.set_ylabel('Residual')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Residuals H7
        ax4 = axes[1, 1]
        lgb_residuals_h7 = lgb_Y_pred[:n_samples, 6] - lgb_Y_true[:n_samples, 6]
        tcn_residuals_h7 = tcn_Y_pred[:n_samples, 6] - tcn_Y_true[:n_samples, 6]
        ax4.scatter(range(n_samples), lgb_residuals_h7, alpha=0.5, s=10, c='red', label='LightGBM')
        ax4.scatter(range(n_samples), tcn_residuals_h7, alpha=0.5, s=10, c='green', label='TCN')
        ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax4.set_title('Residuals H7 (Predicted - Actual)')
        ax4.set_xlabel('Test Sample Index')
        ax4.set_ylabel('Residual')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = os.path.join(output_dir, f'{target_col}_horizon_comparison.png')
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[OK] Saved: {plot_path}")
    
    # Horizon-wise metrics plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    for idx, target_col in enumerate(TARGET_COLS):
        ax = axes[idx]
        
        lgb_metrics = lgb_results[target_col]['metrics']
        tcn_metrics = tcn_results[target_col]['metrics']
        
        horizons = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7']
        
        lgb_smape = lgb_metrics[lgb_metrics['Horizon'].isin(horizons)]['sMAPE'].values
        tcn_smape = tcn_metrics[tcn_metrics['Horizon'].isin(horizons)]['sMAPE'].values
        
        x = np.arange(len(horizons))
        width = 0.35
        
        ax.bar(x - width/2, lgb_smape, width, label='LightGBM', color='coral')
        ax.bar(x + width/2, tcn_smape, width, label='TCN', color='seagreen')
        
        ax.set_xlabel('Horizon')
        ax.set_ylabel('sMAPE (%)')
        ax.set_title(f'{target_col} - sMAPE by Horizon')
        ax.set_xticks(x)
        ax.set_xticklabels(horizons)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    metrics_plot_path = os.path.join(output_dir, 'horizon_metrics_comparison.png')
    plt.savefig(metrics_plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved: {metrics_plot_path}")


# =============================================================================
# 10) MAIN
# =============================================================================

def main():
    """Main execution function."""
    print("\n" + "=" * 70)
    print("SMART PORT INTELLIGENCE SYSTEM - FEATURE 1")
    print("Port Throughput Forecasting for Port of Tallinn")
    print("Multi-Horizon Direct Forecasting (7 days ahead)")
    print("=" * 70)
    print(f"\n[CONFIG]")
    print(f"   Encoder Length: {ENCODER_LENGTH} days")
    print(f"   Forecast Horizon: {FORECAST_HORIZON} days")
    print(f"   Train/Test Split: {TRAIN_RATIO*100:.0f}% / {(1-TRAIN_RATIO)*100:.0f}%")
    print(f"   Model A: LightGBM (7 horizon-specific models per target)")
    print(f"   Model B: TCN (Temporal Convolutional Network)")
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # 1) Load and clean data
    df = load_and_clean_data(DATA_PATH)
    
    # 5A) Train and evaluate LightGBM
    lgb_results = evaluate_lightgbm(df)
    
    # Save LightGBM models
    for target_col in TARGET_COLS:
        for h, model in lgb_results[target_col]['models'].items():
            model_path = os.path.join(MODEL_DIR, f'lgb_{target_col}_h{h}.txt')
            model.save_model(model_path)
    print(f"[OK] Saved LightGBM models to {MODEL_DIR}/")
    
    # 5B) Train and evaluate TCN
    tcn_results = evaluate_tcn(df)
    
    # Save TCN models
    for target_col in TARGET_COLS:
        model_path = os.path.join(MODEL_DIR, f'tcn_{target_col}.keras')
        tcn_results[target_col]['model'].save(model_path)
    print(f"[OK] Saved TCN models to {MODEL_DIR}/")
    
    # 7) Create prediction tables
    print("\n" + "=" * 70)
    print("7) ACTUAL vs PREDICTED TABLE")
    print("=" * 70)
    
    pred_table = create_pred_vs_actual_table(lgb_results, tcn_results, df)
    
    # Save full table
    pred_table_path = os.path.join(OUTPUT_DIR, 'pred_vs_actual_feature1.csv')
    pred_table.to_csv(pred_table_path, index=False)
    print(f"[OK] Saved: {pred_table_path}")
    
    # Show first 30 rows
    print("\n[TABLE] First 30 rows of Actual vs Predicted:")
    print("-" * 120)
    display_cols = ['model', 'target', 'as_of_date', 'horizon', 'date_predicted_for', 
                    'actual_value', 'predicted_value', 'absolute_error', 'percent_error']
    print(pred_table[display_cols].head(30).to_string(index=False))
    
    # Summary table
    summary_table = create_summary_table(lgb_results, tcn_results)
    summary_path = os.path.join(OUTPUT_DIR, 'model_summary_feature1.csv')
    summary_table.to_csv(summary_path, index=False)
    
    print("\n" + "=" * 70)
    print("6) FINAL METRICS COMPARISON")
    print("=" * 70)
    print("\n[SUMMARY] Overall Model Performance:")
    print("-" * 80)
    print(summary_table.to_string(index=False))
    
    # 8) Create visualizations
    plot_horizon_comparison(lgb_results, tcn_results, OUTPUT_DIR)
    
    # 9) Decision
    print("\n" + "=" * 70)
    print("9) MODEL RECOMMENDATION")
    print("=" * 70)
    
    for target_col in TARGET_COLS:
        lgb_overall = lgb_results[target_col]['metrics'][lgb_results[target_col]['metrics']['Horizon'] == 'Overall'].iloc[0]
        tcn_overall = tcn_results[target_col]['metrics'][tcn_results[target_col]['metrics']['Horizon'] == 'Overall'].iloc[0]
        
        # Primary: lowest sMAPE, Secondary: highest R2
        lgb_score = -lgb_overall['sMAPE'] + lgb_overall['R2'] * 10
        tcn_score = -tcn_overall['sMAPE'] + tcn_overall['R2'] * 10
        
        best_model = "LightGBM" if lgb_score > tcn_score else "TCN"
        
        print(f"\n[BEST] {target_col}: Best model is {best_model}")
        print(f"   LightGBM - sMAPE: {lgb_overall['sMAPE']:.2f}%, R2: {lgb_overall['R2']:.4f}, MAE: {lgb_overall['MAE']:.2f}")
        print(f"   TCN      - sMAPE: {tcn_overall['sMAPE']:.2f}%, R2: {tcn_overall['R2']:.4f}, MAE: {tcn_overall['MAE']:.2f}")
        
        # Horizon stability analysis
        lgb_h1 = lgb_results[target_col]['metrics'][lgb_results[target_col]['metrics']['Horizon'] == 'H1'].iloc[0]['sMAPE']
        lgb_h7 = lgb_results[target_col]['metrics'][lgb_results[target_col]['metrics']['Horizon'] == 'H7'].iloc[0]['sMAPE']
        tcn_h1 = tcn_results[target_col]['metrics'][tcn_results[target_col]['metrics']['Horizon'] == 'H1'].iloc[0]['sMAPE']
        tcn_h7 = tcn_results[target_col]['metrics'][tcn_results[target_col]['metrics']['Horizon'] == 'H7'].iloc[0]['sMAPE']
        
        print(f"\n   Horizon Stability (H1 vs H7 sMAPE):")
        print(f"   LightGBM - H1: {lgb_h1:.2f}%, H7: {lgb_h7:.2f}% (degradation: {lgb_h7-lgb_h1:+.2f}%)")
        print(f"   TCN      - H1: {tcn_h1:.2f}%, H7: {tcn_h7:.2f}% (degradation: {tcn_h7-tcn_h1:+.2f}%)")
    
    # 10) Output artifacts
    print("\n" + "=" * 70)
    print("10) SAVED ARTIFACTS")
    print("=" * 70)
    print(f"\n[FILE] Models ({MODEL_DIR}/):")
    for target_col in TARGET_COLS:
        print(f"   - lgb_{target_col}_h1.txt .. lgb_{target_col}_h7.txt")
        print(f"   - tcn_{target_col}.keras")
    print(f"   - tcn_scaler.pkl")
    
    print(f"\n[FILE] Outputs ({OUTPUT_DIR}/):")
    print(f"   - pred_vs_actual_feature1.csv")
    print(f"   - model_summary_feature1.csv")
    print(f"   - port_calls_horizon_comparison.png")
    print(f"   - throughput_containers_horizon_comparison.png")
    print(f"   - horizon_metrics_comparison.png")
    
    print("\n[OK] Feature 1 training complete!")
    
    return lgb_results, tcn_results


if __name__ == '__main__':
    lgb_results, tcn_results = main()
