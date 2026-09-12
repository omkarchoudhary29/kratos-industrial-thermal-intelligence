import pandas as pd
from pathlib import Path

events_path = Path("data/processed/final_fused_events.parquet")
sources_path = Path("data/processed/thermal_sources.parquet")

df_events = pd.read_parquet(events_path)
df_sources = pd.read_parquet(sources_path)

print("Region counts in events (8891 total):")
print(df_events["region_name"].value_counts())
print("\nSum of events region counts:", df_events["region_name"].value_counts().sum())

print("\nRegion counts in sources (312 total):")
if "region_name" in df_sources.columns:
    print(df_sources["region_name"].value_counts())
    print("Sum of sources region counts:", df_sources["region_name"].value_counts().sum())
elif "_region_key" in df_sources.columns:
    print(df_sources["_region_key"].value_counts())
    print("Sum of sources region counts:", df_sources["_region_key"].value_counts().sum())
