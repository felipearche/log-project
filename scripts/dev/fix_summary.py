import pandas as pd

df = pd.read_csv("experiments/summary.csv")

# Remove the single stale synthetic row (2025-08-23) that has blank TPR
mask_stale = (
    (df["date"] == "2025-08-23")
    & (df["dataset"] == "synth_tokens")
    & (df["TPR_at_1pct_FPR"].isna())
)
df = df.loc[~mask_stale].copy()

# Make the TPR column "object" so mixing numbers and 'NA' is ok (no warning)
df["TPR_at_1pct_FPR"] = df["TPR_at_1pct_FPR"].astype(object)

# For mini_tokens, TPR should be the literal 'NA' (never blank)
mini = df["dataset"] == "mini_tokens"
df.loc[mini, "TPR_at_1pct_FPR"] = df.loc[mini, "TPR_at_1pct_FPR"].where(
    df.loc[mini, "TPR_at_1pct_FPR"].notna(), "NA"
)

# Safety: any other blank TPR -> 'NA'
df["TPR_at_1pct_FPR"] = df["TPR_at_1pct_FPR"].where(df["TPR_at_1pct_FPR"].notna(), "NA")

# Write back with LF endings, no index
df.to_csv("experiments/summary.csv", index=False, lineterminator="\n")
