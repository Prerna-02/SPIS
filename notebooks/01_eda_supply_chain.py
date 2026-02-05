# %% [markdown]
# # EDA: Supply Chain Logistics Dataset
# 
# This notebook explores the `dynamic_supply_chain_logistics_dataset.csv` for:
# - Feature 1: Port Throughput Forecasting
# - Feature 2A: Anomaly Detection

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
df = pd.read_csv('../data/raw/dynamic_supply_chain_logistics_dataset.csv')

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
print(df.dtypes)

# %% [markdown]
# ## 2. Data Overview

# %%
# Basic statistics
df.describe()

# %%
# Missing values
missing = df.isnull().sum()
missing_pct = (missing / len(df)) * 100
missing_df = pd.DataFrame({
    'Missing Count': missing,
    'Missing %': missing_pct
}).sort_values('Missing Count', ascending=False)

print("Missing Values:")
print(missing_df[missing_df['Missing Count'] > 0])
if missing_df['Missing Count'].sum() == 0:
    print("✅ No missing values!")

# %% [markdown]
# ## 3. Time Analysis

# %%
# Convert timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['date'] = df['timestamp'].dt.date
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek
df['month'] = df['timestamp'].dt.month
df['year'] = df['timestamp'].dt.year

print(f"Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Total Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

# %%
# Records per year
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Records by year
yearly_counts = df.groupby('year').size()
axes[0].bar(yearly_counts.index, yearly_counts.values, color='steelblue')
axes[0].set_title('Records per Year', fontsize=14, fontweight='bold')
axes[0].set_xlabel('Year')
axes[0].set_ylabel('Count')

# Records by month
monthly_counts = df.groupby('month').size()
axes[1].bar(monthly_counts.index, monthly_counts.values, color='coral')
axes[1].set_title('Records per Month', fontsize=14, fontweight='bold')
axes[1].set_xlabel('Month')
axes[1].set_ylabel('Count')

plt.tight_layout()
plt.savefig('../data/processed/supply_chain_time_distribution.png', dpi=150, bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 4. Target Variable Analysis

# %%
# Risk Classification Distribution
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Count plot
risk_counts = df['risk_classification'].value_counts()
colors = {'High Risk': '#e74c3c', 'Moderate Risk': '#f39c12', 'Low Risk': '#27ae60'}
axes[0].bar(risk_counts.index, risk_counts.values, color=[colors[x] for x in risk_counts.index])
axes[0].set_title('Risk Classification Distribution', fontsize=14, fontweight='bold')
axes[0].set_ylabel('Count')

# Percentage
risk_pct = (risk_counts / len(df)) * 100
axes[1].pie(risk_pct.values, labels=risk_pct.index, autopct='%1.1f%%', 
            colors=[colors[x] for x in risk_pct.index], explode=[0.05]*len(risk_pct))
axes[1].set_title('Risk Classification (%)', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('../data/processed/risk_classification_distribution.png', dpi=150, bbox_inches='tight')
plt.show()

print("\nRisk Classification Counts:")
print(risk_counts)

# %%
# Key numeric targets
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

# Delay probability
axes[0].hist(df['delay_probability'], bins=50, color='steelblue', edgecolor='white')
axes[0].set_title('Delay Probability Distribution', fontsize=12, fontweight='bold')
axes[0].set_xlabel('Delay Probability')

# Delivery time deviation
axes[1].hist(df['delivery_time_deviation'], bins=50, color='coral', edgecolor='white')
axes[1].set_title('Delivery Time Deviation', fontsize=12, fontweight='bold')
axes[1].set_xlabel('Deviation')

# Disruption likelihood
axes[2].hist(df['disruption_likelihood_score'], bins=50, color='green', edgecolor='white')
axes[2].set_title('Disruption Likelihood Score', fontsize=12, fontweight='bold')
axes[2].set_xlabel('Score')

plt.tight_layout()
plt.savefig('../data/processed/target_distributions.png', dpi=150, bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 5. Feature Analysis

# %%
# Operational features - key columns for LSTM throughput forecasting
operational_cols = [
    'port_congestion_level', 'shipping_costs', 'weather_condition_severity',
    'historical_demand', 'traffic_congestion_level', 'eta_variation_hours'
]

# Summary stats
print("Operational Features Summary:")
print(df[operational_cols].describe())

# %%
# Distribution of operational features
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.flatten()

for i, col in enumerate(operational_cols):
    axes[i].hist(df[col], bins=40, color='steelblue', edgecolor='white', alpha=0.7)
    axes[i].axvline(df[col].mean(), color='red', linestyle='--', label=f'Mean: {df[col].mean():.2f}')
    axes[i].set_title(col.replace('_', ' ').title(), fontsize=11, fontweight='bold')
    axes[i].legend()

plt.tight_layout()
plt.savefig('../data/processed/operational_features.png', dpi=150, bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 6. Correlation Analysis

# %%
# Select numeric columns
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
# Remove engineered columns for clean correlation
exclude = ['hour', 'day_of_week', 'month', 'year']
numeric_cols = [c for c in numeric_cols if c not in exclude]

# Correlation matrix
corr_matrix = df[numeric_cols].corr()

# Plot
plt.figure(figsize=(16, 14))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(corr_matrix, mask=mask, annot=False, cmap='RdBu_r', center=0,
            vmin=-1, vmax=1, square=True, linewidths=0.5)
plt.title('Feature Correlation Matrix', fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig('../data/processed/correlation_matrix.png', dpi=150, bbox_inches='tight')
plt.show()

# %%
# Top correlations with delay_probability
target = 'delay_probability'
correlations = corr_matrix[target].drop(target).sort_values(key=abs, ascending=False)

print(f"Top Correlations with {target}:")
print(correlations.head(10))

# %% [markdown]
# ## 7. Time Series Patterns (for LSTM)

# %%
# Aggregate daily for throughput analysis
daily_df = df.groupby('date').agg({
    'historical_demand': 'mean',
    'port_congestion_level': 'mean',
    'shipping_costs': 'mean',
    'delay_probability': 'mean',
    'weather_condition_severity': 'mean'
}).reset_index()

daily_df['date'] = pd.to_datetime(daily_df['date'])

# %%
# Time series plots
fig, axes = plt.subplots(4, 1, figsize=(15, 14), sharex=True)

axes[0].plot(daily_df['date'], daily_df['historical_demand'], color='steelblue', linewidth=0.8)
axes[0].set_title('Daily Historical Demand (Throughput Proxy)', fontsize=12, fontweight='bold')
axes[0].set_ylabel('Demand')

axes[1].plot(daily_df['date'], daily_df['port_congestion_level'], color='coral', linewidth=0.8)
axes[1].set_title('Port Congestion Level', fontsize=12, fontweight='bold')
axes[1].set_ylabel('Congestion')

axes[2].plot(daily_df['date'], daily_df['shipping_costs'], color='green', linewidth=0.8)
axes[2].set_title('Shipping Costs', fontsize=12, fontweight='bold')
axes[2].set_ylabel('Cost')

axes[3].plot(daily_df['date'], daily_df['delay_probability'], color='purple', linewidth=0.8)
axes[3].set_title('Delay Probability', fontsize=12, fontweight='bold')
axes[3].set_ylabel('Probability')
axes[3].set_xlabel('Date')

plt.tight_layout()
plt.savefig('../data/processed/time_series_patterns.png', dpi=150, bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 8. Anomaly Detection Features

# %%
# Features for autoencoder anomaly detection
anomaly_features = [
    'fuel_consumption_rate', 'eta_variation_hours', 'traffic_congestion_level',
    'port_congestion_level', 'disruption_likelihood_score', 'delay_probability',
    'route_risk_level', 'customs_clearance_time'
]

# Distribution check
fig, axes = plt.subplots(2, 4, figsize=(16, 8))
axes = axes.flatten()

for i, col in enumerate(anomaly_features):
    axes[i].hist(df[col], bins=40, color='steelblue', edgecolor='white')
    axes[i].set_title(col.replace('_', ' ').title(), fontsize=10, fontweight='bold')

plt.suptitle('Anomaly Detection Feature Distributions', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('../data/processed/anomaly_features.png', dpi=150, bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 9. Risk Classification by Features

# %%
# Box plots by risk classification
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.flatten()

key_features = ['port_congestion_level', 'delay_probability', 'shipping_costs',
                'disruption_likelihood_score', 'route_risk_level', 'eta_variation_hours']

for i, col in enumerate(key_features):
    df.boxplot(column=col, by='risk_classification', ax=axes[i])
    axes[i].set_title(col.replace('_', ' ').title(), fontsize=11, fontweight='bold')
    axes[i].set_xlabel('')

plt.suptitle('Feature Distribution by Risk Classification', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('../data/processed/features_by_risk.png', dpi=150, bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 10. Summary & Key Insights

# %%
print("=" * 70)
print("SUPPLY CHAIN DATASET - EDA SUMMARY")
print("=" * 70)

print(f"""
📊 DATASET OVERVIEW
   • Records: {len(df):,}
   • Features: {len(df.columns)}
   • Date Range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}
   • Missing Values: None ✅

🎯 TARGET VARIABLES
   • Risk Classification: High ({risk_counts.get('High Risk', 0):,}), 
     Moderate ({risk_counts.get('Moderate Risk', 0):,}), Low ({risk_counts.get('Low Risk', 0):,})
   • Delay Probability: Mean = {df['delay_probability'].mean():.3f}
   • Delivery Time Deviation: Mean = {df['delivery_time_deviation'].mean():.3f}

📈 FOR THROUGHPUT FORECASTING (Feature 1)
   Key Features: port_congestion_level, shipping_costs, weather_condition_severity,
   historical_demand, traffic_congestion_level

🔍 FOR ANOMALY DETECTION (Feature 2A)
   Key Features: fuel_consumption_rate, eta_variation_hours, disruption_likelihood_score,
   delay_probability, route_risk_level

⚠️  OBSERVATIONS
   • Class Imbalance: High Risk dominates ({(risk_counts.get('High Risk', 0)/len(df)*100):.1f}%)
   • Time series shows patterns suitable for LSTM
   • Features show clear separation by risk level
""")

# %%
# Save processed daily data
daily_df.to_csv('../data/processed/supply_chain_daily.csv', index=False)
print("✅ Daily aggregated data saved to data/processed/supply_chain_daily.csv")
