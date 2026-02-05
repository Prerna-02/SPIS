"""
Interactive Prediction Demo for Predictive Maintenance
Predicts RUL (hours) and Failure Mode from sensor inputs.
"""
import sys
sys.path.insert(0, '.')
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import numpy as np
import tensorflow as tf
from src.data.maintenance_preprocessor import MaintenancePreprocessor
from src.models.rul_lstm_attention import SingleAttention

print("="*60)
print("LOADING MODELS...")
print("="*60)

# RUL model uses 72h window
preprocessor_rul = MaintenancePreprocessor(data_dir='data', window_size=72, stride=6)
data_rul = preprocessor_rul.prepare_data()

# Multi-task model uses 24h window  
preprocessor_24h = MaintenancePreprocessor(data_dir='data', window_size=24, stride=6)
data_24h = preprocessor_24h.prepare_data()

# Load models
rul_model = tf.keras.models.load_model('models/rul_lstm_attn_v2.keras')
multitask_model = tf.keras.models.load_model('models/multitask_lstm_best.keras')

print("✅ Models loaded!")

# Constants
FEATURES = [
    'utilization_rate', 'maintenance_age_days', 'load_tons', 'lift_cycles_per_hour',
    'motor_temp_c', 'gearbox_temp_c', 'hydraulic_pressure_bar', 
    'vibration_rms', 'current_amp', 'rpm'
]
FAILURE_MODES = ['bearing', 'electrical', 'hydraulic_leak', 'none', 'overheating']

# Get test data
X_test_rul, y_rul_test, _ = data_rul['test']
X_test_24h, _, y_mode_test = data_24h['test']

# Use min length to align indices
min_len = min(len(X_test_rul), len(X_test_24h))

def predict_sample(idx):
    """Predict RUL and failure mode for a test sample"""
    # Get samples
    sample_rul = X_test_rul[idx:idx+1]
    sample_24h = X_test_24h[idx:idx+1]
    
    # Show input values (last hour from 72h window)
    last_hour = sample_rul[0][-1]
    print("\n" + "="*60)
    print(f"SAMPLE #{idx} - SENSOR READINGS (last hour)")
    print("="*60)
    for i, feat in enumerate(FEATURES):
        print(f"  {feat:25s}: {last_hour[i]:.4f}")
    
    # RUL prediction
    rul_pred_norm = rul_model.predict(sample_rul, verbose=0)[0][0]
    rul_pred = preprocessor_rul.denormalize_rul(np.array([rul_pred_norm]))[0]
    true_rul = preprocessor_rul.denormalize_rul(np.array([y_rul_test[idx]]))[0]
    
    # Failure mode prediction
    _, mode_probs = multitask_model.predict(sample_24h, verbose=0)
    mode_pred_idx = np.argmax(mode_probs[0])
    mode_pred = FAILURE_MODES[mode_pred_idx]
    mode_confidence = mode_probs[0][mode_pred_idx] * 100
    true_mode = FAILURE_MODES[y_mode_test[idx]]
    
    print("\n" + "="*60)
    print("PREDICTION RESULTS")
    print("="*60)
    
    print(f"\n📊 RUL Prediction:")
    print(f"   Predicted: {rul_pred:.0f} hours")
    print(f"   Actual:    {true_rul:.0f} hours")
    error = rul_pred - true_rul
    status = "✅ Good" if abs(error) <= 100 else "⚠️ Large error"
    print(f"   Error:     {error:+.0f} hours ({status})")
    
    print(f"\n🔧 Failure Mode Prediction:")
    print(f"   Predicted: {mode_pred} ({mode_confidence:.1f}% confidence)")
    print(f"   Actual:    {true_mode}")
    print(f"   Match:     {'✅ Correct!' if mode_pred == true_mode else '❌ Wrong'}")
    
    print("\n   Probabilities:")
    for i, mode in enumerate(FAILURE_MODES):
        bar = "█" * int(mode_probs[0][i] * 20)
        marker = " ◄" if i == mode_pred_idx else ""
        print(f"     {mode:15s}: {mode_probs[0][i]*100:5.1f}% {bar}{marker}")

# Interactive loop
print("\n" + "="*60)
print("INTERACTIVE PREDICTION DEMO")
print("="*60)
print(f"\nTest samples available: 0 to {min_len-1}")
print("Commands: number | 'r' (random) | 'q' (quit)")

while True:
    print("\n" + "-"*40)
    user_input = input("Enter sample index: ").strip()
    
    if user_input.lower() == 'q':
        print("\nGoodbye! 👋")
        break
    elif user_input.lower() == 'r':
        idx = np.random.randint(0, min_len)
        print(f"Random sample: {idx}")
    else:
        try:
            idx = int(user_input)
            if idx < 0 or idx >= min_len:
                print(f"⚠️ Index must be 0-{min_len-1}")
                continue
        except ValueError:
            print("⚠️ Enter a number, 'r', or 'q'")
            continue
    
    predict_sample(idx)
