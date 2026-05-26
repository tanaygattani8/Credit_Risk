import os
import joblib
import pandas as pd
import numpy as np
from google.cloud import bigquery
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    classification_report,
    confusion_matrix,
    roc_auc_score
)
import xgboost as xgb
import shap
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')
from dotenv import load_dotenv

load_dotenv()
 
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
client     = bigquery.Client(project=PROJECT_ID)

print("── Loading features from BigQuery...")
 
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
        dist1,
        dist2,
        c1, c2, c3, c6, c11, c13, c14,
        id_01, id_02, id_05, id_06
    FROM `{PROJECT_ID}.staging_mart.mart_fraud_features`
""").to_dataframe()
 
print(f"  ✓ Loaded {len(df):,} rows, fraud rate: {df.is_fraud.mean()*100:.2f}%")

FEATURE_COLS = [
    'transaction_amt',
    'card_txn_count_1h',
    'card_txn_count_24h',
    'card_amt_sum_24h',
    'card_avg_amt_30_txns',
    'amt_deviation_from_avg',
    'amt_to_avg_ratio',
    'txn_hour',
    'txn_day_of_week',
    'is_night_transaction',
    'is_weekend',
    'is_free_email',
    'is_mobile',
    'email_domains_match',
    'dist1',
    'dist2',
    'c1', 'c2', 'c3', 'c6', 'c11', 'c13', 'c14',
    'id_01', 'id_02', 'id_05', 'id_06'
]

X = df[FEATURE_COLS].copy()
y = df['is_fraud'].copy()

X = X.fillna(-999)

bool_cols = ['is_night_transaction', 'is_weekend', 'is_free_email',
             'is_mobile', 'email_domains_match']
for col in bool_cols:
    X[col] = X[col].astype(int)

# Train Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\n── Train/test split")
print(f"  Train: {len(X_train):,} rows | fraud: {y_train.sum():,}")
print(f"  Test : {len(X_test):,} rows  | fraud: {y_test.sum():,}")

# Training XGBOOST
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"\n── Training XGBoost (scale_pos_weight={scale_pos_weight:.1f})...")

model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    eval_metric='aucpr',
    early_stopping_rounds=20,
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=50
)


# Evaluation
print("\n── Evaluation")
y_prob = model.predict_proba(X_test)[:, 1]
 
auprc  = average_precision_score(y_test, y_prob)
auroc  = roc_auc_score(y_test, y_prob)
 
# Find optimal threshold by maximising F1
precision, recall, thresholds = precision_recall_curve(y_test, y_prob)
f1_scores  = 2 * precision * recall / (precision + recall + 1e-8)
best_idx   = np.argmax(f1_scores)
best_threshold = thresholds[best_idx]
y_pred     = (y_prob >= best_threshold).astype(int)
 
print(f"  AUPRC (main metric) : {auprc:.4f}  ← aim for >0.50")
print(f"  AUROC               : {auroc:.4f}")
print(f"  Optimal threshold   : {best_threshold:.4f}")
print(f"\n  Classification report at threshold {best_threshold:.2f}:")
print(classification_report(y_test, y_pred, target_names=['Legit', 'Fraud']))
 
cm = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()
print(f"  True Negatives  (correct legit) : {tn:,}")
print(f"  False Positives (wrong alerts)  : {fp:,}")
print(f"  False Negatives (missed fraud)  : {fn:,}")
print(f"  True Positives  (caught fraud)  : {tp:,}")


# SHAP Explainability
print("\n── Computing SHAP values (this takes ~1 min)...")
explainer   = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test.iloc[:2000])  # sample for speed
 
# Global feature importance plot
plt.figure(figsize=(10, 8))
shap.summary_plot(shap_values, X_test.iloc[:2000], plot_type="bar",
                  show=False, max_display=15)
plt.title("Top 15 Features — Global SHAP Importance")
plt.tight_layout()
plt.savefig("shap_importance.png", dpi=150, bbox_inches='tight')
print("  ✓ Saved shap_importance.png")
 
# SHAP beeswarm plot
plt.figure(figsize=(10, 8))
shap.summary_plot(shap_values, X_test.iloc[:2000], show=False, max_display=15)
plt.title("SHAP Feature Impact — Fraud Classifier")
plt.tight_layout()
plt.savefig("shap_beeswarm.png", dpi=150, bbox_inches='tight')
print("  ✓ Saved shap_beeswarm.png")

shap_df = pd.DataFrame(shap_values, columns=FEATURE_COLS)
shap_df['transaction_id'] = df.iloc[
    X_test.index[:2000]
]['transaction_id'].values
shap_df.to_csv("shap_values_sample.csv", index=False)
print("  ✓ Saved shap_values_sample.csv (used by Phase 4 agent)")
 
# Save model
joblib.dump(model, "fraud_model.pkl")
joblib.dump({
    'feature_cols': FEATURE_COLS,
    'threshold': best_threshold,
    'auprc': auprc,
    'auroc': auroc
}, "model_metadata.pkl")
print("\n  ✓ Saved fraud_model.pkl")
print("  ✓ Saved model_metadata.pkl")
 
# Write predictions back to BigQuery 
print("\n── Writing predictions to BigQuery...")
 
all_probs = model.predict_proba(X)[:, 1]
preds_df = pd.DataFrame({
    'transaction_id'  : df['transaction_id'],
    'is_fraud_actual' : df['is_fraud'],
    'fraud_score'     : all_probs.round(6),
    'is_fraud_predicted': (all_probs >= best_threshold).astype(int)
})
 
table_ref = f"{PROJECT_ID}.staging_mart.mart_fraud_predictions"
job_config = bigquery.LoadJobConfig(
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
)
job = client.load_table_from_dataframe(preds_df, table_ref, job_config=job_config)
job.result()
print(f"  ✓ Wrote {len(preds_df):,} predictions to {table_ref}")