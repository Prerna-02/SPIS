"""
LSTM Model for Port Throughput Prediction
Predicts next 7 days of port throughput (containers/day).
"""
import tensorflow as tf
from tensorflow.keras import layers, Model


def build_throughput_lstm(
    window_size: int = 7,
    n_features: int = 6,
    forecast_horizon: int = 7,
    lstm_units: list = [64, 32],
    dropout: float = 0.2,
    learning_rate: float = 0.001
) -> Model:
    """
    Build LSTM model for 7-day throughput forecasting.
    
    Architecture:
        Input (7 days × 6 features)
        → LSTM (64 units) → Dropout (20%)
        → LSTM (32 units) → Dropout (20%)
        → Dense (16) → Output (7 days)
    
    Args:
        window_size: Days of historical data as input
        n_features: Number of input features
        forecast_horizon: Days to predict ahead
        lstm_units: Units per LSTM layer
        dropout: Dropout rate
        learning_rate: Adam learning rate
    
    Returns:
        Compiled Keras model
    """
    inputs = layers.Input(shape=(window_size, n_features), name='daily_input')
    
    x = inputs
    
    # LSTM Layer 1
    x = layers.LSTM(lstm_units[0], return_sequences=True, name='lstm_1')(x)
    x = layers.Dropout(dropout, name='dropout_1')(x)
    
    # LSTM Layer 2
    x = layers.LSTM(lstm_units[1], return_sequences=False, name='lstm_2')(x)
    x = layers.Dropout(dropout, name='dropout_2')(x)
    
    # Dense layers
    x = layers.Dense(16, activation='relu', name='dense_1')(x)
    
    # Output: 7 days of throughput prediction
    output = layers.Dense(forecast_horizon, activation='linear', name='throughput_output')(x)
    
    model = Model(inputs=inputs, outputs=output, name='Throughput_LSTM')
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss='mse',
        metrics=['mae']
    )
    
    return model


if __name__ == '__main__':
    model = build_throughput_lstm()
    model.summary()
