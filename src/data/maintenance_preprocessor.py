"""
Maintenance Preprocessor Module (TensorFlow Version)
=====================================================
Feature 3: Predictive Maintenance - Multi-task LSTM
Prepares data for dual prediction:
  - Head A: RUL (Remaining Useful Life) - Regression
  - Head B: Failure Mode - 5-class Classification
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)
from typing import Tuple, List, Optional, Dict
from pathlib import Path
import pickle
import json


class MaintenancePreprocessor:
    """
    Preprocessor for Port Maintenance dataset (TensorFlow version).
    Creates sliding window sequences for LSTM training.
    """
    
    # Column definitions
    IDENTIFIERS = ['asset_id', 'asset_type', 'timestamp', 'operator_shift_id']
    CONTEXT = ['operation_state', 'utilization_rate', 'maintenance_age_days']
    WORKLOAD = ['load_tons', 'lift_cycles_per_hour']
    SENSORS = ['motor_temp_c', 'gearbox_temp_c', 'hydraulic_pressure_bar',
               'vibration_rms', 'current_amp', 'rpm']
    TARGETS = ['rul_hours', 'failure_mode']
    
    # Failure modes
    FAILURE_MODES = ['none', 'bearing', 'overheating', 'hydraulic_leak', 'electrical']
    
    def __init__(self,
                 data_dir: str = "data",
                 window_size: int = 24,
                 stride: int = 1,
                 random_state: int = 42):
        """
        Initialize maintenance preprocessor.
        
        Args:
            data_dir: Root data directory
            window_size: Sliding window size (hours)
            stride: Window stride (hours)
            random_state: Random seed
        """
        self.data_dir = Path(data_dir)
        self.window_size = window_size
        self.stride = stride
        self.random_state = random_state
        
        # Feature columns for LSTM input
        self.feature_columns = self.CONTEXT[1:] + self.WORKLOAD + self.SENSORS
        self.num_features = len(self.feature_columns)
        
        # Scalers and encoders
        self.feature_scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.operation_encoder = LabelEncoder()
        
        # RUL normalization params
        self.rul_min = None
        self.rul_max = None
        
        # Class weights
        self.class_weights = None
        
        self.is_fitted = False
        
    def load_data(self, filename: str = "port_maintenance_synthetic_3months.csv") -> pd.DataFrame:
        """Load maintenance dataset from raw data directory."""
        filepath = self.data_dir / "raw" / filename
        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(['asset_id', 'timestamp']).reset_index(drop=True)
        
        print(f"✅ Loaded {len(df):,} records from {filename}")
        print(f"   Assets: {df['asset_id'].nunique()}, Date range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
        return df
    
    def preprocess(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Apply preprocessing transformations."""
        df = df.copy()
        
        # Check missing values
        missing = df.isnull().sum().sum()
        if missing > 0:
            print(f"⚠️ Found {missing} missing values, filling with mean")
            df = df.fillna(df.mean(numeric_only=True))
        else:
            print("✅ No missing values")
        
        # Encode operation_state
        if fit:
            df['operation_state_encoded'] = self.operation_encoder.fit_transform(df['operation_state'])
            print(f"✅ Encoded operation_state: {list(self.operation_encoder.classes_)}")
        else:
            df['operation_state_encoded'] = self.operation_encoder.transform(df['operation_state'])
        
        # Encode failure_mode
        if fit:
            df['failure_mode_encoded'] = self.label_encoder.fit_transform(df['failure_mode'])
            print(f"✅ Encoded failure_mode: {list(self.label_encoder.classes_)}")
        else:
            df['failure_mode_encoded'] = self.label_encoder.transform(df['failure_mode'])
        
        # Scale features
        if fit:
            df[self.feature_columns] = self.feature_scaler.fit_transform(df[self.feature_columns])
            print(f"✅ Scaled {len(self.feature_columns)} feature columns")
        else:
            df[self.feature_columns] = self.feature_scaler.transform(df[self.feature_columns])
        
        # Normalize RUL
        if fit:
            self.rul_min = df['rul_hours'].min()
            self.rul_max = df['rul_hours'].max()
        df['rul_normalized'] = (df['rul_hours'] - self.rul_min) / (self.rul_max - self.rul_min)
        print(f"✅ Normalized RUL: [{self.rul_min:.0f}, {self.rul_max:.0f}] hours → [0, 1]")
        
        self.is_fitted = True
        return df
    
    def create_sequences(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Create sliding window sequences per asset."""
        X_list, y_rul_list, y_mode_list = [], [], []
        
        for asset_id in df['asset_id'].unique():
            asset_df = df[df['asset_id'] == asset_id].reset_index(drop=True)
            features = asset_df[self.feature_columns].values
            rul = asset_df['rul_normalized'].values
            mode = asset_df['failure_mode_encoded'].values
            
            for i in range(0, len(asset_df) - self.window_size + 1, self.stride):
                X_list.append(features[i:i + self.window_size])
                y_rul_list.append(rul[i + self.window_size - 1])
                y_mode_list.append(mode[i + self.window_size - 1])
        
        X = np.array(X_list, dtype=np.float32)
        y_rul = np.array(y_rul_list, dtype=np.float32)
        y_mode = np.array(y_mode_list, dtype=np.int32)
        
        print(f"✅ Created {len(X):,} sequences (window={self.window_size}h, stride={self.stride}h)")
        print(f"   X shape: {X.shape}, y_rul: {y_rul.shape}, y_mode: {y_mode.shape}")
        return X, y_rul, y_mode
    
    def split_by_asset(self, df: pd.DataFrame, 
                       train_ratio: float = 0.7,
                       val_ratio: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split data by asset to prevent data leakage."""
        assets = df['asset_id'].unique()
        np.random.seed(self.random_state)
        np.random.shuffle(assets)
        
        n_train = int(len(assets) * train_ratio)
        n_val = int(len(assets) * val_ratio)
        
        train_assets = assets[:n_train]
        val_assets = assets[n_train:n_train + n_val]
        test_assets = assets[n_train + n_val:]
        
        train_df = df[df['asset_id'].isin(train_assets)]
        val_df = df[df['asset_id'].isin(val_assets)]
        test_df = df[df['asset_id'].isin(test_assets)]
        
        print(f"✅ Split by asset: Train={len(train_assets)}, Val={len(val_assets)}, Test={len(test_assets)}")
        return train_df, val_df, test_df
    
    def compute_class_weights(self, y: np.ndarray) -> Dict[int, float]:
        """Compute class weights for imbalanced data."""
        classes, counts = np.unique(y, return_counts=True)
        total = len(y)
        n_classes = len(classes)
        weights = {int(c): total / (n_classes * count) for c, count in zip(classes, counts)}
        print(f"✅ Class weights: {weights}")
        self.class_weights = weights
        return weights
    
    def prepare_data(self, filename: str = "port_maintenance_synthetic_3months.csv") -> Dict:
        """Full preprocessing pipeline."""
        print("=" * 60)
        print("PREPROCESSING PIPELINE")
        print("=" * 60)
        
        # Load
        df = self.load_data(filename)
        
        # Preprocess
        print("\n📦 Preprocessing...")
        df = self.preprocess(df, fit=True)
        
        # Split
        print("\n✂️ Splitting by asset...")
        train_df, val_df, test_df = self.split_by_asset(df)
        
        # Create sequences
        print("\n� Creating sequences...")
        print("Training set:")
        X_train, y_rul_train, y_mode_train = self.create_sequences(train_df)
        print("Validation set:")
        X_val, y_rul_val, y_mode_val = self.create_sequences(val_df)
        print("Test set:")
        X_test, y_rul_test, y_mode_test = self.create_sequences(test_df)
        
        # Class weights
        print("\n⚖️ Computing class weights...")
        self.compute_class_weights(y_mode_train)
        
        return {
            'train': (X_train, y_rul_train, y_mode_train),
            'val': (X_val, y_rul_val, y_mode_val),
            'test': (X_test, y_rul_test, y_mode_test)
        }
    
    def create_tf_dataset(self, X: np.ndarray, y_rul: np.ndarray, y_mode: np.ndarray,
                          batch_size: int = 64, shuffle: bool = True) -> tf.data.Dataset:
        """Create TensorFlow Dataset."""
        dataset = tf.data.Dataset.from_tensor_slices((X, {'rul_output': y_rul, 'mode_output': y_mode}))
        if shuffle:
            dataset = dataset.shuffle(buffer_size=len(X))
        dataset = dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)
        return dataset
    
    def denormalize_rul(self, rul_normalized: np.ndarray) -> np.ndarray:
        """Convert normalized RUL back to hours."""
        return rul_normalized * (self.rul_max - self.rul_min) + self.rul_min
    
    def get_failure_mode_name(self, encoded: int) -> str:
        """Get failure mode name from encoded value."""
        return self.label_encoder.classes_[encoded]
    
    def save(self, filepath: str):
        """Save preprocessor state."""
        state = {
            'feature_scaler': self.feature_scaler,
            'label_encoder': self.label_encoder,
            'operation_encoder': self.operation_encoder,
            'rul_min': self.rul_min,
            'rul_max': self.rul_max,
            'class_weights': self.class_weights,
            'window_size': self.window_size,
            'stride': self.stride,
            'feature_columns': self.feature_columns
        }
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)
        print(f"✅ Preprocessor saved to {filepath}")
    
    def load(self, filepath: str):
        """Load preprocessor state."""
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        for key, value in state.items():
            setattr(self, key, value)
        self.is_fitted = True
        print(f"✅ Preprocessor loaded from {filepath}")


# ==================== EVALUATION METRICS ====================

def evaluate_rul_predictions(y_true: np.ndarray, y_pred: np.ndarray, 
                              rul_min: float, rul_max: float) -> Dict:
    """
    Evaluate RUL regression predictions.
    
    Returns:
        Dictionary with MAE, RMSE, R2 (in both normalized and hours scale)
    """
    # Normalized scale metrics
    mae_norm = mean_absolute_error(y_true, y_pred)
    rmse_norm = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    # Convert to hours for interpretable metrics
    y_true_hours = y_true * (rul_max - rul_min) + rul_min
    y_pred_hours = y_pred * (rul_max - rul_min) + rul_min
    mae_hours = mean_absolute_error(y_true_hours, y_pred_hours)
    rmse_hours = np.sqrt(mean_squared_error(y_true_hours, y_pred_hours))
    
    return {
        'mae_normalized': mae_norm,
        'rmse_normalized': rmse_norm,
        'r2_score': r2,
        'mae_hours': mae_hours,
        'rmse_hours': rmse_hours
    }


def evaluate_failure_mode_predictions(y_true: np.ndarray, y_pred: np.ndarray,
                                       class_names: List[str]) -> Dict:
    """
    Evaluate failure mode classification predictions.
    
    Returns:
        Dictionary with accuracy, precision, recall, F1, confusion matrix
    """
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
    cm = confusion_matrix(y_true, y_pred)
    report = classification_report(y_true, y_pred, target_names=class_names, zero_division=0)
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'confusion_matrix': cm,
        'classification_report': report
    }


def print_evaluation_results(rul_metrics: Dict, mode_metrics: Dict):
    """Print formatted evaluation results."""
    print("\n" + "=" * 60)
    print("📊 EVALUATION RESULTS")
    print("=" * 60)
    
    print("\n🔧 RUL PREDICTION (Regression)")
    print("-" * 40)
    print(f"   MAE:  {rul_metrics['mae_hours']:.2f} hours")
    print(f"   RMSE: {rul_metrics['rmse_hours']:.2f} hours")
    print(f"   R²:   {rul_metrics['r2_score']:.4f}")
    
    print("\n⚙️ FAILURE MODE PREDICTION (Classification)")
    print("-" * 40)
    print(f"   Accuracy:  {mode_metrics['accuracy']*100:.2f}%")
    print(f"   Precision: {mode_metrics['precision']*100:.2f}%")
    print(f"   Recall:    {mode_metrics['recall']*100:.2f}%")
    print(f"   F1-Score:  {mode_metrics['f1_score']*100:.2f}%")
    
    print("\n📋 Confusion Matrix:")
    print(mode_metrics['confusion_matrix'])
    
    print("\n📝 Classification Report:")
    print(mode_metrics['classification_report'])


# ==================== MAIN TEST ====================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 TESTING MAINTENANCE PREPROCESSOR (TensorFlow)")
    print("=" * 60 + "\n")
    
    # Initialize preprocessor
    preprocessor = MaintenancePreprocessor(
        data_dir="data",
        window_size=24,
        stride=6  # 6-hour stride for faster testing
    )
    
    # Full pipeline
    data = preprocessor.prepare_data()
    
    # Create TF datasets
    print("\n" + "=" * 60)
    print("📦 CREATING TENSORFLOW DATASETS")
    print("=" * 60)
    
    train_ds = preprocessor.create_tf_dataset(*data['train'], batch_size=64, shuffle=True)
    val_ds = preprocessor.create_tf_dataset(*data['val'], batch_size=64, shuffle=False)
    test_ds = preprocessor.create_tf_dataset(*data['test'], batch_size=64, shuffle=False)
    
    print(f"✅ Train batches: {len(list(train_ds))}")
    print(f"✅ Val batches: {len(list(val_ds))}")
    print(f"✅ Test batches: {len(list(test_ds))}")
    
    # Test one batch
    print("\n" + "=" * 60)
    print("🔍 SAMPLE BATCH")
    print("=" * 60)
    
    for X_batch, y_batch in train_ds.take(1):
        print(f"X shape: {X_batch.shape}")
        print(f"y_rul shape: {y_batch['rul_output'].shape}")
        print(f"y_mode shape: {y_batch['mode_output'].shape}")
        print(f"X dtype: {X_batch.dtype}")
        print(f"Sample y_rul values: {y_batch['rul_output'][:5].numpy()}")
        print(f"Sample y_mode values: {y_batch['mode_output'][:5].numpy()}")
    
    # Demo evaluation (with dummy predictions)
    print("\n" + "=" * 60)
    print("📊 DEMO EVALUATION (with random predictions)")
    print("=" * 60)
    
    X_test, y_rul_test, y_mode_test = data['test']
    
    # Simulate predictions (random for demo)
    np.random.seed(42)
    y_rul_pred = np.clip(y_rul_test + np.random.normal(0, 0.1, len(y_rul_test)), 0, 1)
    y_mode_pred = np.random.randint(0, 5, len(y_mode_test))
    
    # Evaluate
    rul_metrics = evaluate_rul_predictions(
        y_rul_test, y_rul_pred,
        preprocessor.rul_min, preprocessor.rul_max
    )
    
    mode_metrics = evaluate_failure_mode_predictions(
        y_mode_test, y_mode_pred,
        list(preprocessor.label_encoder.classes_)
    )
    
    print_evaluation_results(rul_metrics, mode_metrics)
    
    # Save preprocessor
    preprocessor.save("data/processed/maintenance_preprocessor_tf.pkl")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
