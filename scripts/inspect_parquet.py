import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.thermal_intelligence import thermal_intelligence

events = thermal_intelligence.events
sources = thermal_intelligence.sources

print(f"Events shape: {events.shape}")
print(f"Sources shape: {sources.shape}")
print(f"Total events: {len(events)}")
print(f"Total sources: {len(sources)}")
print("\nRegion value counts in events:")
print(events["_region_key"].value_counts())
print("\nTotal sum across all regions in events:", events["_region_key"].value_counts().sum())
