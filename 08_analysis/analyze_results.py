#!/usr/bin/env python3
"""
analyze_results.py (DETAILED, FINAL)

Reads:
  ACBP_Clinical_Dashboard_Experiment/07_metrics_collection/raw_logs/combined_metrics.csv

Assumes CSV columns (your collector writes these):
  timestamp_utc, iteration, condition, ok, elapsed_ms,
  cpu_percent, mem_used, mem_limit, mem_percent,
  shared_hit, result_hash, result_preview, stderr_preview

Produces:
  1) Console summary:
     - Latency stats for feed_cycle / live / cbp
     - Correctness (hash match rate live vs cbp)
     - Speedup stats (live/cbp)
     - Buffer stats (shared_hit) and ratio stats (live/cbp) using only iterations where buffers exist
  2) Plots saved into:
     ACBP_Clinical_Dashboard_Experiment/08_analysis/plots/
        latency_timeseries.png
        latency_boxplot.png
        speedup_timeseries.png
        resources_timeseries.png
        buffers_hits_timeseries.png
        buffers_ratio_timeseries.png
  3) Markdown summary:
     ACBP_Clinical_Dashboard_Experiment/08_analysis/stats_summary.md

Usage:
  python ACBP_Clinical_Dashboard_Experiment/08_analysis/analyze_results.py
  python ACBP_Clinical_Dashboard_Experiment/08_analysis/analyze_results.py --input path/to/combined_metrics.csv
"""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DEFAULT_INPUT = Path("ACBP_Clinical_Dashboard_Experiment/07_metrics_collection/raw_logs/combined_metrics.csv")
PLOTS_DIR = Path("ACBP_Clinical_Dashboard_Experiment/08_analysis/plots")
SUMMARY_MD = Path("ACBP_Clinical_Dashboard_Experiment/08_analysis/stats_summary.md")


# ----------------------------
# Helpers
# ----------------------------
def _to_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def summarize(values):
    """
    Return robust summary stats for a numeric array-like.
    """
    x = np.array(values, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return {"n": 0}
    return {
        "n": int(len(x)),
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "p95": float(np.percentile(x, 95)),
        "min": float(np.min(x)),
        "max": float(np.max(x)),
        "std": float(np.std(x, ddof=1)) if len(x) > 1 else 0.0,
        "cv": float((np.std(x, ddof=1) / np.mean(x)) if len(x) > 1 and np.mean(x) != 0 else 0.0),
    }


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


# ----------------------------
# Load + clean
# ----------------------------
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Numeric coercions
    df["iteration"] = _to_numeric(df.get("iteration"))
    df["ok"] = _to_numeric(df.get("ok"))
    df["elapsed_ms"] = _to_numeric(df.get("elapsed_ms"))
    df["cpu_percent"] = _to_numeric(df.get("cpu_percent"))
    df["mem_percent"] = _to_numeric(df.get("mem_percent"))
    df["shared_hit"] = _to_numeric(df.get("shared_hit"))

    # Normalize condition strings just in case
    df["condition"] = df["condition"].astype(str).str.strip()

    return df


# ----------------------------
# Correctness (hash match)
# ----------------------------
def hash_equivalence(df: pd.DataFrame) -> dict:
    """
    Compare result_hash between live and cbp for paired iterations (ok=1).
    """
    sub = df[(df["ok"] == 1) & (df["condition"].isin(["live", "cbp"]))].copy()

    piv = sub.pivot_table(
        index="iteration",
        columns="condition",
        values="result_hash",
        aggfunc="first",
    ).dropna()

    if piv.empty:
        return {"pairs": 0, "match_rate": np.nan, "mismatches": 0}

    eq = (piv["live"] == piv["cbp"])
    return {
        "pairs": int(len(piv)),
        "match_rate": float(eq.mean()),
        "mismatches": int((~eq).sum()),
    }


# ----------------------------
# Speedup (latency ratio)
# ----------------------------
def speedup_stats(df: pd.DataFrame):
    """
    live/cbp speedup over paired iterations.
    """
    sub = df[(df["ok"] == 1) & (df["condition"].isin(["live", "cbp"]))].copy()

    piv = sub.pivot_table(
        index="iteration",
        columns="condition",
        values="elapsed_ms",
        aggfunc="first",
    ).dropna()

    if piv.empty:
        return {"pairs": 0}, None

    piv["speedup_live_over_cbp"] = piv["live"] / piv["cbp"]
    st = summarize(piv["speedup_live_over_cbp"].values)
    st["pairs"] = st.pop("n")
    return st, piv


# ----------------------------
# Buffers (shared_hit)
# ----------------------------
def buffer_ratio_stats(df: pd.DataFrame):
    """
    Buffer ratio stats using ONLY iterations where BOTH live and cbp have shared_hit.
    This matches your --buffers_every sampling pattern.
    """
    sub = df[
        (df["ok"] == 1)
        & (df["condition"].isin(["live", "cbp"]))
        & (df["shared_hit"].notna())
    ].copy()

    piv = sub.pivot_table(
        index="iteration",
        columns="condition",
        values="shared_hit",
        aggfunc="first",
    )

    # must have both columns and non-null rows
    if "live" not in piv.columns or "cbp" not in piv.columns:
        return None, None

    piv = piv.dropna()
    if piv.empty:
        return None, None

    piv["buffer_ratio_live_over_cbp"] = piv["live"] / piv["cbp"]
    piv["buffer_reduction_percent"] = (1.0 - (piv["cbp"] / piv["live"])) * 100.0

    ratio_stats = summarize(piv["buffer_ratio_live_over_cbp"].values)
    ratio_stats["pairs"] = ratio_stats.pop("n")

    red_stats = summarize(piv["buffer_reduction_percent"].values)
    red_stats["pairs"] = red_stats.pop("n")

    return {"ratio": ratio_stats, "reduction_percent": red_stats}, piv


# ----------------------------
# Plotting
# ----------------------------
def plot_latency_timeseries(df: pd.DataFrame, out_path: Path):
    sub = df[(df["ok"] == 1) & (df["condition"].isin(["live", "cbp"]))].copy()
    if sub.empty:
        return
    sub = sub.sort_values("iteration")

    plt.figure(figsize=(10, 4))
    for cond in ["live", "cbp"]:
        s = sub[sub["condition"] == cond]
        plt.plot(s["iteration"], s["elapsed_ms"], marker="o", linewidth=1, markersize=3, label=cond)

    plt.xlabel("Iteration")
    plt.ylabel("Elapsed ms (end-to-end)")
    plt.title("Latency vs Iteration (Live vs CBP)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_latency_boxplot(df: pd.DataFrame, out_path: Path):
    sub = df[(df["ok"] == 1) & (df["condition"].isin(["live", "cbp"]))].copy()
    if sub.empty:
        return

    live = sub[sub["condition"] == "live"]["elapsed_ms"].dropna().values
    cbp = sub[sub["condition"] == "cbp"]["elapsed_ms"].dropna().values
    if len(live) == 0 or len(cbp) == 0:
        return

    plt.figure(figsize=(6, 4))
    plt.boxplot([live, cbp], tick_labels=["live", "cbp"], showfliers=True)
    plt.ylabel("Elapsed ms (end-to-end)")
    plt.title("Latency Distribution")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_speedup_timeseries(piv: pd.DataFrame, out_path: Path):
    if piv is None or piv.empty:
        return
    piv = piv.sort_index()

    plt.figure(figsize=(10, 4))
    plt.plot(piv.index, piv["speedup_live_over_cbp"], marker="o", linewidth=1, markersize=3)
    plt.axhline(1.0, linestyle="--", linewidth=1)
    plt.xlabel("Iteration")
    plt.ylabel("Speedup (live/cbp)")
    plt.title("Speedup vs Iteration")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_resources_timeseries(df: pd.DataFrame, out_path: Path):
    sub = df[(df["ok"] == 1) & (df["condition"].isin(["feed_cycle", "live", "cbp"]))].copy()
    if sub.empty:
        return

    sub = sub.sort_values("iteration")

    plt.figure(figsize=(10, 6))

    ax1 = plt.subplot(2, 1, 1)
    for cond in ["feed_cycle", "live", "cbp"]:
        s = sub[sub["condition"] == cond]
        if not s.empty:
            ax1.plot(s["iteration"], s["cpu_percent"], marker="o", linewidth=1, markersize=3, label=cond)
    ax1.set_xlabel("Iteration")
    ax1.set_ylabel("CPU % (docker stats)")
    ax1.set_title("CPU% over Iterations")
    ax1.legend()

    ax2 = plt.subplot(2, 1, 2)
    for cond in ["feed_cycle", "live", "cbp"]:
        s = sub[sub["condition"] == cond]
        if not s.empty:
            ax2.plot(s["iteration"], s["mem_percent"], marker="o", linewidth=1, markersize=3, label=cond)
    ax2.set_xlabel("Iteration")
    ax2.set_ylabel("Memory % (docker stats)")
    ax2.set_title("Memory% over Iterations")
    ax2.legend()

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_buffers_hits_timeseries(buf_piv: pd.DataFrame, out_path: Path):
    if buf_piv is None or buf_piv.empty:
        return
    buf_piv = buf_piv.sort_index()

    plt.figure(figsize=(10, 4))
    plt.plot(buf_piv.index, buf_piv["live"], marker="o", linewidth=1, markersize=3, label="live shared_hit")
    plt.plot(buf_piv.index, buf_piv["cbp"], marker="o", linewidth=1, markersize=3, label="cbp shared_hit")
    plt.xlabel("Iteration (buffer-sampled)")
    plt.ylabel("Total shared_hit (sum over plan)")
    plt.title("Shared Buffer Hits (EXPLAIN BUFFERS)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def plot_buffers_ratio_timeseries(buf_piv: pd.DataFrame, out_path: Path):
    if buf_piv is None or buf_piv.empty:
        return
    buf_piv = buf_piv.sort_index()

    plt.figure(figsize=(10, 4))
    plt.plot(buf_piv.index, buf_piv["buffer_ratio_live_over_cbp"], marker="o", linewidth=1, markersize=3)
    plt.axhline(1.0, linestyle="--", linewidth=1)
    plt.xlabel("Iteration (buffer-sampled)")
    plt.ylabel("Buffer ratio (live/cbp)")
    plt.title("Buffer Ratio vs Iteration")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


# ----------------------------
# Markdown summary writer
# ----------------------------
def write_summary(df: pd.DataFrame, lat_stats: dict, hash_stats: dict, spd_stats: dict,
                  buf_stats: dict, out_path: Path):
    lines = []
    lines.append("# Stats Summary\n")
    lines.append("Auto-generated by `08_analysis/analyze_results.py`.\n\n")

    lines.append("## Dataset\n")
    lines.append(f"- Input: `{DEFAULT_INPUT.as_posix()}`\n")
    lines.append(f"- Total rows: {len(df)}\n")
    lines.append(f"- ok=1 rows: {int((df['ok']==1).sum())}\n\n")

    lines.append("## Correctness (Live vs CBP)\n")
    lines.append(f"- Paired iterations: {hash_stats.get('pairs', 0)}\n")
    mr = hash_stats.get("match_rate", np.nan)
    if not np.isnan(mr):
        lines.append(f"- Hash match rate: **{mr*100:.2f}%**\n")
    else:
        lines.append("- Hash match rate: N/A\n")
    lines.append(f"- Mismatches: {hash_stats.get('mismatches', 0)}\n\n")

    lines.append("## Latency (ms)\n")
    for cond in ["feed_cycle", "live", "cbp"]:
        s = lat_stats.get(cond, {"n": 0})
        if s.get("n", 0) == 0:
            lines.append(f"- {cond}: no data\n")
        else:
            lines.append(
                f"- {cond}: n={s['n']}, mean={s['mean']:.2f}, median={s['median']:.2f}, "
                f"p95={s['p95']:.2f}, min={s['min']:.2f}, max={s['max']:.2f}, "
                f"std={s['std']:.2f}, cv={s['cv']:.3f}\n"
            )

    lines.append("\n## Speedup (live/cbp)\n")
    if spd_stats.get("pairs", 0) == 0:
        lines.append("- No paired latency samples\n")
    else:
        lines.append(
            f"- pairs={spd_stats['pairs']}, mean={spd_stats['mean']:.3f}, median={spd_stats['median']:.3f}, "
            f"p95={spd_stats['p95']:.3f}, min={spd_stats['min']:.3f}, max={spd_stats['max']:.3f}\n"
        )

    lines.append("\n## Buffers (shared_hit)\n")
    if buf_stats is None:
        lines.append("- No paired buffer samples (shared_hit missing for live/cbp)\n")
    else:
        r = buf_stats["ratio"]
        rp = buf_stats["reduction_percent"]
        lines.append(
            f"- paired={r['pairs']}\n"
            f"- ratio live/cbp: mean={r['mean']:.3f}, median={r['median']:.3f}, p95={r['p95']:.3f}, "
            f"min={r['min']:.3f}, max={r['max']:.3f}\n"
            f"- reduction % (1 - cbp/live): mean={rp['mean']:.2f}%, median={rp['median']:.2f}%, p95={rp['p95']:.2f}%\n"
        )

    out_path.write_text("".join(lines), encoding="utf-8")


# ----------------------------
# Main
# ----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=str, default=str(DEFAULT_INPUT), help="Path to combined_metrics.csv")
    ap.add_argument("--plots_dir", type=str, default=str(PLOTS_DIR), help="Directory for plots")
    args = ap.parse_args()

    df = load_data(Path(args.input))
    ok_df = df[df["ok"] == 1].copy()

    # Latency summaries by condition
    lat_stats = {}
    for cond in ["feed_cycle", "live", "cbp"]:
        lat_stats[cond] = summarize(ok_df[ok_df["condition"] == cond]["elapsed_ms"].dropna().values)

    # Correctness + speedup
    h = hash_equivalence(df)
    spd, spiv = speedup_stats(df)

    # Buffers
    buf_stats, buf_piv = buffer_ratio_stats(df)

    # Console output
    print("=== Latency summaries (ms) ===")
    for cond in ["feed_cycle", "live", "cbp"]:
        print(cond, lat_stats[cond])

    print("\n=== Correctness (hash) ===")
    print(h)

    print("\n=== Speedup (live/cbp) ===")
    print(spd)

    print("\n=== Buffers (live/cbp) ===")
    print(buf_stats)

    # Plots
    plots_dir = Path(args.plots_dir)
    ensure_dir(plots_dir)

    plot_latency_timeseries(df, plots_dir / "latency_timeseries.png")
    plot_latency_boxplot(df, plots_dir / "latency_boxplot.png")
    plot_speedup_timeseries(spiv, plots_dir / "speedup_timeseries.png")
    plot_resources_timeseries(df, plots_dir / "resources_timeseries.png")
    plot_buffers_hits_timeseries(buf_piv, plots_dir / "buffers_hits_timeseries.png")
    plot_buffers_ratio_timeseries(buf_piv, plots_dir / "buffers_ratio_timeseries.png")

    # Markdown summary
    write_summary(df, lat_stats, h, spd, buf_stats, SUMMARY_MD)

    print(f"\n✅ Saved plots to: {plots_dir}")
    print(f"✅ Wrote: {SUMMARY_MD}")


if __name__ == "__main__":
    main()