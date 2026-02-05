"""
Bidirectional LSTM with Attention for RUL Prediction
Focused model for improving Remaining Useful Life regression accuracy.
"""
import tensorflow as tf
from tensorflow.keras import layers, Model
from keras.saving import register_keras_serializable


@register_keras_serializable(package='CustomLayers')
class AttentionLayer(layers.Layer):
    """Simple attention mechanism for sequence models."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def build(self, input_shape):
        self.W = self.add_weight(
            name='attention_weight',
            shape=(input_shape[-1], 1),
            initializer='glorot_uniform',
            trainable=True
        )
        self.b = self.add_weight(
            name='attention_bias',
            shape=(input_shape[1], 1),
            initializer='zeros',
            trainable=True
        )
        super().build(input_shape)
    
    def call(self, x):
        # x shape: (batch, timesteps, features)
        e = tf.nn.tanh(tf.tensordot(x, self.W, axes=1) + self.b)
        a = tf.nn.softmax(e, axis=1)
        output = tf.reduce_sum(x * a, axis=1)
        return output


def build_rul_bilstm(
    window_size: int = 72,
    n_features: int = 10,
    lstm_units: list = [64, 32],
    dropout: float = 0.2,
    learning_rate: float = 0.001
) -> Model:
    """
    Build Bidirectional LSTM with Attention for RUL prediction.
    
    Args:
        window_size: Sequence length (hours)
        n_features: Number of input features
        lstm_units: List of LSTM units per layer
        dropout: Dropout rate
        learning_rate: Learning rate for Adam optimizer
    
    Returns:
        Compiled Keras model
    """
    inputs = layers.Input(shape=(window_size, n_features), name='sensor_input')
    
    x = inputs
    
    # Bidirectional LSTM layers
    for i, units in enumerate(lstm_units):
        return_sequences = (i < len(lstm_units) - 1)  # Return sequences for all but last
        x = layers.Bidirectional(
            layers.LSTM(units, return_sequences=True, name=f'lstm_{i}'),
            name=f'bilstm_{i}'
        )(x)
        x = layers.Dropout(dropout, name=f'dropout_{i}')(x)
    
    # Attention layer
    x = AttentionLayer(name='attention')(x)
    
    # Dense layers
    x = layers.Dense(32, activation='relu', name='dense_1')(x)
    x = layers.Dropout(dropout, name='dropout_dense')(x)
    x = layers.Dense(16, activation='relu', name='dense_2')(x)
    
    # Output - RUL prediction (normalized 0-1)
    output = layers.Dense(1, activation='sigmoid', name='rul_output')(x)
    
    model = Model(inputs=inputs, outputs=output, name='RUL_BiLSTM_Attention')
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss='mse',
        metrics=['mae']
    )
    
    return model


if __name__ == '__main__':
    # Quick test
    model = build_rul_bilstm(window_size=72, n_features=10)
    model.summary()
