import os
import pandas as pd
import numpy as np 
from google.cloud import bigquery
from scipy import stats 
import matplotlib.pyplot as plt 
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
client = bigquery.Client(project=PROJECT_ID)

df = client.query(f"""
    SELECT
        transaction_id,
        is_fraud,
        transaction_amt,
        card_txn_count_1h,
        card_txn_count_24h,
        card_amt_sum_24h,
        card_avg_amt_30_txns,
        amt_deviation_from_avg,
        amt_to_avg_ratio,
        txn_hour,
        txn_day_of_week,
        is_night_transaction,
        is_weekend,
        is_free_email,
        is_mobile,
        email_domains_match,
        c1, c2, c3, c6, c11, c13, c14
    FROM `{PROJECT_ID}.staging_mart.mart_fraud_features`
""").to_dataframe()

print(f"  ✓ Loaded {len(df):,} rows")
print(f"  ✓ Fraud rate: {df.is_fraud.mean()*100:.2f}%")
print(f"  ✓ Fraud transactions: {df.is_fraud.sum():,}")
print(f"  ✓ Legit transactions: {(df.is_fraud==0).sum():,}")

fraud = df[df.is_fraud == 1]
legit = df[df.is_fraud == 0]


# Mann-Whitney U tests
print("\n── Mann-Whitney U Tests (are fraud/legit populations different?)")
print(f"  {'Feature':<30} {'Fraud median':>14} {'Legit median':>14} {'p-value':>12} {'Significant':>12}")
print("  " + "-"*84)
 
features_to_test = [
    'transaction_amt',
    'card_txn_count_1h',
    'card_txn_count_24h',
    'card_amt_sum_24h',
    'amt_deviation_from_avg',
    'amt_to_avg_ratio',
    'c1', 'c2', 'c6', 'c11', 'c13', 'c14'
]

results = []
for feat in features_to_test:
    f_vals = fraud[feat].dropna()
    l_vals = legit[feat].dropna()
    if len(f_vals) < 10 or len(l_vals) < 10:
        continue
    stat, p = stats.mannwhitneyu(f_vals, l_vals, alternative='two-sided')
    sig = "✓ YES" if p < 0.05 else "✗ NO"
    results.append({'feature': feat, 'p_value': p, 'significant': p < 0.05})
    print(f"  {feat:<30} {f_vals.median():>14.4f} {l_vals.median():>14.4f} {p:>12.2e} {sig:>12}")
 
sig_count = sum(r['significant'] for r in results)
print(f"\n  ✓ {sig_count}/{len(results)} features significantly different between fraud and legit")


# Key Insights
print("\n── Key Fraud Insights")
 
# Night transactions
night_fraud = df[df.is_night_transaction == 1].is_fraud.mean() * 100
day_fraud   = df[df.is_night_transaction == 0].is_fraud.mean() * 100
print(f"  Night transaction fraud rate : {night_fraud:.2f}%")
print(f"  Day transaction fraud rate   : {day_fraud:.2f}%")
print(f"  Night is {night_fraud/day_fraud:.1f}x more likely to be fraud")
 
# Free email
free_email_fraud = df[df.is_free_email == 1].is_fraud.mean() * 100
corp_email_fraud = df[df.is_free_email == 0].is_fraud.mean() * 100
print(f"\n  Free email fraud rate  : {free_email_fraud:.2f}%")
print(f"  Corp email fraud rate  : {corp_email_fraud:.2f}%")
 
# High velocity
high_vel = df[df.card_txn_count_1h > 3].is_fraud.mean() * 100
low_vel  = df[df.card_txn_count_1h <= 3].is_fraud.mean() * 100
print(f"\n  High velocity (>3 txns/hr) fraud rate : {high_vel:.2f}%")
print(f"  Low velocity (<=3 txns/hr) fraud rate : {low_vel:.2f}%")

# Saving Plots
print("\n── Generating plots...")
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle('Fraud vs Legit — Feature Distributions', fontsize=14, fontweight='bold')
 
# Transaction amount
ax = axes[0, 0]
ax.hist(legit.transaction_amt.clip(0, 1000), bins=50, alpha=0.6, label='Legit', color='steelblue')
ax.hist(fraud.transaction_amt.clip(0, 1000), bins=50, alpha=0.6, label='Fraud', color='tomato')
ax.set_title('Transaction Amount (clipped at $1000)')
ax.set_xlabel('Amount ($)')
ax.legend()
 
# Velocity 1h
ax = axes[0, 1]
ax.hist(legit.card_txn_count_1h.clip(0, 20), bins=20, alpha=0.6, label='Legit', color='steelblue')
ax.hist(fraud.card_txn_count_1h.clip(0, 20), bins=20, alpha=0.6, label='Fraud', color='tomato')
ax.set_title('Card Velocity (last 1 hour)')
ax.set_xlabel('Transaction count')
ax.legend()
 
# Txn hour
ax = axes[1, 0]
legit_hours = legit.txn_hour.value_counts().sort_index()
fraud_hours = fraud.txn_hour.value_counts().sort_index()
ax.plot(legit_hours.index, legit_hours.values, label='Legit', color='steelblue')
ax.plot(fraud_hours.index, fraud_hours.values, label='Fraud', color='tomato')
ax.set_title('Transactions by Hour of Day')
ax.set_xlabel('Hour')
ax.legend()
 
# Fraud rate by hour
ax = axes[1, 1]
hourly_fraud = df.groupby('txn_hour').is_fraud.mean() * 100
ax.bar(hourly_fraud.index, hourly_fraud.values, color='tomato', alpha=0.7)
ax.set_title('Fraud Rate (%) by Hour of Day')
ax.set_xlabel('Hour')
ax.set_ylabel('Fraud rate (%)')
 
plt.tight_layout()
plt.savefig('fraud_analysis.png', dpi=150, bbox_inches='tight')
print("  ✓ Saved fraud_analysis.png")