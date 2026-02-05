# Feature 1: Port Throughput Forecasting

## Smart Port Intelligence System (SPIS) - Port of Tallinn

**Document Version**: 1.0  
**Last Updated**: January 2026  
**Author**: SPIS Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Data Overview](#3-data-overview)
4. [Methodology](#4-methodology)
5. [Model Architecture](#5-model-architecture)
6. [Why TCN Outperforms LightGBM](#6-why-tcn-outperforms-lightgbm)
7. [Why Horizon-Wise Metrics](#7-why-horizon-wise-metrics-instead-of-overall)
8. [Results & Evaluation](#8-results--evaluation)
9. [Frontend Visualizations](#9-frontend-visualizations)
10. [TCN Parameters Explained](#10-tcn-parameters-in-detail)
11. [Deployment & Artifacts](#11-deployment--artifacts)
12. [Future Improvements](#12-future-improvements)

---

## 1. Executive Summary

Feature 1 forecasts **port demand** (port_calls and throughput_containers) for the **next 7 days** at the Port of Tallinn. This enables port operators to:

- Allocate crane operators and equipment efficiently
- Plan warehouse capacity in advance
- Schedule vessel berths optimally
- Coordinate trucking and logistics

### Key Results

| Target | Best Model | sMAPE | R² | MAE |
|--------|------------|-------|-----|-----|
| port_calls | TCN | 5.76% | -0.002 | 11.00 |
| throughput_containers | TCN | 6.24% | 0.749 | 1,688 |

**Winner**: TCN (Temporal Convolutional Network) outperforms LightGBM on both targets.

---

## 2. Problem Statement

### Business Challenge

> "Given today's date (T), predict the next 7 days of port activity (T+1 to T+7)"

Port operators face significant challenges:

| Challenge | Impact |
|-----------|--------|
| Demand volatility | 15-25% daily variance in port calls |
| Resource planning | Under/over-staffing costs $10K-50K daily |
| Equipment scheduling | Idle equipment = wasted capital |
| Warehouse capacity | Overflow causes delays and penalties |

### Technical Requirements

1. **Multi-horizon forecasting**: Predict days 1-7 simultaneously
2. **No data leakage**: Cannot use future information
3. **Time-series integrity**: Maintain temporal order (no shuffling)
4. **Interpretable metrics**: Horizon-specific performance analysis

---

## 3. Data Overview

### Dataset: `tallinn_feature1_daily_v2.csv`

| Property | Value |
|----------|-------|
| Records | 4,167 daily observations |
| Date Range | January 2014 - May 2025 |
| Frequency | Daily aggregated |
| Missing Values | None |

### Target Variables

| Target | Description | Mean | Std | Min | Max |
|--------|-------------|------|-----|-----|-----|
| `port_calls` | Daily total vessel arrivals | 189 | 20 | 55 | 247 |
| `throughput_containers` | Daily container throughput (TEU proxy) | 26,576 | 4,532 | 8,408 | 42,673 |

### Input Features (16 total)

| Category | Features |
|----------|----------|
| **Weather** | `weather_condition_severity` (0-1 scale) |
| **Operations** | `port_congestion_level`, `delay_probability`, `handling_equipment_availability` |
| **Logistics** | `warehouse_inventory_level`, `loading_unloading_time_hours` |
| **Cargo Mix** | `food_share`, `pharma_share`, `electronics_share`, `other_share` |
| **Quality** | `position_accuracy_m` |
| **Calendar** | `year`, `month`, `day`, `day_of_week`, `day_of_year` |

---

## 4. Methodology

### 4.1 Forecasting Approach: Direct Multi-Step

We use **Direct Multi-Step Forecasting** where each model directly predicts all 7 future values:

```
Input Window (56 days)              Output (7 days)
[t-55, t-54, ..., t-1, t]  --->    [t+1, t+2, ..., t+7]
```

**Why Direct instead of Recursive?**

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **Recursive** | Predict t+1, use it to predict t+2, etc. | Simple | Error accumulates |
| **Direct** | Train separate model for each horizon | No error accumulation | More models to train |
| **Direct Multi-Output** | Single model predicts all horizons | Efficient, captures horizon dependencies | More complex |

We chose **Direct (for LightGBM)** and **Direct Multi-Output (for TCN)** to avoid error accumulation.

### 4.2 Train/Validation/Test Split

```
Timeline: |-------- Train (72%) --------|-- Val (8%) --|---- Test (20%) ----|
          |                             |              |                     |
          2014-01-01              ~2021-06        ~2023-02              2025-05
```

| Split | Percentage | Samples | Date Range |
|-------|------------|---------|------------|
| Train | 72% | ~2,955 | 2014-01 to ~2021-06 |
| Validation | 8% | ~329 | ~2021-06 to ~2023-02 |
| Test | 20% | ~821 | ~2023-02 to 2025-05 |

**Critical**: No shuffling - temporal order preserved to simulate real deployment.

### 4.3 Feature Engineering (LightGBM only)

For LightGBM, we create lag and rolling features using **only past data**:

```python
# Lag features (shift ensures no leakage)
port_calls_lag_1  = port_calls.shift(1)   # Yesterday's value
port_calls_lag_7  = port_calls.shift(7)   # Same day last week
port_calls_lag_14 = port_calls.shift(14)  # Two weeks ago
port_calls_lag_28 = port_calls.shift(28)  # Four weeks ago

# Rolling statistics (shift(1) ensures we don't include today)
port_calls_rolling_mean_7 = port_calls.shift(1).rolling(7).mean()
port_calls_rolling_std_7  = port_calls.shift(1).rolling(7).std()
```

**Leakage Prevention**: All features are computed using `shift()` to ensure no future information leaks into training.

---

## 5. Model Architecture

### 5.1 Model A: LightGBM (Baseline)

**Approach**: Train 7 separate models per target (14 total models)

```
Target: port_calls
├── Model H1: Predicts port_calls at t+1
├── Model H2: Predicts port_calls at t+2
├── ...
└── Model H7: Predicts port_calls at t+7

Target: throughput_containers
├── Model H1: Predicts throughput at t+1
├── ...
└── Model H7: Predicts throughput at t+7
```

**Hyperparameters**:

```python
params = {
    'objective': 'regression',
    'metric': 'mae',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'num_boost_round': 500,
    'early_stopping_rounds': 30
}
```

**Feature Set**: 16 exogenous features + 32 lag/rolling features = **48 features**

### 5.2 Model B: TCN (Temporal Convolutional Network)

**Approach**: Single model predicts all 7 horizons simultaneously

```
Input: (batch_size, 56, 18)  # 56 days × 18 features
           ↓
    [Residual Block, dilation=1]
           ↓
    [Residual Block, dilation=2]
           ↓
    [Residual Block, dilation=4]
           ↓
    [Residual Block, dilation=8]
           ↓
    [Residual Block, dilation=16]
           ↓
    [GlobalAveragePooling1D]
           ↓
    [Dense(128, relu) → Dropout(0.1)]
           ↓
    [Dense(64, relu)]
           ↓
Output: (batch_size, 7)  # 7 days forecast
```

**Total Parameters**: ~85,000 per model

---

## 6. Why TCN Outperforms LightGBM

### 6.1 Results Comparison

| Target | Metric | LightGBM | TCN | Winner |
|--------|--------|----------|-----|--------|
| port_calls | sMAPE | 5.78% | **5.76%** | TCN |
| port_calls | R² | -0.0141 | **-0.0022** | TCN |
| port_calls | MAE | 11.04 | **11.00** | TCN |
| throughput_containers | sMAPE | 6.31% | **6.24%** | TCN |
| throughput_containers | R² | 0.7452 | **0.7494** | TCN |
| throughput_containers | MAE | 1,707 | **1,688** | TCN |

### 6.2 Reasons for TCN's Superior Performance

#### Reason 1: Temporal Pattern Learning

```
LightGBM: Treats each sample independently
          Input → [Features at time t] → Prediction
          
TCN:      Learns temporal dependencies across 56 days
          Input → [Sequence of 56 days] → Captures trends, seasonality → Prediction
```

**TCN sees the full trajectory**, not just point-in-time features. This helps capture:
- Weekly seasonality (7-day cycles)
- Monthly patterns
- Trend changes
- Momentum

#### Reason 2: Hierarchical Feature Extraction

TCN's **dilated convolutions** capture patterns at multiple time scales:

```
Dilation=1:  Captures daily patterns (consecutive days)
Dilation=2:  Captures 2-day patterns
Dilation=4:  Captures weekly patterns (~4-5 days)
Dilation=8:  Captures bi-weekly patterns
Dilation=16: Captures monthly patterns
```

LightGBM relies on **hand-crafted features** (lags at 1, 7, 14, 28 days), which may miss patterns at other scales.

#### Reason 3: Joint Horizon Learning

```
LightGBM: 7 independent models, no information sharing between horizons
          - H1 model doesn't know what H7 model learned
          - Inconsistent predictions possible

TCN:      Single model learns all horizons jointly
          - Shared representation captures common patterns
          - Consistent predictions across horizons
```

#### Reason 4: Non-Linear Feature Interactions

```
LightGBM: Tree-based splits (axis-aligned decisions)
          - Good for tabular, structured patterns
          - Limited interaction modeling

TCN:      Convolutional filters + dense layers
          - Learns complex non-linear interactions
          - Better at capturing smooth temporal dynamics
```

#### Reason 5: Regularization Through Architecture

TCN has built-in regularization:
- **Dropout** (0.1) prevents overfitting
- **Residual connections** stabilize training
- **Layer normalization** improves generalization

### 6.3 When LightGBM Might Win

| Scenario | Preferred Model |
|----------|-----------------|
| Small dataset (<1000 samples) | LightGBM |
| Strong categorical features | LightGBM |
| Interpretability required | LightGBM |
| Real-time inference (low latency) | LightGBM |
| Complex temporal patterns | TCN |
| Large dataset (>3000 samples) | TCN |
| Multi-horizon forecasting | TCN |

---

## 7. Why Horizon-Wise Metrics Instead of Overall

### 7.1 The Problem with Overall Metrics

**Flattened evaluation hides important information:**

```python
# Overall (flattened) approach - WRONG
y_true_flat = Y_true.reshape(-1)  # [sample1_h1, sample1_h2, ..., sampleN_h7]
y_pred_flat = Y_pred.reshape(-1)
overall_mae = MAE(y_true_flat, y_pred_flat)  # Single number, loses horizon info
```

**What's hidden:**
- H1 might have MAE=5, H7 might have MAE=20
- Overall MAE=12.5 tells you nothing about this degradation
- Business decisions need horizon-specific accuracy

### 7.2 Horizon-Wise Evaluation

```python
# Horizon-wise approach - CORRECT
for h in range(1, 8):
    y_true_h = Y_true[:, h-1]  # All samples for horizon h
    y_pred_h = Y_pred[:, h-1]
    mae_h = MAE(y_true_h, y_pred_h)
    print(f"H{h} MAE: {mae_h}")
```

**What you learn:**
- How accuracy degrades with forecast distance
- Which horizons are reliable for business decisions
- Whether the model has systematic biases at certain horizons

### 7.3 Expected Horizon Degradation

**Uncertainty grows with forecast distance:**

```
Forecast Distance →
    H1      H2      H3      H4      H5      H6      H7
    |       |       |       |       |       |       |
   Low    ←←←←←←←←←  Uncertainty  →→→→→→→→→   High
  Error                                           Error
```

**Our Results (throughput_containers TCN):**

| Horizon | sMAPE | Change from H1 |
|---------|-------|----------------|
| H1 | 6.18% | baseline |
| H2 | 6.17% | -0.01% |
| H3 | 6.23% | +0.05% |
| H4 | 6.25% | +0.07% |
| H5 | 6.26% | +0.08% |
| H6 | 6.24% | +0.06% |
| H7 | 6.31% | +0.13% |

**Observation**: Only +0.13% degradation from H1 to H7 indicates a **stable model**.

### 7.4 Business Implications

| Horizon | Business Use | Acceptable Error |
|---------|--------------|------------------|
| H1 (Tomorrow) | Shift scheduling, equipment prep | <5% |
| H2-H3 | Detailed resource planning | <7% |
| H4-H5 | Warehouse capacity planning | <10% |
| H6-H7 | Strategic planning, trucking contracts | <15% |

**Recommendation**: Use H1-H3 for operational decisions, H4-H7 for planning.

---

## 8. Results & Evaluation

### 8.1 Horizon-Wise Metrics Tables

#### port_calls

| Horizon | LightGBM MAE | LightGBM sMAPE | TCN MAE | TCN sMAPE | Best |
|---------|--------------|----------------|---------|-----------|------|
| H1 | 11.04 | 5.79% | 11.03 | 5.77% | TCN |
| H2 | 11.05 | 5.78% | 10.92 | 5.72% | TCN |
| H3 | 11.00 | 5.76% | 10.96 | 5.75% | TCN |
| H4 | 11.06 | 5.78% | 11.01 | 5.76% | TCN |
| H5 | 11.05 | 5.79% | 11.01 | 5.74% | TCN |
| H6 | 11.03 | 5.79% | 10.98 | 5.75% | TCN |
| H7 | 11.06 | 5.78% | 11.08 | 5.80% | LightGBM |
| **Overall** | **11.04** | **5.78%** | **11.00** | **5.76%** | **TCN** |

#### throughput_containers

| Horizon | LightGBM MAE | LightGBM sMAPE | TCN MAE | TCN sMAPE | Best |
|---------|--------------|----------------|---------|-----------|------|
| H1 | 1,703 | 6.29% | 1,673 | 6.18% | TCN |
| H2 | 1,705 | 6.30% | 1,671 | 6.17% | TCN |
| H3 | 1,707 | 6.31% | 1,685 | 6.23% | TCN |
| H4 | 1,708 | 6.31% | 1,694 | 6.25% | TCN |
| H5 | 1,709 | 6.31% | 1,695 | 6.26% | TCN |
| H6 | 1,708 | 6.31% | 1,690 | 6.24% | TCN |
| H7 | 1,710 | 6.30% | 1,704 | 6.31% | Tie |
| **Overall** | **1,707** | **6.31%** | **1,688** | **6.24%** | **TCN** |

### 8.2 Interpretation

1. **port_calls has negative R²**: The target is highly volatile with weak predictability. Mean prediction would perform similarly. This is a **hard forecasting problem**.

2. **throughput_containers has R² ~0.75**: Good predictability. The model explains 75% of the variance.

3. **Both models are stable across horizons**: Minimal degradation from H1 to H7 (<1% sMAPE increase).

4. **TCN wins on average**: But LightGBM is competitive and faster for inference.

---

## 9. Frontend Visualizations

### 9.1 Planned Dashboard Components

#### Component 1: Forecast Overview Card

```
┌─────────────────────────────────────────────────────────────┐
│  PORT DEMAND FORECAST                        As of: Jan 30  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Port Calls (Next 7 Days)                                   │
│  ┌───┬───┬───┬───┬───┬───┬───┐                             │
│  │185│190│188│192│195│189│187│  Total: 1,326               │
│  └───┴───┴───┴───┴───┴───┴───┘                             │
│   +1  +2  +3  +4  +5  +6  +7                                │
│                                                             │
│  Throughput (TEU) (Next 7 Days)                             │
│  ┌────┬────┬────┬────┬────┬────┬────┐                      │
│  │26.5│27.1│26.8│27.3│27.5│26.9│26.2│  Total: 188.3K       │
│  └────┴────┴────┴────┴────┴────┴────┘                      │
│   +1   +2   +3   +4   +5   +6   +7                          │
│                                                             │
│  Confidence: High (sMAPE < 7%)                              │
└─────────────────────────────────────────────────────────────┘
```

#### Component 2: Time Series Forecast Chart

```
Port Calls - 30-Day History + 7-Day Forecast
     │
 220 ┤                                    ╭──────╮
     │         ╭──╮    ╭╮                │ Forecast
 200 ┤    ╭───╮│  │╭──╮││    ╭─╮ ╭──╮   │ ± Confidence
     │╭──╮│   ╰╯  ╰╯  ╰╯╰───╮│ ╰─╯  ╰───╯
 180 ┤│  ╰╯                  ╰╯
     │╯                                  
 160 ┼────────────────────────────────────────────────
     Jan 1    Jan 10    Jan 20    Jan 30  │  Feb 6
                                          │
                                    Today ─┘
```

**Implementation**: Line chart with:
- Solid line: Historical actual values
- Dashed line: 7-day forecast
- Shaded area: Confidence interval (P10-P90)
- Vertical line: "Today" marker

#### Component 3: Horizon Accuracy Heatmap

```
Model Performance by Horizon (sMAPE %)

              H1    H2    H3    H4    H5    H6    H7
            ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┐
port_calls  │ 5.8 │ 5.7 │ 5.8 │ 5.8 │ 5.7 │ 5.8 │ 5.8 │  ████ <6%
            ├─────┼─────┼─────┼─────┼─────┼─────┼─────┤  ▓▓▓▓ 6-8%
throughput  │ 6.2 │ 6.2 │ 6.2 │ 6.3 │ 6.3 │ 6.2 │ 6.3 │  ░░░░ >8%
            └─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

#### Component 4: Actual vs Predicted Comparison

```
┌─────────────────────────────────────────────────────────────┐
│  FORECAST ACCURACY - Last 30 Days (Backtest)                │
├─────────────────────────────────────────────────────────────┤
│  Date       Actual  Predicted  Error   Status               │
│  ─────────────────────────────────────────────              │
│  Jan 28     192     189        -3      ✓ Within 5%          │
│  Jan 27     185     188        +3      ✓ Within 5%          │
│  Jan 26     178     190        +12     ⚠ Over 5%            │
│  Jan 25     203     195        -8      ✓ Within 5%          │
│  ...                                                         │
│                                                              │
│  Accuracy Rate: 87% within ±5%                              │
└─────────────────────────────────────────────────────────────┘
```

#### Component 5: Residual Distribution Chart

```
Prediction Errors Distribution (Test Period)
                    
     │    ╭───╮
  30%│   ╱     ╲
     │  ╱       ╲
  20%│ ╱         ╲
     │╱           ╲
  10%├─────────────────────
     │                    ╲
   0%┼────┬────┬────┬────┬────┬────┬────
    -30  -20  -10   0   +10  +20  +30
                Error (%)
     
     Mean: -0.2%  |  Std: 5.8%  |  Skew: 0.1
```

#### Component 6: Feature Importance (LightGBM)

```
Top 10 Features for port_calls Prediction

port_calls_lag_1        ████████████████████ 18.5%
port_calls_lag_7        ███████████████████  17.2%
throughput_lag_1        ████████████████     14.8%
port_congestion_level   ████████████         11.3%
day_of_week             ██████████           9.5%
port_calls_rolling_7    ████████             7.8%
delay_probability       ███████              6.9%
warehouse_inventory     ██████               5.4%
weather_severity        █████                4.8%
loading_time            ████                 3.8%
```

### 9.2 Interactive Features

| Feature | Description |
|---------|-------------|
| **Date Picker** | Select "as-of" date to see forecast for that date |
| **Horizon Slider** | Choose which horizon (H1-H7) to display |
| **Model Selector** | Compare LightGBM vs TCN predictions |
| **Export Button** | Download forecast as CSV/Excel |
| **Refresh Button** | Re-run model with latest data |

### 9.3 Alert Thresholds

| Condition | Alert Level | Color |
|-----------|-------------|-------|
| Forecast < 150 port_calls | LOW DEMAND | Blue |
| Forecast 150-200 port_calls | NORMAL | Green |
| Forecast 200-220 port_calls | HIGH DEMAND | Yellow |
| Forecast > 220 port_calls | CRITICAL | Red |

---

## 10. TCN Parameters in Detail

### 10.1 Architecture Overview

```python
model = build_tcn_model(
    input_length=56,        # 56 days of history
    n_features=18,          # 16 exogenous + 2 targets as past features
    output_length=7,        # 7 days forecast
    n_targets=1,            # 1 target per model
    filters=64,             # Convolutional filters
    kernel_size=3,          # Filter width
    dilations=[1,2,4,8,16], # Exponentially increasing dilations
    dropout_rate=0.1,       # Regularization
    learning_rate=0.001     # Adam optimizer
)
```

### 10.2 Parameter Deep Dive

#### `input_length = 56`

**What it means**: The model sees 56 consecutive days of history.

**Why 56?**
- 56 = 8 weeks = captures 2 full monthly cycles
- Includes multiple weekday/weekend patterns
- Balances context length vs computational cost

```
Receptive Field Calculation:
With dilations [1,2,4,8,16] and kernel_size=3:
RF = 1 + sum([d * (k-1) for d in dilations])
RF = 1 + (1*2 + 2*2 + 4*2 + 8*2 + 16*2) = 1 + 62 = 63 days

Our input_length (56) is covered by the receptive field (63).
```

#### `n_features = 18`

**Composition**:
```
16 exogenous features (weather, congestion, etc.)
+2 target features (port_calls, throughput as past observed)
= 18 total input features
```

**Why include past targets?**
- Autoregressive signal: yesterday's demand predicts today's
- But we DON'T include future targets (that would be leakage)

#### `filters = 64`

**What it means**: Each convolutional layer produces 64 feature maps.

**Why 64?**
- Captures sufficient pattern diversity
- Not too large (overfitting risk, slow training)
- Powers of 2 are efficient on GPUs

```
Layer output shapes:
Input:        (batch, 56, 18)
After Block1: (batch, 56, 64)
After Block2: (batch, 56, 64)
...
After Block5: (batch, 56, 64)
```

#### `kernel_size = 3`

**What it means**: Each filter looks at 3 consecutive timesteps.

```
Kernel = [w1, w2, w3]

At time t, the filter sees: [x_{t-2}, x_{t-1}, x_t]
```

**Why 3?**
- Captures local patterns (consecutive day relationships)
- Larger kernels (5, 7) would increase parameters without much benefit
- Dilations handle longer-range patterns

#### `dilations = [1, 2, 4, 8, 16]`

**What it means**: Each block skips more timesteps.

```
Dilation=1:  [t-2, t-1, t]     → Consecutive days
Dilation=2:  [t-4, t-2, t]     → Every other day
Dilation=4:  [t-8, t-4, t]     → ~Weekly patterns
Dilation=8:  [t-16, t-8, t]    → Bi-weekly patterns
Dilation=16: [t-32, t-16, t]   → Monthly patterns
```

**Visual representation**:
```
Input:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 ...

d=1:    ▓  ▓  ▓  .  .  .  .  .  .  .  .  .  .  .  .  .  (3 consecutive)
d=2:    ▓  .  ▓  .  ▓  .  .  .  .  .  .  .  .  .  .  .  (skip 1)
d=4:    ▓  .  .  .  ▓  .  .  .  ▓  .  .  .  .  .  .  .  (skip 3)
d=8:    ▓  .  .  .  .  .  .  .  ▓  .  .  .  .  .  .  ▓  (skip 7)
d=16:   ▓  .  .  .  .  .  .  .  .  .  .  .  .  .  .  ▓  ... (skip 15)
```

**Why exponential growth?**
- Covers exponentially more history with linear depth
- 5 layers cover 63 days of receptive field
- Non-dilated network would need 32+ layers for same coverage

#### `dropout_rate = 0.1`

**What it means**: 10% of neurons randomly set to 0 during training.

**Purpose**:
- Prevents overfitting by introducing noise
- Forces the network to learn redundant representations
- Acts as ensemble (each forward pass is a different sub-network)

**Why 0.1?**
- Light regularization for time series (temporal structure is strong)
- Higher (0.3-0.5) might hurt signal learning
- Lower (0.0) risks overfitting on training patterns

#### `learning_rate = 0.001`

**What it means**: Step size for gradient descent updates.

```
new_weights = old_weights - learning_rate * gradient
```

**Why 0.001?**
- Default for Adam optimizer
- Balances convergence speed and stability
- ReduceLROnPlateau halves it when val_loss plateaus

### 10.3 Residual Block Architecture

```python
class ResidualBlock:
    """
    Input (B, T, C_in)
        │
        ├──────────────────────────────┐
        │                              │ (skip connection)
        ▼                              │
    Conv1D(filters, kernel, dilation)  │
        │                              │
        ▼                              │
    ReLU activation                    │
        │                              │
        ▼                              │
    Dropout(rate)                      │
        │                              │
        ▼                              │
    Conv1D(filters, kernel, dilation)  │
        │                              │
        ▼                              │
    ReLU activation                    │
        │                              │
        ▼                              │
    Dropout(rate)                      │
        │                              │
        ▼                              │
    + ←────────────────────────────────┘
        │                              
        ▼                              
    LayerNormalization
        │
        ▼
    Output (B, T, filters)
    """
```

**Why residual connections?**
- Gradient flow: easier to train deep networks
- Identity mapping: if a layer is unhelpful, skip connection preserves input
- Proven effective: ResNet, Transformers all use residuals

### 10.4 Training Configuration

```python
# Callbacks
EarlyStopping(patience=10)        # Stop if no improvement for 10 epochs
ReduceLROnPlateau(factor=0.5,     # Halve LR if val_loss plateaus
                  patience=5)      # Wait 5 epochs before reducing
ModelCheckpoint(save_best_only=True)  # Keep best model

# Training
epochs = 100        # Maximum epochs
batch_size = 32     # Samples per gradient update
```

---

## 11. Deployment & Artifacts

### 11.1 Saved Models

| File | Description | Size |
|------|-------------|------|
| `models/feature1/tcn_port_calls.keras` | TCN model for port_calls | ~1 MB |
| `models/feature1/tcn_throughput_containers.keras` | TCN model for throughput | ~1 MB |
| `models/feature1/lgb_port_calls_h1.txt` .. `h7.txt` | 7 LightGBM models | ~100 KB each |
| `models/feature1/lgb_throughput_containers_h1.txt` .. `h7.txt` | 7 LightGBM models | ~100 KB each |
| `models/feature1/tcn_scaler.pkl` | StandardScaler for TCN inputs | ~5 KB |

### 11.2 Output Files

| File | Description |
|------|-------------|
| `data/processed/feature1_outputs/pred_vs_actual_feature1.csv` | Full predictions table |
| `data/processed/feature1_outputs/model_summary_feature1.csv` | Metrics summary |
| `data/processed/feature1_outputs/port_calls_horizon_comparison.png` | Visualization |
| `data/processed/feature1_outputs/throughput_containers_horizon_comparison.png` | Visualization |
| `data/processed/feature1_outputs/horizon_metrics_comparison.png` | sMAPE by horizon |

### 11.3 Inference Pipeline

```python
def predict_7day_forecast(as_of_date: str, model_type: str = 'tcn'):
    """
    Generate 7-day forecast for a given date.
    
    Args:
        as_of_date: The date to forecast from (YYYY-MM-DD)
        model_type: 'tcn' or 'lightgbm'
    
    Returns:
        dict with port_calls and throughput_containers forecasts
    """
    # 1. Load last 56 days of data ending at as_of_date
    # 2. Scale features (if TCN)
    # 3. Create input sequence
    # 4. Run model inference
    # 5. Inverse transform predictions
    # 6. Return forecast for T+1 to T+7
```

---

## 12. Future Improvements

### 12.1 Model Enhancements

| Improvement | Expected Impact | Complexity |
|-------------|-----------------|------------|
| Ensemble TCN + LightGBM | +5% accuracy | Medium |
| Add external data (holidays, events) | +3-5% accuracy | Low |
| Quantile regression (P10, P50, P90) | Better uncertainty estimates | Medium |
| N-BEATS architecture | State-of-the-art forecasting | High |
| Transfer learning from similar ports | Faster convergence | High |

### 12.2 Infrastructure

| Improvement | Benefit |
|-------------|---------|
| Model versioning (MLflow) | Reproducibility, A/B testing |
| Real-time inference API | <100ms response time |
| Automated retraining pipeline | Model freshness |
| Monitoring dashboard | Detect model drift |

### 12.3 Business Integration

| Integration | Use Case |
|-------------|----------|
| ERP system | Auto-generate shift schedules |
| Warehouse management | Pre-allocate storage capacity |
| Customer portal | Share expected arrival times |
| Financial planning | Budget forecasting |

---

## Appendix A: Code Reference

**Main training script**: `src/feature1_throughput_forecasting.py`

**Key functions**:
- `load_and_clean_data()` - Data loading and validation
- `create_lag_features()` - Feature engineering for LightGBM
- `make_windows_dl()` - Sequence creation for TCN
- `build_tcn_model()` - TCN architecture
- `train_lightgbm_horizon()` - Train single LightGBM model
- `calculate_horizon_metrics()` - Compute metrics per horizon

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Horizon** | Number of days into the future (H1=tomorrow, H7=7 days ahead) |
| **sMAPE** | Symmetric Mean Absolute Percentage Error |
| **TCN** | Temporal Convolutional Network |
| **Dilated Convolution** | Convolution with gaps between filter elements |
| **Receptive Field** | How far back in time a model can "see" |
| **Direct Forecasting** | Separate model for each horizon |
| **Recursive Forecasting** | Use predictions as inputs for next prediction |
| **Residual Connection** | Shortcut that adds input to output |

---

*Document generated as part of Smart Port Intelligence System (SPIS) development.*
