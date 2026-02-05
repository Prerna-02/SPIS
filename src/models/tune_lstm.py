"""
Hyperparameter Tuning for Multi-task LSTM
==========================================
Tuned parameters:
- Window size: 7 days (168 hours)
- Dropout: 20% at head layers (reduced from 30%)
- Learning rate: 0.0005
- LSTM units: 256
- RUL loss weight: 2.0
"""

import sys
sys.path.insert(0, '.')

import tensorflow as tf
from tensorflow import keras
from keras import layers, Model, regularizers
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
import numpy as np
from pathlib import Path

from src.data.maintenance_preprocessor import (
    MaintenancePreprocessor,
    evaluate_rul_predictions,
    evaluate_failure_mode_predictions,
    print_evaluation_results
)


def build_tuned_multitask_lstm(
    input_shape,
    num_classes=5,
    lstm_units=256,          # Increased from 128
    num_lstm_layers=2,
    dense_units=128,         # Increased from 64
    dropout_lstm=0.3,        # Dropout for LSTM layers
    dropout_heads=0.2,       # Reduced dropout for head layers (was 0.3)
    l2_reg=0.001
):
    """
    Build tuned Multi-task LSTM model.
    Key changes: Larger LSTM, reduced dropout at heads.
    """
    inputs = layers.Input(shape=input_shape, name='sensor_input')
    
    # Shared LSTM Encoder
    x = inputs
    for i in range(num_lstm_layers):
        return_sequences = (i < num_lstm_layers - 1)
        x = layers.LSTM(
            units=lstm_units,
            return_sequences=return_sequences,
            dropout=dropout_lstm,
            recurrent_dropout=dropout_lstm,
            kernel_regularizer=regularizers.l2(l2_reg),
            name=f'lstm_{i+1}'
        )(x)
    
    shared = layers.BatchNormalization(name='shared_bn')(x)
    shared = layers.Dropout(dropout_heads, name='shared_dropout')(shared)  # Reduced dropout
    
    # HEAD A: RUL Regression
    rul_branch = layers.Dense(dense_units, activation='relu',
                              kernel_regularizer=regularizers.l2(l2_reg),
                              name='rul_dense_1')(shared)
    rul_branch = layers.Dropout(dropout_heads, name='rul_dropout')(rul_branch)  # 20% dropout
    rul_branch = layers.Dense(dense_units // 2, activation='relu',
                              kernel_regularizer=regularizers.l2(l2_reg),
                              name='rul_dense_2')(rul_branch)
    rul_output = layers.Dense(1, activation='sigmoid', name='rul_output')(rul_branch)
    
    # HEAD B: Failure Mode Classification
    mode_branch = layers.Dense(dense_units, activation='relu',
                               kernel_regularizer=regularizers.l2(l2_reg),
                               name='mode_dense_1')(shared)
    mode_branch = layers.Dropout(dropout_heads, name='mode_dropout')(mode_branch)  # 20% dropout
    mode_branch = layers.Dense(dense_units // 2, activation='relu',
                               kernel_regularizer=regularizers.l2(l2_reg),
                               name='mode_dense_2')(mode_branch)
    mode_output = layers.Dense(num_classes, activation='softmax', name='mode_output')(mode_branch)
    
    model = Model(inputs=inputs, outputs=[rul_output, mode_output], name='Tuned_MultiTask_LSTM')
    return model


def main():
    print("\n" + "=" * 60)
    print("🔧 HYPERPARAMETER TUNING - 7 DAY WINDOW")
    print("=" * 60)
    
    # Configuration
    WINDOW_SIZE = 168  # 7 days (24 hours × 7)
    STRIDE = 12        # 12 hour stride
    BATCH_SIZE = 32    # Smaller batch for larger sequences
    LEARNING_RATE = 0.0005
    RUL_LOSS_WEIGHT = 2.0
    MODE_LOSS_WEIGHT = 1.0
    EPOCHS = 50
    
    print(f"\n📋 Configuration:")
    print(f"   Window Size: {WINDOW_SIZE} hours ({WINDOW_SIZE//24} days)")
    print(f"   Stride: {STRIDE} hours")
    print(f"   Learning Rate: {LEARNING_RATE}")
    print(f"   RUL Loss Weight: {RUL_LOSS_WEIGHT}")
    print(f"   Dropout (heads): 20%")
    print(f"   LSTM Units: 256")
    
    # 1. Load and preprocess data
    print("\n📦 Loading data with 7-day window...")
    preprocessor = MaintenancePreprocessor(
        data_dir="data",
        window_size=WINDOW_SIZE,
        stride=STRIDE
    )
    data = preprocessor.prepare_data()
    
    # 2. Create TF datasets
    print("\n📦 Creating TensorFlow datasets...")
    train_ds = preprocessor.create_tf_dataset(*data['train'], batch_size=BATCH_SIZE, shuffle=True)
    val_ds = preprocessor.create_tf_dataset(*data['val'], batch_size=BATCH_SIZE, shuffle=False)
    test_ds = preprocessor.create_tf_dataset(*data['test'], batch_size=BATCH_SIZE, shuffle=False)
    
    print(f"✅ Train batches: {len(list(train_ds))}")
    
    # Recreate datasets after counting
    train_ds = preprocessor.create_tf_dataset(*data['train'], batch_size=BATCH_SIZE, shuffle=True)
    val_ds = preprocessor.create_tf_dataset(*data['val'], batch_size=BATCH_SIZE, shuffle=False)
    test_ds = preprocessor.create_tf_dataset(*data['test'], batch_size=BATCH_SIZE, shuffle=False)
    
    # 3. Build tuned model
    print("\n🏗️ Building tuned model...")
    model = build_tuned_multitask_lstm(
        input_shape=(WINDOW_SIZE, preprocessor.num_features),
        num_classes=5,
        lstm_units=256,
        dense_units=128,
        dropout_lstm=0.3,
        dropout_heads=0.2  # Reduced from 0.3
    )
    
    # 4. Compile
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss={
            'rul_output': 'mse',
            'mode_output': 'sparse_categorical_crossentropy'
        },
        loss_weights={
            'rul_output': RUL_LOSS_WEIGHT,
            'mode_output': MODE_LOSS_WEIGHT
        },
        metrics={
            'rul_output': ['mae'],
            'mode_output': ['accuracy']
        }
    )
    
    print("\n🏗️ Model Summary:")
    model.summary()
    
    # 5. Callbacks
    Path("models").mkdir(exist_ok=True)
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True, verbose=1),
        ModelCheckpoint('models/tuned_lstm_best.keras', monitor='val_loss', save_best_only=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=1)
    ]
    
    # 6. Train
    print("\n" + "=" * 60)
    print("🚀 TRAINING TUNED MODEL")
    print("=" * 60)
    
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS,
        callbacks=callbacks,
        verbose=1
    )
    
    # 7. Evaluate
    print("\n" + "=" * 60)
    print("🧪 EVALUATING ON TEST SET")
    print("=" * 60)
    
    # Get predictions
    y_rul_true_list, y_mode_true_list = [], []
    y_rul_pred_list, y_mode_pred_list = [], []
    
    test_ds = preprocessor.create_tf_dataset(*data['test'], batch_size=BATCH_SIZE, shuffle=False)
    
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
    
    # Metrics
    rul_metrics = evaluate_rul_predictions(
        y_rul_true, y_rul_pred,
        preprocessor.rul_min, preprocessor.rul_max
    )
    
    mode_metrics = evaluate_failure_mode_predictions(
        y_mode_true, y_mode_pred,
        list(preprocessor.label_encoder.classes_)
    )
    
    print_evaluation_results(rul_metrics, mode_metrics)
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 TUNED MODEL - TEST ACCURACY SUMMARY")
    print("=" * 60)
    print(f"   RUL R² Score:           {rul_metrics['r2_score']:.4f}")
    print(f"   RUL MAE:                {rul_metrics['mae_hours']:.2f} hours")
    print(f"   Failure Mode Accuracy:  {mode_metrics['accuracy']*100:.2f}%")
    print(f"   Failure Mode F1-Score:  {mode_metrics['f1_score']*100:.2f}%")
    
    # Save
    model.save("models/tuned_lstm_final.keras")
    preprocessor.save("data/processed/tuned_preprocessor.pkl")
    
    print("\n" + "=" * 60)
    print("🎉 TUNING COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
