import pandas as pd

df = pd.read_parquet("data/processed/final_fused_events.parquet")
print("Columns in final_fused_events.parquet:")
print(df.columns.tolist())

for col in ["is_night", "daynight", "day_night", "time"]:
    if col in df.columns:
        print(f"{col} found! Value counts:\n", df[col].value_counts())
