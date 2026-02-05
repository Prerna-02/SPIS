"""
Base Preprocessor Module
========================
Common preprocessing utilities shared across all features.

Provides:
- StandardScaler wrapper with save/load
- Train/Val/Test splitting with stratification
- Common data validation utilities
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import pickle
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
import json


class BasePreprocessor:
    """
    Base class for all feature-specific preprocessors.
    Provides common functionality for scaling, splitting, and saving.
    """
    
    def __init__(self, 
                 data_dir: str = "data",
                 random_state: int = 42):
        """
        Initialize base preprocessor.
        
        Args:
            data_dir: Root data directory
            random_state: Random seed for reproducibility
        """
        self.data_dir = Path(data_dir)
        self.random_state = random_state
        self.scalers: Dict[str, StandardScaler] = {}
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_columns: List[str] = []
        self.is_fitted = False
        
    def validate_dataframe(self, df: pd.DataFrame, required_columns: List[str]) -> bool:
        """
        Validate that dataframe contains required columns.
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            
        Returns:
            True if valid, raises ValueError otherwise
        """
        missing = set(required_columns) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        return True
    
    def check_missing_values(self, df: pd.DataFrame, fill_strategy: str = "mean") -> pd.DataFrame:
        """
        Check and handle missing values.
        
        Args:
            df: DataFrame to check
            fill_strategy: Strategy for filling NaN - 'mean', 'median', 'zero', or 'drop'
            
        Returns:
            DataFrame with missing values handled
        """
        missing_count = df.isnull().sum().sum()
        
        if missing_count > 0:
            print(f"⚠️ Found {missing_count} missing values")
            
            if fill_strategy == "mean":
                df = df.fillna(df.mean(numeric_only=True))
            elif fill_strategy == "median":
                df = df.fillna(df.median(numeric_only=True))
            elif fill_strategy == "zero":
                df = df.fillna(0)
            elif fill_strategy == "drop":
                df = df.dropna()
            
            print(f"✅ Missing values handled with strategy: {fill_strategy}")
        else:
            print("✅ No missing values found")
            
        return df
    
    def fit_scaler(self, 
                   df: pd.DataFrame, 
                   columns: List[str], 
                   scaler_name: str = "default") -> pd.DataFrame:
        """
        Fit StandardScaler on specified columns.
        
        Args:
            df: DataFrame containing columns to scale
            columns: List of column names to scale
            scaler_name: Name to identify this scaler
            
        Returns:
            DataFrame with scaled columns
        """
        scaler = StandardScaler()
        df_scaled = df.copy()
        df_scaled[columns] = scaler.fit_transform(df[columns])
        self.scalers[scaler_name] = scaler
        
        print(f"✅ Fitted scaler '{scaler_name}' on {len(columns)} columns")
        return df_scaled
    
    def transform_scaler(self, 
                         df: pd.DataFrame, 
                         columns: List[str], 
                         scaler_name: str = "default") -> pd.DataFrame:
        """
        Transform using fitted scaler.
        
        Args:
            df: DataFrame containing columns to scale
            columns: List of column names to scale
            scaler_name: Name of previously fitted scaler
            
        Returns:
            DataFrame with scaled columns
        """
        if scaler_name not in self.scalers:
            raise ValueError(f"Scaler '{scaler_name}' not found. Fit first.")
            
        df_scaled = df.copy()
        df_scaled[columns] = self.scalers[scaler_name].transform(df[columns])
        return df_scaled
    
    def inverse_transform_scaler(self,
                                  data: np.ndarray,
                                  scaler_name: str = "default") -> np.ndarray:
        """
        Inverse transform scaled data back to original scale.
        
        Args:
            data: Scaled data array
            scaler_name: Name of scaler to use
            
        Returns:
            Data in original scale
        """
        if scaler_name not in self.scalers:
            raise ValueError(f"Scaler '{scaler_name}' not found.")
        return self.scalers[scaler_name].inverse_transform(data)
    
    def fit_label_encoder(self, 
                          df: pd.DataFrame, 
                          column: str, 
                          encoder_name: Optional[str] = None) -> pd.DataFrame:
        """
        Fit LabelEncoder on categorical column.
        
        Args:
            df: DataFrame containing column
            column: Column name to encode
            encoder_name: Name for encoder (defaults to column name)
            
        Returns:
            DataFrame with encoded column
        """
        encoder_name = encoder_name or column
        encoder = LabelEncoder()
        df_encoded = df.copy()
        df_encoded[column] = encoder.fit_transform(df[column])
        self.label_encoders[encoder_name] = encoder
        
        print(f"✅ Fitted label encoder '{encoder_name}': {list(encoder.classes_)}")
        return df_encoded
    
    def transform_label_encoder(self,
                                 df: pd.DataFrame,
                                 column: str,
                                 encoder_name: Optional[str] = None) -> pd.DataFrame:
        """
        Transform using fitted label encoder.
        """
        encoder_name = encoder_name or column
        if encoder_name not in self.label_encoders:
            raise ValueError(f"Label encoder '{encoder_name}' not found. Fit first.")
            
        df_encoded = df.copy()
        df_encoded[column] = self.label_encoders[encoder_name].transform(df[column])
        return df_encoded
    
    def get_label_mapping(self, encoder_name: str) -> Dict[int, str]:
        """
        Get mapping from encoded labels to original values.
        """
        if encoder_name not in self.label_encoders:
            raise ValueError(f"Label encoder '{encoder_name}' not found.")
        encoder = self.label_encoders[encoder_name]
        return {i: label for i, label in enumerate(encoder.classes_)}
    
    def train_val_test_split(self,
                              df: pd.DataFrame,
                              val_size: float = 0.15,
                              test_size: float = 0.15,
                              stratify_column: Optional[str] = None,
                              shuffle: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split data into train, validation, and test sets.
        
        Args:
            df: DataFrame to split
            val_size: Fraction for validation (0.0-1.0)
            test_size: Fraction for test (0.0-1.0)
            stratify_column: Column to stratify by (for classification)
            shuffle: Whether to shuffle before splitting
            
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        stratify = df[stratify_column] if stratify_column else None
        
        # First split: train+val vs test
        train_val, test = train_test_split(
            df,
            test_size=test_size,
            random_state=self.random_state,
            stratify=stratify,
            shuffle=shuffle
        )
        
        # Second split: train vs val
        val_ratio = val_size / (1 - test_size)
        stratify_train_val = train_val[stratify_column] if stratify_column else None
        
        train, val = train_test_split(
            train_val,
            test_size=val_ratio,
            random_state=self.random_state,
            stratify=stratify_train_val,
            shuffle=shuffle
        )
        
        print(f"✅ Data split: Train={len(train)}, Val={len(val)}, Test={len(test)}")
        return train, val, test

    def compute_class_weights(self, 
                               labels: np.ndarray, 
                               method: str = "balanced") -> np.ndarray:
        """
        Compute class weights for imbalanced data.
        
        Args:
            labels: Array of class labels
            method: 'balanced' or 'inverse'
            
        Returns:
            Array of weights per class
        """
        classes, counts = np.unique(labels, return_counts=True)
        n_samples = len(labels)
        n_classes = len(classes)
        
        if method == "balanced":
            weights = n_samples / (n_classes * counts)
        elif method == "inverse":
            weights = 1.0 / counts
            weights = weights / weights.sum() * n_classes
        else:
            raise ValueError(f"Unknown method: {method}")
            
        print(f"✅ Class weights computed: {dict(zip(classes, np.round(weights, 3)))}")
        return weights
    
    def save(self, filepath: str):
        """
        Save preprocessor state to file.
        
        Args:
            filepath: Path to save to
        """
        state = {
            'scalers': self.scalers,
            'label_encoders': self.label_encoders,
            'feature_columns': self.feature_columns,
            'random_state': self.random_state,
            'is_fitted': self.is_fitted
        }
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)
            
        print(f"✅ Preprocessor saved to {filepath}")
    
    def load(self, filepath: str):
        """
        Load preprocessor state from file.
        
        Args:
            filepath: Path to load from
        """
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
            
        self.scalers = state['scalers']
        self.label_encoders = state['label_encoders']
        self.feature_columns = state['feature_columns']
        self.random_state = state['random_state']
        self.is_fitted = state['is_fitted']
        
        print(f"✅ Preprocessor loaded from {filepath}")


# Utility functions

def get_sample_weights(labels: np.ndarray, class_weights: np.ndarray) -> np.ndarray:
    """
    Convert class weights to per-sample weights.
    
    Args:
        labels: Array of sample labels
        class_weights: Weights per class
        
    Returns:
        Array of weights per sample
    """
    return np.array([class_weights[label] for label in labels])


if __name__ == "__main__":
    # Quick test
    print("Testing BasePreprocessor...")
    
    # Create sample data
    np.random.seed(42)
    df = pd.DataFrame({
        'feature1': np.random.randn(100),
        'feature2': np.random.randn(100),
        'label': np.random.choice(['A', 'B', 'C'], 100)
    })
    
    # Test preprocessor
    prep = BasePreprocessor()
    
    # Test validation
    prep.validate_dataframe(df, ['feature1', 'feature2', 'label'])
    
    # Test scaling
    df_scaled = prep.fit_scaler(df, ['feature1', 'feature2'], 'features')
    
    # Test label encoding
    df_encoded = prep.fit_label_encoder(df_scaled, 'label')
    
    # Test split
    train, val, test = prep.train_val_test_split(df_encoded, stratify_column='label')
    
    # Test class weights
    weights = prep.compute_class_weights(df_encoded['label'].values)
    
    print("\n✅ All tests passed!")
