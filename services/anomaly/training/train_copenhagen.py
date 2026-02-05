"""
Copenhagen Port Anomaly Detection Training Pipeline
====================================================
VESSEL-LEVEL anomaly detection using autoencoder.

Vessel-level = a vessel is anomalous if ANY AIS message for that MMSI exceeds threshold.
Vessel score = max reconstruction error across that vessel's messages.

Port: Danish Waters (Copenhagen Region)
Bounding Box:
  - lat_min = 54.50, lat_max = 58.50
  - lon_min = 7.00, lon_max = 16.00
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================
COPENHAGEN_BBOX = {
    'lat_min': 54.50,
    'lat_max': 58.50,
    'lon_min': 7.00,
    'lon_max': 16.00
}

RANDOM_SEED = 42
TEST_SIZE = 0.15
VAL_SIZE = 0.15

# For small datasets, t95 is more appropriate than t99
# Set to 95 for more alerts, 99 for fewer false positives
THRESHOLD_PERCENTILE = 95  # Use 95 for small datasets

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
MODELS_DIR = BASE_DIR / 'models'
SAMPLE_CSV = BASE_DIR / 'sample_data.csv'


# ============================================================
# STEP 2: DATA FILTERING
# ============================================================
def filter_copenhagen_data(input_csv: str, output_csv: str) -> pd.DataFrame:
    """
    Load AIS data and filter for Copenhagen bounding box.
    NO synthetic data generation - uses real data only.
    """
    print("=" * 60)
    print("STEP 2: DATA FILTERING - Copenhagen Port Area")
    print("=" * 60)
    
    print(f"\nLoading AIS data from: {input_csv}")
    try:
        df = pd.read_csv(input_csv, on_bad_lines='skip')
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None
    
    rows_before = len(df)
    print(f"  Total rows loaded: {rows_before}")
    
    df.columns = df.columns.str.strip()
    
    lat_col = 'Latitude' if 'Latitude' in df.columns else 'latitude'
    lon_col = 'Longitude' if 'Longitude' in df.columns else 'longitude'
    
    if lat_col not in df.columns or lon_col not in df.columns:
        print(f"  ERROR: Required columns not found. Available: {df.columns.tolist()}")
        return None
    
    df = df.dropna(subset=[lat_col, lon_col])
    print(f"  After dropping missing lat/lon: {len(df)}")
    
    print(f"\n  Dataset coordinate ranges:")
    print(f"    Latitude:  {df[lat_col].min():.4f} to {df[lat_col].max():.4f}")
    print(f"    Longitude: {df[lon_col].min():.4f} to {df[lon_col].max():.4f}")
    
    bbox = COPENHAGEN_BBOX
    print(f"\n  Copenhagen Bounding Box:")
    print(f"    Lat: {bbox['lat_min']} to {bbox['lat_max']}")
    print(f"    Lon: {bbox['lon_min']} to {bbox['lon_max']}")
    
    df_filtered = df[
        (df[lat_col] >= bbox['lat_min']) &
        (df[lat_col] <= bbox['lat_max']) &
        (df[lon_col] >= bbox['lon_min']) &
        (df[lon_col] <= bbox['lon_max'])
    ].copy()
    
    rows_after = len(df_filtered)
    print(f"\n  Rows after filtering: {rows_after} (from {rows_before})")
    
    if rows_after == 0:
        print("\n  [WARNING] Bounding box returned 0 rows. Adjust bbox or dataset.")
        print("  Stopping training - NO SYNTHETIC DATA will be generated.")
        return None
    
    if rows_after < 50:
        print(f"\n  [WARNING] Only {rows_after} rows. Consider widening bounding box.")
    
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df_filtered.to_csv(output_csv, index=False)
    print(f"\n  [OK] Saved filtered data to: {output_csv}")
    
    return df_filtered


# ============================================================
# STEP 3: FEATURE PREPARATION
# ============================================================
def prepare_features(df: pd.DataFrame) -> tuple:
    """
    Prepare 7 features matching backend:
    - Timestamp (numeric seconds)
    - MMSI
    - Latitude, Longitude
    - SOG, COG, Heading
    
    Returns: (X, feature_cols, mmsi_array)
    """
    print("\n" + "=" * 60)
    print("STEP 3: FEATURE PREPARATION")
    print("=" * 60)
    
    col_mapping = {
        '# Timestamp': 'Timestamp',
        'timestamp': 'Timestamp',
        'Latitude': 'Latitude',
        'latitude': 'Latitude',
        'Longitude': 'Longitude',
        'longitude': 'Longitude',
        'mmsi': 'MMSI',
        'sog': 'SOG',
        'cog': 'COG',
        'heading': 'Heading'
    }
    df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})
    
    if 'Timestamp' in df.columns:
        try:
            df['timestamp_sec'] = pd.to_datetime(
                df['Timestamp'], 
                format='%d/%m/%Y %H:%M:%S',
                errors='coerce'
            ).astype('int64') / 1e9
        except:
            df['timestamp_sec'] = pd.Timestamp.now().timestamp()
    else:
        df['timestamp_sec'] = pd.Timestamp.now().timestamp()
    
    feature_cols = ['timestamp_sec', 'MMSI', 'Latitude', 'Longitude', 'SOG', 'COG', 'Heading']
    
    for col in feature_cols:
        if col not in df.columns:
            print(f"  Warning: Column {col} missing, filling with 0")
            df[col] = 0
    
    df_clean = df[feature_cols].dropna()
    
    # Extract MMSI separately for vessel-level tracking
    X = df_clean.values
    mmsi_array = X[:, 1].astype(int)  # MMSI is column 1
    
    print(f"  Features: {feature_cols}")
    print(f"  Samples after cleaning: {len(df_clean)}")
    print(f"  Unique vessels (MMSI): {len(np.unique(mmsi_array))}")
    
    return X, feature_cols, mmsi_array


# ============================================================
# STEP 4: DATA SPLIT (PRESERVING MMSI)
# ============================================================
def split_data_with_mmsi(X: np.ndarray, mmsi: np.ndarray) -> tuple:
    """
    Split into train/validation/test with fixed random seed.
    PRESERVES MMSI array alongside X for vessel-level analysis.
    
    Returns: (X_train, X_val, X_test, mmsi_train, mmsi_val, mmsi_test)
    """
    print("\n" + "=" * 60)
    print("STEP 4: DATA SPLIT (with MMSI preservation)")
    print("=" * 60)
    
    # First split: train+val vs test (85/15)
    X_train_val, X_test, mmsi_train_val, mmsi_test = train_test_split(
        X, mmsi, test_size=TEST_SIZE, random_state=RANDOM_SEED
    )
    
    # Second split: train vs val
    val_ratio = VAL_SIZE / (1 - TEST_SIZE)
    X_train, X_val, mmsi_train, mmsi_val = train_test_split(
        X_train_val, mmsi_train_val, test_size=val_ratio, random_state=RANDOM_SEED
    )
    
    print(f"  Train: {len(X_train)} samples, {len(np.unique(mmsi_train))} vessels")
    print(f"  Validation: {len(X_val)} samples, {len(np.unique(mmsi_val))} vessels")
    print(f"  Test: {len(X_test)} samples, {len(np.unique(mmsi_test))} vessels")
    
    return X_train, X_val, X_test, mmsi_train, mmsi_val, mmsi_test


# ============================================================
# STEP 5: SCALING
# ============================================================
def fit_and_save_scaler(X_train: np.ndarray, scaler_path: str) -> StandardScaler:
    """Fit StandardScaler ONLY on training set."""
    print("\n" + "=" * 60)
    print("STEP 5: SCALING")
    print("=" * 60)
    
    scaler = StandardScaler()
    scaler.fit(X_train)
    
    Path(scaler_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, scaler_path)
    
    print(f"  Fitted on training set ({len(X_train)} samples)")
    print(f"  [OK] Scaler saved to: {scaler_path}")
    
    return scaler


# ============================================================
# STEP 6: AUTOENCODER TRAINING
# ============================================================
def build_autoencoder(input_dim: int) -> Model:
    """Build autoencoder: 32 -> 16 -> 8 -> 16 -> 32 -> output"""
    inputs = layers.Input(shape=(input_dim,))
    
    x = layers.Dense(32, activation='relu')(inputs)
    x = layers.Dense(16, activation='relu')(x)
    encoded = layers.Dense(8, activation='relu')(x)
    
    x = layers.Dense(16, activation='relu')(encoded)
    x = layers.Dense(32, activation='relu')(x)
    decoded = layers.Dense(input_dim, activation='linear')(x)
    
    model = Model(inputs, decoded, name='copenhagen_autoencoder')
    model.compile(optimizer='adam', loss='mse')
    
    return model


def train_autoencoder(X_train_scaled: np.ndarray, X_val_scaled: np.ndarray,
                      model_path: str, epochs: int = 100, batch_size: int = 16) -> Model:
    """Train autoencoder with EarlyStopping on val_loss."""
    print("\n" + "=" * 60)
    print("STEP 6: AUTOENCODER TRAINING")
    print("=" * 60)
    
    input_dim = X_train_scaled.shape[1]
    model = build_autoencoder(input_dim)
    
    print(f"\n  Architecture: Input({input_dim}) -> 32 -> 16 -> 8 -> 16 -> 32 -> Output({input_dim})")
    print(f"  Loss: MSE | Optimizer: Adam")
    
    batch_size = min(batch_size, max(1, len(X_train_scaled) // 4))
    
    callbacks = [
        EarlyStopping(
            monitor='val_loss',
            patience=15,
            restore_best_weights=True,
            verbose=1
        ),
        ModelCheckpoint(
            model_path,
            monitor='val_loss',
            save_best_only=True,
            verbose=0
        )
    ]
    
    print(f"\n  Training with batch_size={batch_size}, epochs={epochs}...")
    history = model.fit(
        X_train_scaled, X_train_scaled,
        validation_data=(X_val_scaled, X_val_scaled),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1
    )
    
    best_loss = min(history.history['val_loss'])
    print(f"\n  Best validation loss: {best_loss:.6f}")
    print(f"  [OK] Model saved to: {model_path}")
    
    return model


# ============================================================
# VESSEL-LEVEL HELPER: Compute vessel scores
# ============================================================
def compute_vessel_scores(errors: np.ndarray, mmsi: np.ndarray) -> dict:
    """
    Aggregate row-level errors to vessel-level scores.
    Vessel score = MAX reconstruction error across all messages for that MMSI.
    
    Returns: dict {mmsi: max_error}
    """
    vessel_scores = defaultdict(float)
    for i, m in enumerate(mmsi):
        vessel_scores[m] = max(vessel_scores[m], errors[i])
    return dict(vessel_scores)


# ============================================================
# STEP 7: THRESHOLD COMPUTATION (VESSEL-LEVEL)
# ============================================================
def compute_vessel_threshold(model: Model, X_val_scaled: np.ndarray, 
                             mmsi_val: np.ndarray, threshold_path: str) -> dict:
    """
    Compute VESSEL-LEVEL thresholds from validation data.
    
    - Compute row-level errors
    - Group by MMSI: vessel_score = max(errors for that MMSI)
    - Compute percentile thresholds from vessel_scores (not row errors)
    """
    print("\n" + "=" * 60)
    print("STEP 7: THRESHOLD COMPUTATION (VESSEL-LEVEL)")
    print("=" * 60)
    
    # Get row-level reconstruction errors
    reconstructed = model.predict(X_val_scaled, verbose=0)
    row_errors = np.mean(np.square(X_val_scaled - reconstructed), axis=1)
    
    print(f"\n  Row-level Error Statistics:")
    print(f"    Mean: {np.mean(row_errors):.6f}")
    print(f"    Std:  {np.std(row_errors):.6f}")
    print(f"    Max:  {np.max(row_errors):.6f}")
    
    # Compute vessel-level scores (max error per MMSI)
    vessel_scores = compute_vessel_scores(row_errors, mmsi_val)
    vessel_score_values = np.array(list(vessel_scores.values()))
    num_vessels = len(vessel_scores)
    
    print(f"\n  Vessel-Level Statistics (max error per MMSI):")
    print(f"    Unique vessels: {num_vessels}")
    print(f"    Mean vessel score: {np.mean(vessel_score_values):.6f}")
    print(f"    Max vessel score: {np.max(vessel_score_values):.6f}")
    
    # Compute percentile thresholds from VESSEL SCORES
    t95_vessel = float(np.percentile(vessel_score_values, 95))
    t99_vessel = float(np.percentile(vessel_score_values, 99))
    
    # For small datasets, t95 may be more appropriate
    if THRESHOLD_PERCENTILE == 95:
        selected_threshold = t95_vessel
    else:
        selected_threshold = t99_vessel
    
    print(f"\n  Vessel-Level Thresholds:")
    print(f"    t95_vessel (95th percentile): {t95_vessel:.6f}")
    print(f"    t99_vessel (99th percentile): {t99_vessel:.6f}")
    print(f"    Selected (p{THRESHOLD_PERCENTILE}): {selected_threshold:.6f}")
    
    # Save threshold config
    threshold_config = {
        'threshold': selected_threshold,
        'percentile': THRESHOLD_PERCENTILE,
        'threshold_95': t95_vessel,
        'threshold_99': t99_vessel,
        'val_vessels': num_vessels,
        'val_error_mean': float(np.mean(row_errors)),
        'val_error_std': float(np.std(row_errors)),
        'detection_type': 'vessel-level',
        'port': 'Copenhagen',
        'bbox': COPENHAGEN_BBOX,
        'created_at': datetime.now().isoformat()
    }
    
    with open(threshold_path, 'w') as f:
        json.dump(threshold_config, f, indent=2)
    
    print(f"\n  [OK] Vessel-level threshold saved to: {threshold_path}")
    
    return threshold_config


# ============================================================
# STEP 8: EVALUATION (VESSEL-LEVEL)
# ============================================================
def evaluate_model_vessel_level(model: Model, scaler: StandardScaler, 
                                X_test: np.ndarray, mmsi_test: np.ndarray,
                                t95: float, t99: float) -> dict:
    """
    VESSEL-LEVEL evaluation.
    
    - Compute row-level errors, then aggregate to vessel scores
    - Report vessel alert rates, not row alert rates
    """
    print("\n" + "=" * 60)
    print("STEP 8: EVALUATION (VESSEL-LEVEL)")
    print("=" * 60)
    
    X_test_scaled = scaler.transform(X_test)
    
    # Get row-level errors
    reconstructed = model.predict(X_test_scaled, verbose=0)
    row_errors = np.mean(np.square(X_test_scaled - reconstructed), axis=1)
    
    print(f"\n  Row-Level Error Distribution (Test Set):")
    print(f"    Samples: {len(row_errors)}")
    print(f"    Mean: {np.mean(row_errors):.6f}")
    print(f"    Std:  {np.std(row_errors):.6f}")
    print(f"    p50:  {np.percentile(row_errors, 50):.6f}")
    print(f"    p95:  {np.percentile(row_errors, 95):.6f}")
    print(f"    Max:  {np.max(row_errors):.6f}")
    
    # Aggregate to vessel-level scores
    vessel_scores = compute_vessel_scores(row_errors, mmsi_test)
    vessel_score_values = np.array(list(vessel_scores.values()))
    vessel_mmsis = np.array(list(vessel_scores.keys()))
    total_vessels = len(vessel_scores)
    
    print(f"\n  Vessel-Level Scores (max error per MMSI):")
    print(f"    Unique vessels in test: {total_vessels}")
    print(f"    Mean vessel score: {np.mean(vessel_score_values):.6f}")
    print(f"    Max vessel score: {np.max(vessel_score_values):.6f}")
    
    # Vessel-level alert rates
    vessels_flagged_t95 = np.sum(vessel_score_values > t95)
    vessels_flagged_t99 = np.sum(vessel_score_values > t99)
    
    vessel_alert_rate_t95 = (vessels_flagged_t95 / total_vessels) * 100 if total_vessels > 0 else 0
    vessel_alert_rate_t99 = (vessels_flagged_t99 / total_vessels) * 100 if total_vessels > 0 else 0
    
    print(f"\n  Vessel-Level Alert Rates:")
    print(f"    At t95 ({t95:.6f}): {vessels_flagged_t95}/{total_vessels} vessels = {vessel_alert_rate_t95:.2f}%")
    print(f"    At t99 ({t99:.6f}): {vessels_flagged_t99}/{total_vessels} vessels = {vessel_alert_rate_t99:.2f}%")
    
    # List flagged vessels
    flagged_mmsis_t95 = vessel_mmsis[vessel_score_values > t95]
    if len(flagged_mmsis_t95) > 0:
        print(f"\n  Vessels flagged at t95: {flagged_mmsis_t95.tolist()}")
    
    return {
        'test_samples': len(row_errors),
        'test_vessels': total_vessels,
        'error_mean': float(np.mean(row_errors)),
        'error_std': float(np.std(row_errors)),
        'error_max': float(np.max(row_errors)),
        'vessel_score_mean': float(np.mean(vessel_score_values)),
        'vessel_score_max': float(np.max(vessel_score_values)),
        'vessels_flagged_t95': int(vessels_flagged_t95),
        'vessels_flagged_t99': int(vessels_flagged_t99),
        'vessel_alert_rate_t95': vessel_alert_rate_t95,
        'vessel_alert_rate_t99': vessel_alert_rate_t99,
        'detection_type': 'vessel-level'
    }


# ============================================================
# MAIN PIPELINE
# ============================================================
def run_training_pipeline():
    """Execute the complete vessel-level anomaly detection pipeline."""
    print("\n" + "=" * 60)
    print("COPENHAGEN PORT ANOMALY DETECTION PIPELINE")
    print(">>> VESSEL-LEVEL DETECTION <<<")
    print("Port Intelligence System - Feature 2")
    print("=" * 60)
    print(f"\nStarted at: {datetime.now().isoformat()}")
    print(f"Threshold percentile: {THRESHOLD_PERCENTILE}")
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # STEP 2: Data Filtering
    filtered_csv = str(DATA_DIR / 'ais_copenhagen_filtered.csv')
    df_filtered = filter_copenhagen_data(str(SAMPLE_CSV), filtered_csv)
    
    if df_filtered is None or len(df_filtered) == 0:
        print("\n[FAILED] Training stopped: No data in Copenhagen bounding box.")
        return None
    
    # STEP 3: Feature Preparation (now returns mmsi array)
    X, feature_cols, mmsi_array = prepare_features(df_filtered)
    
    if len(X) < 10:
        print(f"\n[FAILED] Training stopped: Only {len(X)} valid samples. Need at least 10.")
        return None
    
    # STEP 4: Data Split (preserving MMSI)
    X_train, X_val, X_test, mmsi_train, mmsi_val, mmsi_test = split_data_with_mmsi(X, mmsi_array)
    
    # STEP 5: Scaling
    scaler_path = str(MODELS_DIR / 'scaler.pkl')
    scaler = fit_and_save_scaler(X_train, scaler_path)
    
    X_train_scaled = scaler.transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # STEP 6: Autoencoder Training
    model_path = str(MODELS_DIR / 'autoencoder_model.keras')
    model = train_autoencoder(X_train_scaled, X_val_scaled, model_path)
    
    # STEP 7: Vessel-Level Threshold Computation
    threshold_path = str(MODELS_DIR / 'threshold.json')
    threshold_config = compute_vessel_threshold(model, X_val_scaled, mmsi_val, threshold_path)
    
    # STEP 8: Vessel-Level Evaluation
    eval_results = evaluate_model_vessel_level(
        model, scaler, X_test, mmsi_test,
        threshold_config['threshold_95'],
        threshold_config['threshold_99']
    )
    
    # Final Summary
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE - VESSEL-LEVEL SUMMARY")
    print("=" * 60)
    print(f"\n  Detection Type: VESSEL-LEVEL (max error per MMSI)")
    
    print(f"\n  Files Created:")
    print(f"    - {filtered_csv}")
    print(f"    - {scaler_path}")
    print(f"    - {model_path}")
    print(f"    - {threshold_path}")
    
    print(f"\n  Dataset Summary:")
    print(f"    Total samples: {len(X)}")
    print(f"    Unique vessels: {len(np.unique(mmsi_array))}")
    print(f"    Train: {len(X_train)} samples | Val: {len(X_val)} samples | Test: {len(X_test)} samples")
    
    print(f"\n  Vessel-Level Thresholds:")
    print(f"    t95_vessel: {threshold_config['threshold_95']:.6f}")
    print(f"    t99_vessel: {threshold_config['threshold_99']:.6f}")
    print(f"    Selected (p{THRESHOLD_PERCENTILE}): {threshold_config['threshold']:.6f}")
    
    print(f"\n  Test Set Vessel Performance:")
    print(f"    Test vessels: {eval_results['test_vessels']}")
    print(f"    Vessels flagged (t95): {eval_results['vessels_flagged_t95']}")
    print(f"    Vessels flagged (t99): {eval_results['vessels_flagged_t99']}")
    print(f"    Vessel alert rate (t95): {eval_results['vessel_alert_rate_t95']:.2f}%")
    print(f"    Vessel alert rate (t99): {eval_results['vessel_alert_rate_t99']:.2f}%")
    
    print(f"\n  Completed at: {datetime.now().isoformat()}")
    
    return {
        'model': model,
        'scaler': scaler,
        'threshold_config': threshold_config,
        'eval_results': eval_results
    }


if __name__ == '__main__':
    run_training_pipeline()
