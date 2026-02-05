"""
Temporal Fusion Transformer (TFT) for Port Throughput Prediction
A simplified TFT implementation for 7-day ahead throughput forecasting.
"""
import tensorflow as tf
from tensorflow.keras import layers, Model
import numpy as np


class GatedLinearUnit(layers.Layer):
    """Gated Linear Unit for controlling information flow."""
    
    def __init__(self, units, dropout_rate=0.1, **kwargs):
        super().__init__(**kwargs)
        self.units = units
        self.dropout_rate = dropout_rate
        
    def build(self, input_shape):
        self.dense_1 = layers.Dense(self.units, activation='linear')
        self.dense_2 = layers.Dense(self.units, activation='sigmoid')
        self.dropout = layers.Dropout(self.dropout_rate)
        
    def call(self, x, training=None):
        return self.dropout(self.dense_1(x) * self.dense_2(x), training=training)
    
    def get_config(self):
        config = super().get_config()
        config.update({
            'units': self.units,
            'dropout_rate': self.dropout_rate
        })
        return config


class GatedResidualNetwork(layers.Layer):
    """Gated Residual Network (GRN) - core building block of TFT."""
    
    def __init__(self, units, dropout_rate=0.1, **kwargs):
        super().__init__(**kwargs)
        self.units = units
        self.dropout_rate = dropout_rate
        
    def build(self, input_shape):
        self.dense_1 = layers.Dense(self.units, activation='elu')
        self.dense_2 = layers.Dense(self.units, activation='linear')
        self.glu = GatedLinearUnit(self.units, self.dropout_rate)
        self.layer_norm = layers.LayerNormalization()
        self.project = layers.Dense(self.units) if input_shape[-1] != self.units else None
        
    def call(self, x, training=None):
        residual = self.project(x) if self.project else x
        x = self.dense_1(x)
        x = self.dense_2(x)
        x = self.glu(x, training=training)
        return self.layer_norm(x + residual)
    
    def get_config(self):
        config = super().get_config()
        config.update({
            'units': self.units,
            'dropout_rate': self.dropout_rate
        })
        return config


class VariableSelectionNetwork(layers.Layer):
    """Variable Selection Network for feature importance."""
    
    def __init__(self, num_features, units, dropout_rate=0.1, **kwargs):
        super().__init__(**kwargs)
        self.num_features = num_features
        self.units = units
        self.dropout_rate = dropout_rate
        
    def build(self, input_shape):
        self.grn_var = [GatedResidualNetwork(self.units, self.dropout_rate) 
                        for _ in range(self.num_features)]
        self.grn_weights = GatedResidualNetwork(self.num_features, self.dropout_rate)
        self.softmax = layers.Softmax()
        
    def call(self, x, training=None):
        # x shape: (batch, time, features)
        batch_size = tf.shape(x)[0]
        time_steps = tf.shape(x)[1]
        
        # Flatten for weight computation
        x_flat = tf.reshape(x, [-1, self.num_features])
        
        # Compute variable weights
        weights = self.grn_weights(x_flat, training=training)
        weights = self.softmax(weights)
        weights = tf.reshape(weights, [batch_size, time_steps, self.num_features, 1])
        
        # Process each variable
        processed = []
        for i in range(self.num_features):
            var_input = x[:, :, i:i+1]
            var_output = self.grn_var[i](var_input, training=training)
            processed.append(var_output)
        
        # Stack and weight
        processed = tf.stack(processed, axis=2)  # (batch, time, features, units)
        output = tf.reduce_sum(processed * weights, axis=2)  # (batch, time, units)
        
        return output, tf.squeeze(weights, axis=-1)
    
    def get_config(self):
        config = super().get_config()
        config.update({
            'num_features': self.num_features,
            'units': self.units,
            'dropout_rate': self.dropout_rate
        })
        return config


class TemporalAttention(layers.Layer):
    """Interpretable Multi-Head Attention for temporal patterns."""
    
    def __init__(self, num_heads, key_dim, dropout_rate=0.1, **kwargs):
        super().__init__(**kwargs)
        self.num_heads = num_heads
        self.key_dim = key_dim
        self.dropout_rate = dropout_rate
        
    def build(self, input_shape):
        self.mha = layers.MultiHeadAttention(
            num_heads=self.num_heads,
            key_dim=self.key_dim,
            dropout=self.dropout_rate
        )
        self.layer_norm = layers.LayerNormalization()
        
    def call(self, x, training=None):
        attn_output, attn_weights = self.mha(x, x, return_attention_scores=True, training=training)
        return self.layer_norm(x + attn_output), attn_weights
    
    def get_config(self):
        config = super().get_config()
        config.update({
            'num_heads': self.num_heads,
            'key_dim': self.key_dim,
            'dropout_rate': self.dropout_rate
        })
        return config


def build_throughput_tft(
    window_size: int = 7,
    n_features: int = 6,
    forecast_horizon: int = 7,
    hidden_units: int = 32,
    num_heads: int = 4,
    dropout_rate: float = 0.1,
    learning_rate: float = 0.001
) -> Model:
    """
    Build simplified TFT model for throughput forecasting.
    
    Architecture:
        Input → Variable Selection Network
        → LSTM Encoder
        → Temporal Attention
        → GRN Decoder
        → Output (7-day forecast)
    
    Args:
        window_size: Days of historical data as input
        n_features: Number of input features
        forecast_horizon: Days to predict ahead
        hidden_units: Hidden layer dimension
        num_heads: Attention heads
        dropout_rate: Dropout rate
        learning_rate: Adam learning rate
    
    Returns:
        Compiled Keras model
    """
    inputs = layers.Input(shape=(window_size, n_features), name='daily_input')
    
    # 1. Variable Selection Network
    vsn = VariableSelectionNetwork(n_features, hidden_units, dropout_rate)
    x, var_weights = vsn(inputs)
    
    # 2. LSTM Encoder (processes temporal patterns)
    x = layers.LSTM(hidden_units, return_sequences=True, name='encoder_lstm')(x)
    x = layers.Dropout(dropout_rate)(x)
    
    # 3. Temporal Attention (interpretable attention over time steps)
    attn_layer = TemporalAttention(num_heads, hidden_units // num_heads, dropout_rate)
    x, attn_weights = attn_layer(x)
    
    # 4. GRN Decoder
    grn_decoder = GatedResidualNetwork(hidden_units, dropout_rate)
    x = grn_decoder(x)
    
    # 5. Global pooling and output
    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dense(hidden_units, activation='relu')(x)
    x = layers.Dropout(dropout_rate)(x)
    
    # Output: 7-day forecast
    output = layers.Dense(forecast_horizon, activation='linear', name='throughput_output')(x)
    
    model = Model(inputs=inputs, outputs=output, name='Throughput_TFT')
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss='mse',
        metrics=['mae']
    )
    
    return model


if __name__ == '__main__':
    model = build_throughput_tft()
    model.summary()
