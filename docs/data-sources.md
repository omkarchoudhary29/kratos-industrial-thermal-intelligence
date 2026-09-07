# KRATOS V3.1 — Data Sources & Attribution

KRATOS V3.1 synthesizes multi-source remote sensing, geospatial infrastructure, and environmental datasets to produce evidence-grounded intelligence.

## 1. Primary Data Providers

| Dataset | Provider | Spatial Resolution | Temporal Frequency | License / Terms |
|---|---|:---:|:---:|---|
| **VIIRS Active Fire (VNP14IMGTDL / VJ114IMGTDL)** | NASA LANCE FIRMS | 375m (I-Band) | Near-Real-Time (approx. 3-hour latency) | Open Data (NASA Earth Science Data Policy) |
| **Industrial Infrastructure Polygons** | OpenStreetMap (OSM) | Boundary Polygons | Updated Continually | Open Data Commons Open Database License (ODbL) |
| **Global Land Cover 2021** | ESA WorldCover Consortium | 10m | Static Baseline (2021) | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| **India High-Resolution Population Grid** | WorldPop (University of Southampton) | 1 km / 100m Constrained | Annual (2026 Projection) | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| **ERA5-Land Atmospheric Data** | ECMWF / Copernicus Climate Change Service | 0.1° (~9 km) | Hourly Reanalysis | Copernicus Open Access License |

## 2. Monitored Corridors & Landscapes

KRATOS maintains active monitoring across 10 strategic geographic regions in India:

### Industrial Corridors (6)
1. **Vijayanagar / Toranagallu Industrial Region (Karnataka):** Integrated steel manufacturing, power plants, and iron ore processing infrastructure.
2. **Talcher / Angul Industrial Corridor (Odisha):** Coal mining basins, thermal power generation, and aluminum smelting complexes.
3. **Dhanbad / Bokaro Industrial Corridor (Jharkhand):** Coking coal reserves, blast furnace steel complexes, and heavy industrial facilities.
4. **Singrauli / Sonbhadra Energy Corridor (MP / UP):** Pithead thermal power super-stations and open-cast coal mines.
5. **Korba Industrial Corridor (Chhattisgarh):** Thermal power generation, captive power units, and aluminum manufacturing.
6. **Jamnagar / Vadinar Refinery Corridor (Gujarat):** Complex mega-refineries, petrochemical cracking units, and marine tanker crude handling terminals.

### Forest Landscapes (4)
7. **Gadchiroli Forest Landscape (Maharashtra):** Tropical dry and moist deciduous forest frontiers.
8. **Kanha Forest Landscape (Madhya Pradesh):** Protected tiger corridor and moist sal forest biomes.
9. **Bastar Forest Landscape (Chhattisgarh):** Dense sal and teak forest canopy reserves.
10. **Mizoram Forest Landscape (Mizoram):** Hilly montane bamboo forests and jhum rotational agro-forestry frontiers.

## 3. Operational Ingestion vs. Historical Baseline

- **Historical Baseline Archive:** 8,891 fused thermal observations and 312 corroborated persistent thermal sources covering January 2021 through December 2025.
- **Near-Real-Time Ingestion:** Background scheduler (`pipeline/thermal/refresh.py`) polls NASA FIRMS Area API every 15 minutes for rolling 48-hour active fire observations.
