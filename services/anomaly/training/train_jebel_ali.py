"""
Jebel Ali Port Anomaly Detection Training Pipeline
===================================================
Filters AIS data for Jebel Ali port area, trains autoencoder,
computes dynamic threshold from validation data, and evaluates with proper metrics.

Port: Jebel Ali, Dubai, UAE
Bounding Box:
  - lat_min = 24.90, lat_max = 25.22
  - lon_min = 54.85, lon_max = 55.20
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score
import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# ============================================================
# CONFIGURATION
# ============================================================
JEBEL_ALI_BBOX = {
    'lat_min': 24.90,
    'lat_max': 25.22,
    'lon_min': 54.85,
    'lon_max': 55.20
}

RANDOM_SEED = 42
TEST_SIZE = 0.2
VAL_SIZE = 0.15
THRESHOLD_PERCENTILE = 99  # Use 99th percentile for fewer false alarms

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
MODELS_DIR = BASE_DIR / 'models'

# ============================================================
# A) DATA FILTERING
# ============================================================
def load_and_filter_ais_data(input_csv: str, output_csv: str = None) -> pd.DataFrame:
    """
    Load AIS data and filter for Jebel Ali bounding box.
    
    Args:
        input_csv: Path to raw AIS data
        output_csv: Optional path to save filtered data
        
    Returns:
        Filtered DataFrame
    """
    print("=" * 60)
    print("A) DATA FILTERING - Jebel Ali Port Area")
    print("=" * 60)
    
    # Load data with error handling for malformed lines
    print(f"\nLoading AIS data from: {input_csv}")
    try:
        df = pd.read_csv(input_csv, on_bad_lines='skip', comment='#')
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None
    
    print(f"  Total rows loaded: {len(df):,}")
    
    # Standardize column names (handle variations)
    df.columns = df.columns.str.strip().str.lower()
    
    # Map common column name variations
    col_mapping = {
        '# timestamp': 'timestamp',
        'timestamp': 'timestamp',
        'timestamp_str': 'timestamp',
        'lat': 'latitude',
        'lon': 'longitude',
        'long': 'longitude'
    }
    df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})
    
    # Drop rows with missing lat/lon
    rows_before = len(df)
    df = df.dropna(subset=['latitude', 'longitude'])
    print(f"  After dropping missing lat/lon: {len(df):,} (removed {rows_before - len(df):,})")
    
    # Apply Jebel Ali bounding box filter
    rows_before = len(df)
    bbox = JEBEL_ALI_BBOX
    df_filtered = df[
        (df['latitude'] >= bbox['lat_min']) &
        (df['latitude'] <= bbox['lat_max']) &
        (df['longitude'] >= bbox['lon_min']) &
        (df['longitude'] <= bbox['lon_max'])
    ].copy()
    
    print(f"\n  Bounding Box Filter:")
    print(f"    Lat: {bbox['lat_min']} to {bbox['lat_max']}")
    print(f"    Lon: {bbox['lon_min']} to {bbox['lon_max']}")
    print(f"  Rows after filtering: {len(df_filtered):,} (from {rows_before:,})")
    
    # Save filtered data if path provided
    if output_csv and len(df_filtered) > 0:
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        df_filtered.to_csv(output_csv, index=False)
        print(f"\n  Saved filtered data to: {output_csv}")
    
    return df_filtered


def generate_synthetic_jebel_ali_data(n_samples: int = 5000) -> pd.DataFrame:
    """
    Generate synthetic AIS data for Jebel Ali port for demo/training.
    Creates realistic vessel movement patterns within the port area.
    """
    print("\n" + "=" * 60)
    print("GENERATING SYNTHETIC JEBEL ALI AIS DATA")
    print("=" * 60)
    
    np.random.seed(RANDOM_SEED)
    bbox = JEBEL_ALI_BBOX
    
    # Generate timestamps over last 30 days
    base_time = datetime(2024, 1, 1)
    timestamps = [base_time + pd.Timedelta(hours=np.random.randint(0, 720)) for _ in range(n_samples)]
    timestamp_strs = [t.strftime("%d/%m/%Y %H:%M:%S") for t in timestamps]
    
    # Generate realistic AIS data
    data = {
        'timestamp': timestamp_strs,
        'mmsi': np.random.randint(200000000, 999999999, n_samples),
        'latitude': np.random.uniform(bbox['lat_min'], bbox['lat_max'], n_samples),
        'longitude': np.random.uniform(bbox['lon_min'], bbox['lon_max'], n_samples),
        'sog': np.clip(np.random.exponential(5, n_samples), 0, 25),  # Speed 0-25 knots
        'cog': np.random.uniform(0, 360, n_samples),  # Course 0-360 degrees
        'heading': np.random.uniform(0, 360, n_samples)  # Heading 0-360 degrees
    }
    
    df = pd.DataFrame(data)
    print(f"  Generated {len(df):,} synthetic AIS records")
    print(f"  Lat range: {df['latitude'].min():.4f} to {df['latitude'].max():.4f}")
    print(f"  Lon range: {df['longitude'].min():.4f} to {df['longitude'].max():.4f}")
    
    return df


# ============================================================
# B) FEATURE PREPARATION
# ============================================================
def prepare_features(df: pd.DataFrame) -> tuple:
    """
    Prepare features for autoencoder training.
    
    Features:
        - timestamp (numeric seconds)
        - mmsi
        - latitude, longitude
        - sog, cog, heading
    """
    print("\n" + "=" * 60)
    print("B) FEATURE PREPARATION")
    print("=" * 60)
    
    # Convert timestamp to numeric
    if 'timestamp' in df.columns:
        try:
            df['timestamp_sec'] = pd.to_datetime(
                df['timestamp'], 
                format='%d/%m/%Y %H:%M:%S',
                errors='coerce'
            ).astype('int64') / 1e9
        except:
            df['timestamp_sec'] = pd.Timestamp.now().timestamp()
    else:
        df['timestamp_sec'] = pd.Timestamp.now().timestamp()
    
    # Select features
    feature_cols = ['timestamp_sec', 'mmsi', 'latitude', 'longitude', 'sog', 'cog', 'heading']
    
    # Handle missing features
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0
    
    # Drop rows with any missing values in features
    df_clean = df[feature_cols].dropna()
    print(f"  Samples after cleaning: {len(df_clean):,}")
    
    # Split data
    X = df_clean.values
    X_train_val, X_test = train_test_split(X, test_size=TEST_SIZE, random_state=RANDOM_SEED)
    X_train, X_val = train_test_split(X_train_val, test_size=VAL_SIZE, random_state=RANDOM_SEED)
    
    print(f"  Train samples: {len(X_train):,}")
    print(f"  Validation samples: {len(X_val):,}")
    print(f"  Test samples: {len(X_test):,}")
    
    return X_train, X_val, X_test, feature_cols


# ============================================================
# C) SCALING
# ============================================================
def fit_scaler(X_train: np.ndarray, save_path: str) -> StandardScaler:
    """
    Fit StandardScaler on training data only.
    """
    print("\n" + "=" * 60)
    print("C) SCALING")
    print("=" * 60)
    
    scaler = StandardScaler()
    scaler.fit(X_train)
    
    # Save scaler
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, save_path)
    print(f"  Scaler saved to: {save_path}")
    
    return scaler


# ============================================================
# D) AUTOENCODER TRAINING
# ============================================================
def build_autoencoder(input_dim: int) -> Model:
    """
    Build autoencoder with architecture: 32 → 16 → 8 → 16 → 32 → output
    """
    inputs = layers.Input(shape=(input_dim,))
    
    # Encoder
    x = layers.Dense(32, activation='relu')(inputs)
    x = layers.Dense(16, activation='relu')(x)
    encoded = layers.Dense(8, activation='relu')(x)
    
    # Decoder
    x = layers.Dense(16, activation='relu')(encoded)
    x = layers.Dense(32, activation='relu')(x)
    decoded = layers.Dense(input_dim, activation='linear')(x)
    
    autoencoder = Model(inputs, decoded, name='jebel_ali_autoencoder')
    autoencoder.compile(optimizer='adam', loss='mse')
    
    return autoencoder


def train_autoencoder(X_train_scaled: np.ndarray, X_val_scaled: np.ndarray, 
                      model_path: str, epochs: int = 100, batch_size: int = 32) -> Model:
    """
    Train autoencoder with early stopping on validation loss.
    """
    print("\n" + "=" * 60)
    print("D) AUTOENCODER TRAINING")
    print("=" * 60)
    
    input_dim = X_train_scaled.shape[1]
    model = build_autoencoder(input_dim)
    
    print(f"\n  Model Architecture:")
    model.summary()
    
    # Callbacks
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True,
        verbose=1
    )
    
    checkpoint = ModelCheckpoint(
        model_path,
        monitor='val_loss',
        save_best_only=True,
        verbose=1
    )
    
    # Train
    print("\n  Training...")
    history = model.fit(
        X_train_scaled, X_train_scaled,
        validation_data=(X_val_scaled, X_val_scaled),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stop, checkpoint],
        verbose=1
    )
    
    print(f"\n  Best validation loss: {min(history.history['val_loss']):.6f}")
    print(f"  Model saved to: {model_path}")
    
    return model


# ============================================================
# E) THRESHOLD SELECTION
# ============================================================
def compute_threshold(model: Model, X_val_scaled: np.ndarray, 
                      threshold_path: str, percentile: int = 99) -> dict:
    """
    Compute anomaly threshold from validation reconstruction errors.
    Uses percentile-based approach (not hardcoded!).
    """
    print("\n" + "=" * 60)
    print("E) THRESHOLD SELECTION (Port-Specific)")
    print("=" * 60)
    
    # Get reconstruction errors on validation set
    reconstructed = model.predict(X_val_scaled, verbose=0)
    mse_errors = np.mean(np.square(X_val_scaled - reconstructed), axis=1)
    
    # Compute percentile thresholds
    threshold_95 = np.percentile(mse_errors, 95)
    threshold_99 = np.percentile(mse_errors, 99)
    threshold_selected = np.percentile(mse_errors, percentile)
    
    print(f"\n  Validation Set Reconstruction Errors:")
    print(f"    Mean: {np.mean(mse_errors):.6f}")
    print(f"    Std: {np.std(mse_errors):.6f}")
    print(f"    Min: {np.min(mse_errors):.6f}")
    print(f"    Max: {np.max(mse_errors):.6f}")
    print(f"\n  Percentile Thresholds:")
    print(f"    95th percentile: {threshold_95:.6f}")
    print(f"    99th percentile: {threshold_99:.6f}")
    print(f"    Selected ({percentile}th): {threshold_selected:.6f}")
    
    # Save threshold
    threshold_config = {
        'threshold': float(threshold_selected),
        'percentile': percentile,
        'threshold_95': float(threshold_95),
        'threshold_99': float(threshold_99),
        'val_error_mean': float(np.mean(mse_errors)),
        'val_error_std': float(np.std(mse_errors)),
        'port': 'Jebel Ali',
        'bbox': JEBEL_ALI_BBOX,
        'created_at': datetime.now().isoformat()
    }
    
    with open(threshold_path, 'w') as f:
        json.dump(threshold_config, f, indent=2)
    
    print(f"\n  Threshold saved to: {threshold_path}")
    
    return threshold_config


# ============================================================
# F) EVALUATION METRICS
# ============================================================
def evaluate_model(model: Model, scaler: StandardScaler, X_test: np.ndarray, 
                   threshold: float, report_path: str = None) -> dict:
    """
    Comprehensive evaluation with multiple metrics.
    
    Since anomaly detection is unsupervised:
    1. Report alert rate and error distribution on test set
    2. Create synthetic anomalies and compute Precision/Recall/F1
    """
    print("\n" + "=" * 60)
    print("F) EVALUATION METRICS")
    print("=" * 60)
    
    X_test_scaled = scaler.transform(X_test)
    
    # 1. Test Set Analysis (Unsupervised)
    print("\n  1. Test Set Analysis (Unsupervised)")
    print("  " + "-" * 40)
    
    reconstructed = model.predict(X_test_scaled, verbose=0)
    test_errors = np.mean(np.square(X_test_scaled - reconstructed), axis=1)
    
    # Flag anomalies
    anomalies = test_errors > threshold
    alert_rate = np.mean(anomalies) * 100
    
    print(f"    Total test samples: {len(X_test):,}")
    print(f"    Anomalies detected: {np.sum(anomalies):,}")
    print(f"    Alert rate: {alert_rate:.2f}%")
    print(f"\n    Reconstruction Error Distribution:")
    print(f"      Mean: {np.mean(test_errors):.6f}")
    print(f"      Std: {np.std(test_errors):.6f}")
    print(f"      Percentiles: 50th={np.percentile(test_errors, 50):.6f}, "
          f"90th={np.percentile(test_errors, 90):.6f}, "
          f"99th={np.percentile(test_errors, 99):.6f}")
    
    # 2. Synthetic Anomaly Evaluation
    print("\n  2. Synthetic Anomaly Evaluation")
    print("  " + "-" * 40)
    
    # Create synthetic anomalies (controlled evaluation)
    n_synthetic = min(500, len(X_test) // 2)
    X_anomalies = create_synthetic_anomalies(X_test[:n_synthetic], scaler)
    X_anomalies_scaled = scaler.transform(X_anomalies)
    
    # Combine normal and anomalous samples
    X_combined = np.vstack([X_test_scaled[:n_synthetic], X_anomalies_scaled])
    y_true = np.array([0] * n_synthetic + [1] * n_synthetic)  # 0=normal, 1=anomaly
    
    # Predict
    recon_combined = model.predict(X_combined, verbose=0)
    errors_combined = np.mean(np.square(X_combined - recon_combined), axis=1)
    y_pred = (errors_combined > threshold).astype(int)
    
    # Calculate metrics
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    try:
        roc_auc = roc_auc_score(y_true, errors_combined)
    except:
        roc_auc = 0.5
    
    cm = confusion_matrix(y_true, y_pred)
    
    print(f"    Synthetic anomalies created: {n_synthetic}")
    print(f"\n    Classification Metrics:")
    print(f"      Precision: {precision:.4f}")
    print(f"      Recall: {recall:.4f}")
    print(f"      F1-Score: {f1:.4f}")
    print(f"      ROC-AUC: {roc_auc:.4f}")
    print(f"\n    Confusion Matrix:")
    print(f"      [[TN={cm[0,0]:4d}  FP={cm[0,1]:4d}]")
    print(f"       [FN={cm[1,0]:4d}  TP={cm[1,1]:4d}]]")
    
    # Build evaluation report
    report = {
        'test_samples': len(X_test),
        'threshold': threshold,
        'alert_rate_pct': alert_rate,
        'test_error_mean': float(np.mean(test_errors)),
        'test_error_std': float(np.std(test_errors)),
        'test_error_percentiles': {
            '50': float(np.percentile(test_errors, 50)),
            '90': float(np.percentile(test_errors, 90)),
            '99': float(np.percentile(test_errors, 99))
        },
        'synthetic_eval': {
            'n_samples': n_synthetic * 2,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'roc_auc': roc_auc,
            'confusion_matrix': cm.tolist()
        },
        'created_at': datetime.now().isoformat()
    }
    
    # Save report
    if report_path:
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n  Evaluation report saved to: {report_path}")
    
    return report


def create_synthetic_anomalies(X_normal: np.ndarray, scaler: StandardScaler) -> np.ndarray:
    """
    Create synthetic anomalies by injecting:
    - Route deviations (abnormal lat/lon)
    - Speed anomalies (abnormal SOG)
    - Heading anomalies
    """
    np.random.seed(RANDOM_SEED + 1)
    X_anomalies = X_normal.copy()
    
    n = len(X_anomalies)
    
    # Indices: [timestamp_sec, mmsi, latitude, longitude, sog, cog, heading]
    # 30% - Large lat/lon deviation (route anomaly)
    n_route = int(n * 0.3)
    idx_route = np.random.choice(n, n_route, replace=False)
    X_anomalies[idx_route, 2] += np.random.uniform(-0.5, 0.5, n_route)  # lat
    X_anomalies[idx_route, 3] += np.random.uniform(-0.5, 0.5, n_route)  # lon
    
    # 30% - Speed anomaly (very high or very low)
    n_speed = int(n * 0.3)
    idx_speed = np.random.choice(n, n_speed, replace=False)
    X_anomalies[idx_speed, 4] = np.random.choice([0, 50], n_speed)  # sog: 0 or 50 knots
    
    # 40% - Combined anomaly
    remaining = [i for i in range(n) if i not in idx_route and i not in idx_speed]
    for idx in remaining:
        X_anomalies[idx, 2] += np.random.uniform(-0.3, 0.3)  # slight lat deviation
        X_anomalies[idx, 4] *= np.random.uniform(0.1, 5)  # speed multiplier
    
    return X_anomalies


# ============================================================
# MAIN TRAINING PIPELINE
# ============================================================
def run_training_pipeline(input_csv: str = None, use_synthetic: bool = True):
    """
    Run the complete Jebel Ali anomaly detection training pipeline.
    """
    print("\n" + "=" * 60)
    print("JEBEL ALI MARITIME ANOMALY DETECTION PIPELINE")
    print("Port Intelligence System - Feature 2")
    print("=" * 60)
    
    # Ensure directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # A) Data Filtering
    if input_csv and Path(input_csv).exists():
        df = load_and_filter_ais_data(
            input_csv, 
            str(DATA_DIR / 'ais_jebel_ali_filtered.csv')
        )
        if df is None or len(df) == 0:
            print("  No data in Jebel Ali area. Falling back to synthetic data.")
            df = generate_synthetic_jebel_ali_data(5000)
    elif use_synthetic:
        df = generate_synthetic_jebel_ali_data(5000)
        df.to_csv(DATA_DIR / 'ais_jebel_ali_synthetic.csv', index=False)
    else:
        raise ValueError("No input data provided and synthetic generation disabled")
    
    # B) Feature Preparation
    X_train, X_val, X_test, feature_cols = prepare_features(df)
    
    # C) Scaling
    scaler_path = str(MODELS_DIR / 'scaler.pkl')
    scaler = fit_scaler(X_train, scaler_path)
    
    X_train_scaled = scaler.transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # D) Autoencoder Training
    model_path = str(MODELS_DIR / 'autoencoder_model.keras')
    model = train_autoencoder(X_train_scaled, X_val_scaled, model_path, epochs=100, batch_size=32)
    
    # E) Threshold Selection
    threshold_path = str(MODELS_DIR / 'threshold.json')
    threshold_config = compute_threshold(model, X_val_scaled, threshold_path, THRESHOLD_PERCENTILE)
    
    # F) Evaluation
    report_path = str(DATA_DIR / 'evaluation_report.json')
    report = evaluate_model(model, scaler, X_test, threshold_config['threshold'], report_path)
    
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"\n  Files created:")
    print(f"    - {scaler_path}")
    print(f"    - {model_path}")
    print(f"    - {threshold_path}")
    print(f"    - {report_path}")
    print(f"\n  Key Results:")
    print(f"    - Threshold ({THRESHOLD_PERCENTILE}th percentile): {threshold_config['threshold']:.6f}")
    print(f"    - Test Alert Rate: {report['alert_rate_pct']:.2f}%")
    print(f"    - Synthetic Eval F1: {report['synthetic_eval']['f1_score']:.4f}")
    
    return model, scaler, threshold_config, report


if __name__ == '__main__':
    # Run with synthetic data (for demo)
    # For real data: run_training_pipeline(input_csv='path/to/real_ais_data.csv')
    run_training_pipeline(use_synthetic=True)
