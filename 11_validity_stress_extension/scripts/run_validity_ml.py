#!/usr/bin/env python3

import argparse
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

import matplotlib.pyplot as plt

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def connect(args):
    kwargs = {
        "host": args.host,
        "port": args.port,
        "dbname": args.db,
        "user": args.user,
    }
    password = args.password or os.environ.get("PGPASSWORD")
    if password:
        kwargs["password"] = password
    return psycopg2.connect(**kwargs)


def make_encoder():
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def safe_auc(y_true, y_score):
    try:
        if len(set(y_true)) < 2:
            return np.nan
        return roc_auc_score(y_true, y_score)
    except Exception:
        return np.nan


def expected_calibration_error(y_true, y_prob, n_bins=10):
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (y_prob > lo) & (y_prob <= hi)
        if lo == 0.0:
            mask = (y_prob >= lo) & (y_prob <= hi)
        if not np.any(mask):
            continue
        conf = np.mean(y_prob[mask])
        acc = np.mean(y_true[mask])
        ece += (np.sum(mask) / len(y_true)) * abs(acc - conf)
    return float(ece)


def wilson_ci(successes, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    phat = successes / n
    denom = 1.0 + (z * z / n)
    center = (phat + (z * z) / (2 * n)) / denom
    half = z * math.sqrt((phat * (1 - phat) / n) + (z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def metric_row(model_name, y_true, y_pred, y_prob, split_id=None):
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    y_prob = np.asarray(y_prob).astype(float)

    invalid_mask = y_true == 0
    invalid_total = int(np.sum(invalid_mask))
    invalid_recalled = int(np.sum((y_true == 0) & (y_pred == 0)))
    recall_invalid_ci_low, recall_invalid_ci_high = wilson_ci(invalid_recalled, invalid_total)

    try:
        ll = log_loss(y_true, np.vstack([1 - y_prob, y_prob]).T, labels=[0, 1])
    except Exception:
        ll = np.nan

    return {
        "split_id": split_id,
        "model": model_name,
        "n_test": len(y_true),
        "n_invalid_test": invalid_total,
        "accuracy": accuracy_score(y_true, y_pred),
        "f1_valid": f1_score(y_true, y_pred, pos_label=1, zero_division=0),
        "f1_invalid": f1_score(y_true, y_pred, pos_label=0, zero_division=0),
        "precision_invalid": precision_score(y_true, y_pred, pos_label=0, zero_division=0),
        "recall_invalid": recall_score(y_true, y_pred, pos_label=0, zero_division=0),
        "recall_invalid_ci_low_wilson": recall_invalid_ci_low,
        "recall_invalid_ci_high_wilson": recall_invalid_ci_high,
        "roc_auc": safe_auc(y_true, y_prob),
        "brier": brier_score_loss(y_true, y_prob),
        "log_loss": ll,
        "ece_10bin": expected_calibration_error(y_true, y_prob, n_bins=10),
    }


def summarize_splits(split_df):
    metric_cols = [
        "accuracy",
        "f1_valid",
        "f1_invalid",
        "precision_invalid",
        "recall_invalid",
        "roc_auc",
        "brier",
        "log_loss",
        "ece_10bin",
    ]
    rows = []
    for model, g in split_df.groupby("model"):
        row = {"model": model, "n_splits": len(g)}
        for col in metric_cols:
            vals = pd.to_numeric(g[col], errors="coerce").dropna()
            if vals.empty:
                row[f"{col}_mean"] = np.nan
                row[f"{col}_std"] = np.nan
                row[f"{col}_ci95_low"] = np.nan
                row[f"{col}_ci95_high"] = np.nan
                continue
            mean = vals.mean()
            std = vals.std(ddof=1) if len(vals) > 1 else 0.0
            half = 1.96 * std / math.sqrt(len(vals)) if len(vals) > 1 else 0.0
            row[f"{col}_mean"] = mean
            row[f"{col}_std"] = std
            row[f"{col}_ci95_low"] = mean - half
            row[f"{col}_ci95_high"] = mean + half
        rows.append(row)
    return pd.DataFrame(rows)


def make_model():
    return Pipeline(
        steps=[
            (
                "prep",
                ColumnTransformer(
                    transformers=[
                        ("cat", make_encoder(), [
                            "facility_key",
                            "building_type",
                            "loc_nurse_unit_cd",
                            "loc_room_cd",
                            "loc_bed_cd",
                        ]),
                        ("num", "passthrough", [
                            "f_admit_today",
                            "f_disch_today",
                            "f_census_live",
                            "f_bedded_census_live",
                            "f_has_active_discharge_order",
                            "x_room_missing",
                            "x_bed_missing",
                            "x_los_hours",
                        ]),
                    ]
                ),
            ),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=300,
                    random_state=42,
                    class_weight="balanced",
                    min_samples_leaf=2,
                    bootstrap=True,
                ),
            ),
        ]
    )


def prepare_xy(ml_df):
    feature_cols = [
        "facility_key",
        "building_type",
        "loc_nurse_unit_cd",
        "loc_room_cd",
        "loc_bed_cd",
        "f_admit_today",
        "f_disch_today",
        "f_census_live",
        "f_bedded_census_live",
        "f_has_active_discharge_order",
        "x_room_missing",
        "x_bed_missing",
        "x_los_hours",
    ]
    df = ml_df[feature_cols + ["target_acbp_valid"]].copy()
    df["x_los_hours"] = df["x_los_hours"].fillna(-1)
    for col in ["loc_nurse_unit_cd", "loc_room_cd", "loc_bed_cd"]:
        df[col] = df[col].astype("Int64").astype(str).replace("<NA>", "NULL")
    X = df[feature_cols]
    y = df["target_acbp_valid"].astype(int)
    return X, y


def save_bar_plot(series, title, ylabel, path):
    fig, ax = plt.subplots(figsize=(8, 5))
    series.plot(kind="bar", ax=ax)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def run_leave_invalid_type_out(ml_df, X, y):
    if "case_type" not in ml_df.columns:
        return pd.DataFrame()

    rows = []
    invalid_cases = sorted([
        c for c in ml_df.loc[ml_df["target_acbp_valid"] == 0, "case_type"].dropna().unique()
        if str(c).startswith(("BEDDED", "ACTIVE", "DISCHARGE", "LOCATION"))
    ])

    valid_idx_all = ml_df.index[ml_df["target_acbp_valid"] == 1].to_numpy()

    rng = np.random.default_rng(42)

    for case in invalid_cases:
        heldout_invalid_idx = ml_df.index[(ml_df["case_type"] == case) & (ml_df["target_acbp_valid"] == 0)].to_numpy()
        if len(heldout_invalid_idx) == 0:
            continue

        n_valid = min(len(valid_idx_all), max(len(heldout_invalid_idx), 50))
        heldout_valid_idx = rng.choice(valid_idx_all, size=n_valid, replace=False)

        test_idx = np.concatenate([heldout_invalid_idx, heldout_valid_idx])
        train_mask = np.ones(len(ml_df), dtype=bool)
        train_mask[test_idx] = False
        train_mask[ml_df["case_type"].to_numpy() == case] = False

        train_idx = np.where(train_mask)[0]

        if len(np.unique(y.iloc[train_idx])) < 2:
            continue

        model = make_model()
        model.fit(X.iloc[train_idx], y.iloc[train_idx])

        y_true = y.iloc[test_idx]
        y_pred = model.predict(X.iloc[test_idx])
        y_prob = model.predict_proba(X.iloc[test_idx])[:, 1]

        row = metric_row(f"leave_invalid_type_out:{case}", y_true, y_pred, y_prob)
        row["heldout_case_type"] = case
        rows.append(row)

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Run ACBP validity-stress ML diagnostic with uncertainty.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=55432, type=int)
    parser.add_argument("--db", default="acbp_db")
    parser.add_argument("--user", default="acbp")
    parser.add_argument("--password", default="acbp")
    parser.add_argument("--outdir", default="11_validity_stress_extension/outputs")
    parser.add_argument("--n_splits", default=30, type=int)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    plots_dir = outdir.parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    with connect(args) as conn:
        ml_df = pd.read_sql_query("SELECT * FROM validity_ext.ml_dataset;", conn)
        dotk_df = pd.read_sql_query("SELECT * FROM validity_ext.dotk_complexity_summary;", conn)
        case_df = pd.read_sql_query("SELECT * FROM validity_ext.case_type_validity_summary;", conn)
        rule_df = pd.read_sql_query("SELECT * FROM validity_ext.rule_violation_summary;", conn)

    if ml_df.empty:
        raise RuntimeError("validity_ext.ml_dataset is empty. Run the SQL pipeline first.")

    ml_df.to_csv(outdir / "validity_ml_dataset_snapshot.csv", index=False)
    dotk_df.to_csv(outdir / "dotk_complexity_summary.csv", index=False)
    case_df.to_csv(outdir / "case_type_validity_summary.csv", index=False)
    rule_df.to_csv(outdir / "rule_violation_summary.csv", index=False)

    X, y = prepare_xy(ml_df)

    if len(set(y)) < 2:
        findings = "# Validity ML Key Findings\n\nOnly one class is present; ML diagnostic skipped.\n"
        (outdir / "ml_key_findings.md").write_text(findings, encoding="utf-8")
        print(findings)
        return

    splitter = StratifiedShuffleSplit(n_splits=args.n_splits, test_size=0.30, random_state=42)
    split_rows = []

    last_y_test = None
    last_y_pred_ml = None
    last_y_prob_ml = None
    last_y_pred_blind = None
    last_y_prob_blind = None

    for split_id, (train_idx, test_idx) in enumerate(splitter.split(X, y), start=1):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        y_pred_blind = np.ones_like(y_test)
        y_prob_blind = np.ones_like(y_test, dtype=float)
        split_rows.append(metric_row("live_blind_all_valid_baseline", y_test, y_pred_blind, y_prob_blind, split_id))

        model = make_model()
        model.fit(X_train, y_train)
        y_pred_ml = model.predict(X_test)
        y_prob_ml = model.predict_proba(X_test)[:, 1]
        split_rows.append(metric_row("ml_validity_classifier", y_test, y_pred_ml, y_prob_ml, split_id))

        last_y_test = y_test
        last_y_pred_ml = y_pred_ml
        last_y_prob_ml = y_prob_ml
        last_y_pred_blind = y_pred_blind
        last_y_prob_blind = y_prob_blind

    split_df = pd.DataFrame(split_rows)
    split_df.to_csv(outdir / "validity_ml_split_metrics.csv", index=False)

    uncertainty_summary = summarize_splits(split_df)
    uncertainty_summary.to_csv(outdir / "validity_ml_uncertainty_summary.csv", index=False)

    leave_case_df = run_leave_invalid_type_out(ml_df.reset_index(drop=True), X.reset_index(drop=True), y.reset_index(drop=True))
    leave_case_df.to_csv(outdir / "validity_ml_leave_invalid_type_out.csv", index=False)

    # Backward-compatible single table: use the last split's two models.
    metrics = pd.DataFrame([
        metric_row("live_blind_all_valid_baseline", last_y_test, last_y_pred_blind, last_y_prob_blind, args.n_splits),
        metric_row("ml_validity_classifier", last_y_test, last_y_pred_ml, last_y_prob_ml, args.n_splits),
    ])
    metrics.insert(1, "n_rows", len(ml_df))
    metrics.insert(2, "n_train", int(len(ml_df) * 0.70))
    metrics.insert(3, "valid_rate", float(y.mean()))
    metrics.insert(4, "invalid_rate", float(1 - y.mean()))
    metrics.to_csv(outdir / "validity_ml_metrics.csv", index=False)

    report = classification_report(
        last_y_test,
        last_y_pred_ml,
        target_names=["invalid", "valid"],
        output_dict=True,
        zero_division=0,
    )
    pd.DataFrame(report).transpose().to_csv(outdir / "validity_ml_classification_report.csv")

    if not dotk_df.empty:
        dotk = dotk_df.iloc[0]
        save_bar_plot(pd.Series({
            "Observed": dotk["d_obs"],
            "Valid": dotk["d_valid_obs"],
            "Invalid": dotk["d_invalid_obs"],
        }), "DotK State Support Counts", "Distinct states", plots_dir / "dotk_support_counts.png")

        save_bar_plot(pd.Series({
            "K_obs": dotk["k_obs"],
            "K_valid": dotk["k_valid"],
            "K_invalid": dotk["k_invalid"],
            "K_gap": dotk["k_gap"],
        }), "DotK Complexity Decomposition", "Bits", plots_dir / "dotk_bits.png")

    # Plot uncertainty summary.
    plot_df = uncertainty_summary.set_index("model")
    cols = ["accuracy_mean", "f1_invalid_mean", "recall_invalid_mean", "roc_auc_mean", "brier_mean", "ece_10bin_mean"]
    fig, ax = plt.subplots(figsize=(10, 5))
    plot_df[cols].transpose().plot(kind="bar", ax=ax)
    ax.set_title("Validity ML Diagnostic with Repeated-Split Uncertainty")
    ax.set_ylabel("Score / Error")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    fig.savefig(plots_dir / "validity_ml_uncertainty_metrics.png", dpi=200)
    plt.close(fig)

    # Build readable markdown.
    dotk_md = ""
    if not dotk_df.empty:
        d = dotk_df.iloc[0]
        dotk_md = f"""
## DotK Complexity

- Observed distinct states: {int(d['d_obs'])}
- ACBP-valid distinct states: {int(d['d_valid_obs'])}
- ACBP-invalid distinct states: {int(d['d_invalid_obs'])}
- Invalid support percentage: {float(d['invalid_support_pct']):.2f}%
- K_obs: {float(d['k_obs']):.4f} bits
- K_valid: {float(d['k_valid']):.4f} bits
- K_invalid: {float(d['k_invalid']):.4f} bits
- K_gap: {float(d['k_gap']):.4f} bits
"""

    def fmt_summary(model_name, metric):
        row = uncertainty_summary[uncertainty_summary["model"] == model_name].iloc[0]
        return f"{row[metric + '_mean']:.4f} [{row[metric + '_ci95_low']:.4f}, {row[metric + '_ci95_high']:.4f}]"

    findings = f"""# Validity ML Key Findings

This extension uses the same benchmark database but creates an isolated `validity_ext` schema.

The source `cerner`, `cerner_ref`, and `cbp` schemas are not modified.

{dotk_md}

## Uncertainty-aware ML Diagnostic

The ML target is `target_acbp_valid`.

This is not a clinical outcome prediction model. It is a validity-detection diagnostic showing whether invalid feature-state spaces are separable from the same flag and category surface.

To avoid reporting a single overfit train/test split, the script now uses {args.n_splits} repeated stratified splits and reports mean metrics with approximate 95% confidence intervals.

### Live-blind baseline

The Live SQL baseline computes dashboard states but has no explicit validity boundary. Therefore the baseline treats all states as valid.

- Accuracy: {fmt_summary('live_blind_all_valid_baseline', 'accuracy')}
- F1 invalid: {fmt_summary('live_blind_all_valid_baseline', 'f1_invalid')}
- Invalid recall: {fmt_summary('live_blind_all_valid_baseline', 'recall_invalid')}
- ROC-AUC: {fmt_summary('live_blind_all_valid_baseline', 'roc_auc')}
- Brier score: {fmt_summary('live_blind_all_valid_baseline', 'brier')}
- ECE: {fmt_summary('live_blind_all_valid_baseline', 'ece_10bin')}

### ACBP-labeled validity classifier

The classifier is trained on flags and categories to approximate the deterministic ACBP validity label.

- Accuracy: {fmt_summary('ml_validity_classifier', 'accuracy')}
- F1 invalid: {fmt_summary('ml_validity_classifier', 'f1_invalid')}
- Invalid recall: {fmt_summary('ml_validity_classifier', 'recall_invalid')}
- ROC-AUC: {fmt_summary('ml_validity_classifier', 'roc_auc')}
- Brier score: {fmt_summary('ml_validity_classifier', 'brier')}
- ECE: {fmt_summary('ml_validity_classifier', 'ece_10bin')}

## Leave-invalid-type-out diagnostic

A secondary stress check holds out each invalidity type from training and tests whether the model detects that unseen invalidity mechanism. Results are saved in:

`validity_ml_leave_invalid_type_out.csv`

## Interpretation

Live SQL can compute dashboard metrics over a feature-state surface, but it does not explicitly label invalid states.

ACBP provides the deterministic validity boundary.

DotK then measures how much of the observed state-space support is valid versus invalid on a log-scale.
"""

    (outdir / "ml_key_findings.md").write_text(findings, encoding="utf-8")

    print(uncertainty_summary.to_string(index=False))
    print("")
    print(f"Saved outputs to: {outdir}")
    print(f"Saved plots to: {plots_dir}")


if __name__ == "__main__":
    main()
