"""
Separate LSTM Model for RUL Prediction
=======================================
Dedicated model for RUL regression only (no classification).
Goal: Improve R² score by giving 100% focus to RUL prediction.
"""

import sys
sys.path.insert(0, '.')

import tensorflow as tf
from tensorflow import keras
from keras import layers, Model, regularizers
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
import numpy as np
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.data.maintenance_preprocessor import MaintenancePreprocessor


def build_rul_lstm(
    input_shape,
    lstm_units=256,
    num_lstm_layers=3,  # Deeper for RUL
    dense_units=128,
    dropout_rate=0.2,
    l2_reg=0.001
):
    """Build LSTM model dedicated to RUL prediction."""
    inputs = layers.Input(shape=input_shape, name='sensor_input')
    
    x = inputs
    for i in range(num_lstm_layers):
        return_sequences = (i < num_lstm_layers - 1)
        x = layers.LSTM(
            units=lstm_units,
            return_sequences=return_sequences,
            dropout=dropout_rate,
            recurrent_dropout=dropout_rate,
            kernel_regularizer=regularizers.l2(l2_reg),
            name=f'lstm_{i+1}'
        )(x)
    
    x = layers.BatchNormalization()(x)
    x = layers.Dense(dense_units, activation='relu', kernel_regularizer=regularizers.l2(l2_reg))(x)
    x = layers.Dropout(dropout_rate)(x)
    x = layers.Dense(dense_units // 2, activation='relu', kernel_regularizer=regularizers.l2(l2_reg))(x)
    x = layers.Dropout(dropout_rate)(x)
    x = layers.Dense(dense_units // 4, activation='relu')(x)
    
    # RUL output - sigmoid for normalized [0,1] output
    output = layers.Dense(1, activation='sigmoid', name='rul_output')(x)
    
    model = Model(inputs=inputs, outputs=output, name='RUL_LSTM')
    return model


def main():
    print("\n" + "=" * 60)
    print("🎯 SEPARATE RUL LSTM MODEL")
    print("=" * 60)
    
    # Configuration
    WINDOW_SIZE = 168  # 7 days
    STRIDE = 12
    BATCH_SIZE = 32
    LEARNING_RATE = 0.0003  # Lower LR for regression
    EPOCHS = 50
    
    print(f"\n📋 Configuration:")
    print(f"   Window: {WINDOW_SIZE}h ({WINDOW_SIZE//24} days)")
    print(f"   LSTM Layers: 3 (deeper)")
    print(f"   Learning Rate: {LEARNING_RATE}")
    print(f"   Focus: 100% RUL regression")
    
    # Load data
    print("\n📦 Loading data...")
    preprocessor = MaintenancePreprocessor(data_dir="data", window_size=WINDOW_SIZE, stride=STRIDE)
    data = preprocessor.prepare_data()
    
    # Create datasets (RUL only)
    def create_rul_dataset(X, y_rul, y_mode, batch_size, shuffle):
        dataset = tf.data.Dataset.from_tensor_slices((X, y_rul))
        if shuffle:
            dataset = dataset.shuffle(len(X))
        return dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    
    train_ds = create_rul_dataset(*data['train'], BATCH_SIZE, shuffle=True)
    val_ds = create_rul_dataset(*data['val'], BATCH_SIZE, shuffle=False)
    test_ds = create_rul_dataset(*data['test'], BATCH_SIZE, shuffle=False)
    
    # Build model
    print("\n🏗️ Building RUL-only LSTM...")
    model = build_rul_lstm(
        input_shape=(WINDOW_SIZE, preprocessor.num_features),
        lstm_units=256,
        num_lstm_layers=3,
        dense_units=128,
        dropout_rate=0.2
    )
    
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss='mse',
        metrics=['mae']
    )
    
    model.summary()
    
    # Callbacks
    Path("models").mkdir(exist_ok=True)
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True, verbose=1),
        ModelCheckpoint('models/rul_lstm_best.keras', monitor='val_loss', save_best_only=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=1)
    ]
    
    # Train
    print("\n" + "=" * 60)
    print("🚀 TRAINING RUL MODEL")
    print("=" * 60)
    
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS,
        callbacks=callbacks,
        verbose=1
    )
    
    # Evaluate
    print("\n" + "=" * 60)
    print("🧪 EVALUATING ON TEST SET")
    print("=" * 60)
    
    X_test, y_rul_test, _ = data['test']
    y_pred = model.predict(X_test, verbose=0).flatten()
    
    # Metrics (normalized)
    mae_norm = mean_absolute_error(y_rul_test, y_pred)
    rmse_norm = np.sqrt(mean_squared_error(y_rul_test, y_pred))
    r2 = r2_score(y_rul_test, y_pred)
    
    # Metrics (hours)
    y_true_hours = preprocessor.denormalize_rul(y_rul_test)
    y_pred_hours = preprocessor.denormalize_rul(y_pred)
    mae_hours = mean_absolute_error(y_true_hours, y_pred_hours)
    rmse_hours = np.sqrt(mean_squared_error(y_true_hours, y_pred_hours))
    
    print("\n" + "=" * 60)
    print("📊 RUL PREDICTION RESULTS")
    print("=" * 60)
    print(f"   MAE:  {mae_hours:.2f} hours")
    print(f"   RMSE: {rmse_hours:.2f} hours")
    print(f"   R²:   {r2:.4f}")
    
    # Compare with baseline
    print("\n📈 Comparison with Multi-task Model:")
    print(f"   Multi-task R²: 0.4279")
    print(f"   Separate R²:   {r2:.4f}")
    print(f"   Improvement:   {(r2 - 0.4279) * 100:.2f}%")
    
    # Save
    model.save("models/rul_lstm_final.keras")
    print(f"\n✅ Model saved to models/rul_lstm_final.keras")
    
    print("\n" + "=" * 60)
    print("🎉 RUL MODEL COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
