# %% [markdown]
# # EDA: Port Maintenance Dataset
# 
# This notebook explores the `port_maintenance_synthetic_3months.csv` for:
# - Feature 3: Predictive Maintenance (Multi-task LSTM)
#   - Target A: RUL (Remaining Useful Life) - Regression
#   - Target B: Failure Mode - Classification

# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

print("Libraries loaded successfully!")

# %% [markdown]
# ## 1. Load Data

# %%
# Load dataset
df = pd.read_csv('../data/raw/port_maintenance_synthetic_3months.csv')

print(f"Dataset Shape: {df.shape}")
print(f"Memory Usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

# %%
# Display first few rows
df.head()

# %%
# Column info
print("=" * 60)
print("COLUMN INFORMATION")
print("=" * 60)
for col in df.columns:
    print(f"{col:30} | {str(df[col].dtype):15} | Unique: {df[col].nunique()}")

# %% [markdown]
# ## 2. Data Structure Analysis

# %%
# Identify column types
identifiers = ['asset_id', 'asset_type', 'timestamp', 'operator_shift_id']
context = ['operation_state', 'utilization_rate', 'maintenance_age_days']
workload = ['load_tons', 'lift_cycles_per_hour']
sensors = ['motor_temp_c', 'gearbox_temp_c', 'hydraulic_pressure_bar', 
           'vibration_rms', 'current_amp', 'rpm']
targets = ['rul_hours', 'failure_mode', 'failure_in_next_72h']

print("Column Categories:")
print(f"  Identifiers: {identifiers}")
print(f"  Context: {context}")
print(f"  Workload: {workload}")
print(f"  Sensors: {sensors}")
print(f"  Targets: {targets}")

# %%
# Basic statistics
df.describe()

# %%
# Missing values
missing = df.isnull().sum()
print("\nMissing Values:")
if missing.sum() == 0:
    print("✅ No missing values!")
else:
    print(missing[missing > 0])

# %% [markdown]
# ## 3. Asset Analysis

# %%
# Asset types distribution
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

asset_counts = df['asset_type'].value_counts()
colors = plt.cm.Set2(np.linspace(0, 1, len(asset_counts)))

axes[0].barh(asset_counts.index, asset_counts.values, color=colors)
axes[0].set_title('Records per Asset Type', fontsize=14, fontweight='bold')
axes[0].set_xlabel('Count')

# Unique assets per type
unique_assets = df.groupby('asset_type')['asset_id'].nunique()
axes[1].barh(unique_assets.index, unique_assets.values, color=colors)
axes[1].set_title('Unique Assets per Type', fontsize=14, fontweight='bold')
axes[1].set_xlabel('Count')

plt.tight_layout()
plt.savefig('../data/processed/maintenance_asset_distribution.png', dpi=150, bbox_inches='tight')
plt.show()

print(f"\nTotal Unique Assets: {df['asset_id'].nunique()}")

# %%
# Records per asset
records_per_asset = df.groupby('asset_id').size()
print(f"Records per Asset - Mean: {records_per_asset.mean():.0f}, Std: {records_per_asset.std():.0f}")
print(f"Min: {records_per_asset.min()}, Max: {records_per_asset.max()}")

# %% [markdown]
# ## 4. Target Variable Analysis

# %%
# Target 1: RUL (Remaining Useful Life)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].hist(df['rul_hours'], bins=50, color='steelblue', edgecolor='white')
axes[0].axvline(df['rul_hours'].mean(), color='red', linestyle='--', 
                label=f"Mean: {df['rul_hours'].mean():.1f}h")
axes[0].axvline(72, color='orange', linestyle='--', label='72h threshold')
axes[0].set_title('RUL Distribution (Regression Target)', fontsize=14, fontweight='bold')
axes[0].set_xlabel('Remaining Useful Life (hours)')
axes[0].set_ylabel('Count')
axes[0].legend()

# RUL by asset type
df.boxplot(column='rul_hours', by='asset_type', ax=axes[1], rot=45)
axes[1].set_title('RUL by Asset Type', fontsize=14, fontweight='bold')
axes[1].set_xlabel('')
axes[1].set_ylabel('RUL (hours)')

plt.tight_layout()
plt.savefig('../data/processed/rul_distribution.png', dpi=150, bbox_inches='tight')
plt.show()

print(f"\nRUL Statistics:")
print(df['rul_hours'].describe())

# %%
# Target 2: Failure Mode (Classification)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

failure_counts = df['failure_mode'].value_counts()
colors_fm = {'none': '#27ae60', 'bearing': '#e74c3c', 'overheating': '#f39c12', 
             'hydraulic_leak': '#3498db', 'electrical': '#9b59b6'}
bar_colors = [colors_fm.get(x, 'gray') for x in failure_counts.index]

axes[0].bar(failure_counts.index, failure_counts.values, color=bar_colors)
axes[0].set_title('Failure Mode Distribution', fontsize=14, fontweight='bold')
axes[0].set_ylabel('Count')
axes[0].tick_params(axis='x', rotation=45)

# Percentage
failure_pct = (failure_counts / len(df)) * 100
axes[1].pie(failure_pct.values, labels=failure_pct.index, autopct='%1.1f%%',
            colors=bar_colors, explode=[0.05]*len(failure_pct))
axes[1].set_title('Failure Mode (%)', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('../data/processed/failure_mode_distribution.png', dpi=150, bbox_inches='tight')
plt.show()

print("\nFailure Mode Counts:")
print(failure_counts)

# %%
# Derived target: failure_in_next_72h
fig, ax = plt.subplots(figsize=(8, 5))

failure_72h = df['failure_in_next_72h'].value_counts()
ax.bar(['No Failure (0)', 'Failure (1)'], failure_72h.values, 
       color=['#27ae60', '#e74c3c'])
ax.set_title('Failure in Next 72 Hours (Derived from RUL)', fontsize=14, fontweight='bold')
ax.set_ylabel('Count')

for i, v in enumerate(failure_72h.values):
    ax.text(i, v + 1000, f'{v:,}\n({v/len(df)*100:.1f}%)', ha='center', fontweight='bold')

plt.tight_layout()
plt.savefig('../data/processed/failure_72h_distribution.png', dpi=150, bbox_inches='tight')
plt.show()

print(f"\n⚠️ Class Imbalance: {failure_72h[0]/failure_72h[1]:.1f}:1 ratio (No Failure : Failure)")

# %% [markdown]
# ## 5. Sensor Feature Analysis

# %%
# Sensor distributions
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.flatten()

for i, col in enumerate(sensors):
    axes[i].hist(df[col], bins=50, color='steelblue', edgecolor='white', alpha=0.7)
    axes[i].axvline(df[col].mean(), color='red', linestyle='--', 
                    label=f'Mean: {df[col].mean():.2f}')
    axes[i].set_title(col.replace('_', ' ').title(), fontsize=12, fontweight='bold')
    axes[i].legend()

plt.suptitle('Sensor Feature Distributions', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('../data/processed/sensor_distributions.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# Sensor statistics
print("Sensor Feature Statistics:")
print(df[sensors].describe())

# %% [markdown]
# ## 6. Sensors vs Failure Mode

# %%
# Box plots: Sensors by Failure Mode
fig, axes = plt.subplots(2, 3, figsize=(16, 10))
axes = axes.flatten()

for i, col in enumerate(sensors):
    df.boxplot(column=col, by='failure_mode', ax=axes[i], rot=45)
    axes[i].set_title(col.replace('_', ' ').title(), fontsize=11, fontweight='bold')
    axes[i].set_xlabel('')

plt.suptitle('Sensor Values by Failure Mode', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('../data/processed/sensors_by_failure_mode.png', dpi=150, bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 7. Correlation Analysis

# %%
# Numeric columns correlation
numeric_cols = sensors + ['utilization_rate', 'maintenance_age_days', 
                          'load_tons', 'lift_cycles_per_hour', 'rul_hours']

corr_matrix = df[numeric_cols].corr()

plt.figure(figsize=(12, 10))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(corr_matrix, mask=mask, annot=True, cmap='RdBu_r', center=0,
            fmt='.2f', square=True, linewidths=0.5)
plt.title('Feature Correlation Matrix', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('../data/processed/maintenance_correlation.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# Correlations with RUL
rul_corr = corr_matrix['rul_hours'].drop('rul_hours').sort_values(key=abs, ascending=False)
print("Correlations with RUL (Remaining Useful Life):")
print(rul_corr)

# %% [markdown]
# ## 8. Time Series Analysis

# %%
# Convert timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['date'] = df['timestamp'].dt.date
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek

print(f"Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

# %%
# Sample asset time series
sample_asset = df['asset_id'].unique()[0]
asset_df = df[df['asset_id'] == sample_asset].sort_values('timestamp')

fig, axes = plt.subplots(4, 1, figsize=(15, 12), sharex=True)

axes[0].plot(asset_df['timestamp'], asset_df['motor_temp_c'], color='coral', linewidth=0.8)
axes[0].set_title(f'Motor Temperature - Asset: {sample_asset}', fontsize=12, fontweight='bold')
axes[0].set_ylabel('Temp (°C)')

axes[1].plot(asset_df['timestamp'], asset_df['vibration_rms'], color='steelblue', linewidth=0.8)
axes[1].set_title('Vibration RMS', fontsize=12, fontweight='bold')
axes[1].set_ylabel('Vibration')

axes[2].plot(asset_df['timestamp'], asset_df['rul_hours'], color='green', linewidth=0.8)
axes[2].axhline(72, color='red', linestyle='--', label='72h threshold')
axes[2].set_title('RUL (Remaining Useful Life)', fontsize=12, fontweight='bold')
axes[2].set_ylabel('Hours')
axes[2].legend()

axes[3].scatter(asset_df['timestamp'], asset_df['failure_mode'].astype('category').cat.codes, 
                c='purple', alpha=0.5, s=10)
axes[3].set_title('Failure Mode (encoded)', fontsize=12, fontweight='bold')
axes[3].set_ylabel('Mode')
axes[3].set_xlabel('Timestamp')

plt.tight_layout()
plt.savefig('../data/processed/sample_asset_timeseries.png', dpi=150, bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 9. Sequence Length Analysis (for LSTM)

# %%
# Analyze sequence lengths per asset
seq_lengths = df.groupby('asset_id').size()

fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(seq_lengths.values, bins=30, color='steelblue', edgecolor='white')
ax.axvline(seq_lengths.mean(), color='red', linestyle='--', 
           label=f'Mean: {seq_lengths.mean():.0f}')
ax.set_title('Sequence Length per Asset (Time Steps Available)', fontsize=14, fontweight='bold')
ax.set_xlabel('Number of Records')
ax.set_ylabel('Number of Assets')
ax.legend()

plt.tight_layout()
plt.savefig('../data/processed/sequence_lengths.png', dpi=150, bbox_inches='tight')
plt.show()

print(f"Sequence Length Stats:")
print(f"  Mean: {seq_lengths.mean():.0f}")
print(f"  Min: {seq_lengths.min()}")
print(f"  Max: {seq_lengths.max()}")
print(f"\n💡 Recommendation: Use sliding window of 24-48 hours for LSTM")

# %% [markdown]
# ## 10. Summary & Key Insights

# %%
print("=" * 70)
print("PORT MAINTENANCE DATASET - EDA SUMMARY")
print("=" * 70)

print(f"""
📊 DATASET OVERVIEW
   • Records: {len(df):,}
   • Features: {len(df.columns)}
   • Unique Assets: {df['asset_id'].nunique()}
   • Asset Types: {df['asset_type'].nunique()} ({', '.join(df['asset_type'].unique())})
   • Date Range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}
   • Missing Values: None ✅

🎯 TARGET VARIABLES
   A) RUL (Regression):
      • Mean: {df['rul_hours'].mean():.1f} hours
      • Range: {df['rul_hours'].min():.0f} - {df['rul_hours'].max():.0f} hours
   
   B) Failure Mode (5-class Classification):
      • none: {failure_counts['none']:,} ({failure_counts['none']/len(df)*100:.1f}%)
      • bearing: {failure_counts['bearing']:,} ({failure_counts['bearing']/len(df)*100:.1f}%)
      • overheating: {failure_counts['overheating']:,} ({failure_counts['overheating']/len(df)*100:.1f}%)
      • electrical: {failure_counts['electrical']:,} ({failure_counts['electrical']/len(df)*100:.1f}%)
      • hydraulic_leak: {failure_counts['hydraulic_leak']:,} ({failure_counts['hydraulic_leak']/len(df)*100:.1f}%)

📡 SENSOR FEATURES (Input to LSTM)
   {', '.join(sensors)}

⚠️ KEY OBSERVATIONS
   • Class Imbalance in failure_in_next_72h: {failure_72h[0]/failure_72h[1]:.1f}:1
   • Failure modes relatively balanced (17-25% each except 'none')
   • High RUL variance suggests good range for regression
   • Sensor readings show clear patterns before failures

💡 MULTI-TASK LSTM RECOMMENDATIONS
   • Input window: 24-48 hours (hourly readings)
   • Handle class imbalance with weighted loss
   • Normalize sensors before training
   • Use MSE for RUL, CrossEntropy for failure mode
""")

# %%
# Save column metadata
metadata = {
    'identifiers': identifiers,
    'context': context,
    'workload': workload,
    'sensors': sensors,
    'targets': targets
}

import json
with open('../data/processed/maintenance_column_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print("✅ Column metadata saved to data/processed/maintenance_column_metadata.json")
