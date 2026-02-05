"""
LSTM + Single Attention for RUL Prediction
Simpler and more appropriate for time-series sensor data.
"""
import tensorflow as tf
from tensorflow.keras import layers, Model
from keras.saving import register_keras_serializable


@register_keras_serializable(package='CustomLayers')
class SingleAttention(layers.Layer):
    """
    Single attention head - learns which timesteps are most important.
    
    For RUL: "Which hours in the 72h window predict failure best?"
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def build(self, input_shape):
        # input_shape: (batch, timesteps, features)
        self.W = self.add_weight(
            name='attn_weight',
            shape=(input_shape[-1], 1),
            initializer='glorot_uniform',
            trainable=True
        )
        self.b = self.add_weight(
            name='attn_bias',
            shape=(input_shape[1], 1),
            initializer='zeros',
            trainable=True
        )
        super().build(input_shape)
    
    def call(self, x):
        # Compute attention scores
        e = tf.nn.tanh(tf.tensordot(x, self.W, axes=1) + self.b)
        # Softmax over timesteps
        alpha = tf.nn.softmax(e, axis=1)
        # Weighted sum
        context = tf.reduce_sum(x * alpha, axis=1)
        return context
    
    def get_config(self):
        return super().get_config()


def build_rul_lstm_attention(
    window_size: int = 72,
    n_features: int = 10,
    lstm_units: int = 64,
    dropout: float = 0.2,
    learning_rate: float = 0.001
) -> Model:
    """
    Build LSTM + Single Attention for RUL prediction.
    
    Architecture:
        Input → LSTM → Attention → Dense → RUL output
    """
    inputs = layers.Input(shape=(window_size, n_features), name='sensor_input')
    
    # LSTM layer (return sequences for attention)
    x = layers.LSTM(lstm_units, return_sequences=True, name='lstm')(inputs)
    x = layers.Dropout(dropout)(x)
    
    # Single Attention - focus on important timesteps
    x = SingleAttention(name='attention')(x)
    
    # Dense layers
    x = layers.Dense(32, activation='relu', name='dense_1')(x)
    x = layers.Dropout(dropout)(x)
    
    # Output: RUL (normalized 0-1)
    output = layers.Dense(1, activation='sigmoid', name='rul_output')(x)
    
    model = Model(inputs=inputs, outputs=output, name='RUL_LSTM_Attention')
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss='mse',
        metrics=['mae']
    )
    
    return model


if __name__ == '__main__':
    model = build_rul_lstm_attention()
    model.summary()
