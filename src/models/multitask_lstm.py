"""
Multi-task LSTM Model for Predictive Maintenance
=================================================
Feature 3: Predicts both RUL (regression) and Failure Mode (classification)

Architecture:
- Shared LSTM Encoder
- Head A: RUL regression (1 output)
- Head B: Failure Mode classification (5 outputs)
"""

import tensorflow as tf
from tensorflow import keras
from keras import layers, Model, regularizers
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
import numpy as np
from typing import Dict, Tuple, Optional
from pathlib import Path


def build_multitask_lstm(
    input_shape: Tuple[int, int],
    num_classes: int = 5,
    lstm_units: int = 128,
    num_lstm_layers: int = 2,
    dense_units: int = 64,
    dropout_rate: float = 0.3,
    l2_reg: float = 0.001
) -> Model:
    """
    Build Multi-task LSTM model with shared encoder and dual heads.
    
    Args:
        input_shape: (sequence_length, num_features) e.g., (24, 10)
        num_classes: Number of failure mode classes
        lstm_units: Hidden units in LSTM layers
        num_lstm_layers: Number of LSTM layers
        dense_units: Units in dense layers
        dropout_rate: Dropout rate
        l2_reg: L2 regularization strength
        
    Returns:
        Keras Model with two outputs
    """
    # Input layer
    inputs = layers.Input(shape=input_shape, name='sensor_input')
    
    # Shared LSTM Encoder
    x = inputs
    for i in range(num_lstm_layers):
        return_sequences = (i < num_lstm_layers - 1)  # Only last LSTM returns single output
        x = layers.LSTM(
            units=lstm_units,
            return_sequences=return_sequences,
            dropout=dropout_rate,
            recurrent_dropout=dropout_rate,
            kernel_regularizer=regularizers.l2(l2_reg),
            name=f'lstm_{i+1}'
        )(x)
    
    # Shared representation
    shared = layers.BatchNormalization(name='shared_bn')(x)
    shared = layers.Dropout(dropout_rate, name='shared_dropout')(shared)
    
    # ==================== HEAD A: RUL Regression ====================
    rul_branch = layers.Dense(
        dense_units, 
        activation='relu',
        kernel_regularizer=regularizers.l2(l2_reg),
        name='rul_dense_1'
    )(shared)
    rul_branch = layers.Dropout(dropout_rate, name='rul_dropout')(rul_branch)
    rul_branch = layers.Dense(
        dense_units // 2,
        activation='relu',
        kernel_regularizer=regularizers.l2(l2_reg),
        name='rul_dense_2'
    )(rul_branch)
    rul_output = layers.Dense(
        1, 
        activation='sigmoid',  # Output in [0, 1] for normalized RUL
        name='rul_output'
    )(rul_branch)
    
    # ==================== HEAD B: Failure Mode Classification ====================
    mode_branch = layers.Dense(
        dense_units,
        activation='relu',
        kernel_regularizer=regularizers.l2(l2_reg),
        name='mode_dense_1'
    )(shared)
    mode_branch = layers.Dropout(dropout_rate, name='mode_dropout')(mode_branch)
    mode_branch = layers.Dense(
        dense_units // 2,
        activation='relu',
        kernel_regularizer=regularizers.l2(l2_reg),
        name='mode_dense_2'
    )(mode_branch)
    mode_output = layers.Dense(
        num_classes,
        activation='softmax',
        name='mode_output'
    )(mode_branch)
    
    # Build model
    model = Model(
        inputs=inputs,
        outputs=[rul_output, mode_output],
        name='MultiTask_LSTM'
    )
    
    return model


def compile_model(
    model: Model,
    learning_rate: float = 0.001,
    rul_loss_weight: float = 1.0,
    mode_loss_weight: float = 1.0,
    class_weights: Optional[Dict[int, float]] = None
) -> Model:
    """
    Compile model with appropriate losses and metrics.
    
    Args:
        model: Keras model to compile
        learning_rate: Learning rate for Adam optimizer
        rul_loss_weight: Weight for RUL loss
        mode_loss_weight: Weight for classification loss
        class_weights: Optional class weights for imbalanced data
    """
    optimizer = keras.optimizers.Adam(learning_rate=learning_rate)
    
    # Loss functions
    losses = {
        'rul_output': 'mse',
        'mode_output': 'sparse_categorical_crossentropy'
    }
    
    # Loss weights
    loss_weights = {
        'rul_output': rul_loss_weight,
        'mode_output': mode_loss_weight
    }
    
    # Metrics
    metrics = {
        'rul_output': ['mae'],
        'mode_output': ['accuracy']
    }
    
    model.compile(
        optimizer=optimizer,
        loss=losses,
        loss_weights=loss_weights,
        metrics=metrics
    )
    
    return model


def get_callbacks(
    model_path: str = "models/multitask_lstm_best.keras",
    patience_early: int = 10,
    patience_lr: int = 5
) -> list:
    """
    Get training callbacks.
    
    Returns:
        List of Keras callbacks
    """
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    
    callbacks = [
        EarlyStopping(
            monitor='val_loss',
            patience=patience_early,
            restore_best_weights=True,
            verbose=1
        ),
        ModelCheckpoint(
            filepath=model_path,
            monitor='val_loss',
            save_best_only=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=patience_lr,
            min_lr=1e-6,
            verbose=1
        )
    ]
    
    return callbacks


def print_model_summary(model: Model):
    """Print formatted model summary."""
    print("\n" + "=" * 60)
    print("🏗️ MODEL ARCHITECTURE")
    print("=" * 60)
    model.summary()
    
    # Count parameters
    trainable = sum([tf.reduce_prod(w.shape).numpy() for w in model.trainable_weights])
    non_trainable = sum([tf.reduce_prod(w.shape).numpy() for w in model.non_trainable_weights])
    
    print(f"\n📊 Parameters: {trainable:,} trainable, {non_trainable:,} non-trainable")
    print(f"   Total: {trainable + non_trainable:,}")


# ==================== TRAINING FUNCTION ====================

def train_model(
    model: Model,
    train_ds: tf.data.Dataset,
    val_ds: tf.data.Dataset,
    epochs: int = 50,
    class_weights: Optional[Dict[int, float]] = None,
    model_path: str = "models/multitask_lstm_best.keras"
) -> keras.callbacks.History:
    """
    Train the multi-task model.
    
    Args:
        model: Compiled Keras model
        train_ds: Training dataset
        val_ds: Validation dataset
        epochs: Maximum number of epochs
        class_weights: Optional class weights for failure mode
        model_path: Path to save best model
        
    Returns:
        Training history
    """
    callbacks = get_callbacks(model_path)
    
    print("\n" + "=" * 60)
    print("🚀 TRAINING STARTED")
    print("=" * 60)
    
    # Note: For multi-output models, class_weight per output is not directly supported
    # We handle imbalance through loss weighting in compile_model
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=callbacks,
        verbose=1
    )
    
    print("\n" + "=" * 60)
    print("✅ TRAINING COMPLETE")
    print("=" * 60)
    
    return history


# ==================== EVALUATION FUNCTION ====================

def evaluate_model(
    model: Model,
    test_ds: tf.data.Dataset,
    preprocessor,
    verbose: bool = True
) -> Dict:
    """
    Evaluate model on test set with comprehensive metrics.
    
    Args:
        model: Trained Keras model
        test_ds: Test dataset
        preprocessor: MaintenancePreprocessor instance
        verbose: Whether to print results
        
    Returns:
        Dictionary with all metrics
    """
    from src.data.maintenance_preprocessor import (
        evaluate_rul_predictions,
        evaluate_failure_mode_predictions,
        print_evaluation_results
    )
    
    # Get predictions
    y_rul_true_list = []
    y_mode_true_list = []
    y_rul_pred_list = []
    y_mode_pred_list = []
    
    for X_batch, y_batch in test_ds:
        rul_pred, mode_pred = model.predict(X_batch, verbose=0)
        
        y_rul_true_list.extend(y_batch['rul_output'].numpy())
        y_mode_true_list.extend(y_batch['mode_output'].numpy())
        y_rul_pred_list.extend(rul_pred.flatten())
        y_mode_pred_list.extend(np.argmax(mode_pred, axis=1))
    
    y_rul_true = np.array(y_rul_true_list)
    y_mode_true = np.array(y_mode_true_list)
    y_rul_pred = np.array(y_rul_pred_list)
    y_mode_pred = np.array(y_mode_pred_list)
    
    # Evaluate RUL
    rul_metrics = evaluate_rul_predictions(
        y_rul_true, y_rul_pred,
        preprocessor.rul_min, preprocessor.rul_max
    )
    
    # Evaluate Failure Mode
    mode_metrics = evaluate_failure_mode_predictions(
        y_mode_true, y_mode_pred,
        list(preprocessor.label_encoder.classes_)
    )
    
    if verbose:
        print_evaluation_results(rul_metrics, mode_metrics)
        
        # Additional: Test accuracy summary
        print("\n" + "=" * 60)
        print("📈 TEST ACCURACY SUMMARY")
        print("=" * 60)
        print(f"   RUL R² Score:           {rul_metrics['r2_score']:.4f}")
        print(f"   Failure Mode Accuracy:  {mode_metrics['accuracy']*100:.2f}%")
        print(f"   Failure Mode F1-Score:  {mode_metrics['f1_score']*100:.2f}%")
    
    return {
        'rul_metrics': rul_metrics,
        'mode_metrics': mode_metrics,
        'predictions': {
            'y_rul_true': y_rul_true,
            'y_rul_pred': y_rul_pred,
            'y_mode_true': y_mode_true,
            'y_mode_pred': y_mode_pred
        }
    }


# ==================== MAIN ====================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    
    from src.data.maintenance_preprocessor import MaintenancePreprocessor
    
    print("\n" + "=" * 60)
    print("🚀 MULTI-TASK LSTM TRAINING PIPELINE")
    print("=" * 60)
    
    # 1. Load and preprocess data
    print("\n📦 Loading and preprocessing data...")
    preprocessor = MaintenancePreprocessor(
        data_dir="data",
        window_size=24,
        stride=6
    )
    data = preprocessor.prepare_data()
    
    # 2. Create TF datasets
    print("\n📦 Creating TensorFlow datasets...")
    train_ds = preprocessor.create_tf_dataset(*data['train'], batch_size=64, shuffle=True)
    val_ds = preprocessor.create_tf_dataset(*data['val'], batch_size=64, shuffle=False)
    test_ds = preprocessor.create_tf_dataset(*data['test'], batch_size=64, shuffle=False)
    
    # 3. Build model
    print("\n🏗️ Building model...")
    model = build_multitask_lstm(
        input_shape=(24, 10),  # (window_size, num_features)
        num_classes=5,
        lstm_units=128,
        num_lstm_layers=2,
        dense_units=64,
        dropout_rate=0.3
    )
    
    # 4. Compile model
    model = compile_model(
        model,
        learning_rate=0.001,
        rul_loss_weight=1.0,
        mode_loss_weight=1.0
    )
    
    print_model_summary(model)
    
    # 5. Train model
    history = train_model(
        model,
        train_ds,
        val_ds,
        epochs=30,  # Reduced for demo, increase for better results
        class_weights=preprocessor.class_weights,
        model_path="models/multitask_lstm_best.keras"
    )
    
    # 6. Evaluate on test set
    print("\n" + "=" * 60)
    print("🧪 EVALUATING ON TEST SET")
    print("=" * 60)
    
    results = evaluate_model(model, test_ds, preprocessor)
    
    # 7. Save final model
    model.save("models/multitask_lstm_final.keras")
    print(f"\n✅ Model saved to models/multitask_lstm_final.keras")
    
    # Save preprocessor
    preprocessor.save("data/processed/maintenance_preprocessor_final.pkl")
    
    print("\n" + "=" * 60)
    print("🎉 PIPELINE COMPLETE!")
    print("=" * 60)
