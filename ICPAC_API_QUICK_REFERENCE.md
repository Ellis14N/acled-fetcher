# ICPAC API Quick Reference

## TL;DR - What Works

✅ **Use these two APIs:**

1. **Droughtwatch API** - Seasonal forecasts & drought monitoring
   ```
   https://droughtwatch.icpac.net/api/categories/
   https://droughtwatch.icpac.net/api/datasets/
   ```

2. **EA Hazards Watch API** - Hazards, agricultural data & alerts
   ```
   https://eahazardswatch.icpac.net/api/datasets
   ```

❌ **Don't try these:**
- Agriculture Hotspots Portal - No API found
- Seasonal Forecast portal - Use Droughtwatch instead
- Data Center - Just a reference hub

---

## Droughtwatch API Details

### Get Available Data
```bash
curl https://droughtwatch.icpac.net/api/datasets/
```

### What You Get (35 datasets)

**Seasonal Forecasts (PRECIPITATION):**
- Monthly Probabilistic Precipitation Forecast
- Seasonal Probabilistic Precipitation Forecast

**Seasonal Forecasts (TEMPERATURE):**
- Monthly Probabilistic Temperature Forecast  
- Seasonal Probabilistic Temperature Forecast

**Drought Monitoring:**
- Current Drought Conditions (10-day CDI)
- Monthly Combined Drought Indicator
- Seasonal Combined Drought Indicator
- Soil Moisture Anomaly (dekadal, monthly, seasonal)
- Vegetation Condition/Anomaly (dekadal, monthly, seasonal)

**Plus:** Rainfall, temperature, vegetation, hydrological data

### Data Format
- **Type:** WMS tiles + JSON API
- **Temporal:** 10-day (dekad), monthly, seasonal
- **Years:** 2000-2026 (varies by dataset)
- **Grid:** Admin levels 0-2 (countries, regions, districts)

### Example WMS Request
```
https://droughtwatch.icpac.net/mapcache/?
  LAYERS=dekadal_cdi_chirps_tileset
  &SERVICE=WMS&VERSION=1.1.1
  &SELECTED_YEAR=2026
  &SELECTED_DMONTH=03
  &SELECTED_TENDAYS=01
  &BBOX={bbox}&WIDTH=256&HEIGHT=256
```

---

## EA Hazards Watch API Details

### Get Available Data
```bash
curl https://eahazardswatch.icpac.net/api/datasets
```

### What You Get (36 datasets)

**Rainfall & Forecasts:**
- Exceptional Rainfall
- Total Rainfall Forecast  
- Rainfall Anomalies

**Agricultural Data:**
- Crops Conditions
- Rangelands Conditions
- Available Forage Forecast

**Hazards:**
- GHA Cyclone Tracks
- Outbreak Probability
- Combined Drought Indicator

**Humanitarian:**
- Disaster Induced Displacements
- Humanitarian Needs - Persons

**Infrastructure & Boundaries:**
- Admin boundaries (levels 0-2)
- Crop/Range land masks
- Dams, Roads, Airports
- Protected Areas

### Data Format
- **Type:** JSON API only
- **Structure:** Datasets → Layers → Sublayers
- **Categories:** Numeric IDs (1, 4, 5, 7, 10, 12, 18, 22, 23)

### Example Response
```json
{
  "id": "f4f32f26-d98b-46a4-9851-c1afb5b48362",
  "name": "Available Forage Forecast",
  "dataset": "f4f32f26-d98b-46a4-9851-c1afb5b48362",
  "category": 4,
  "layer": "d904b6ce-62e4-4765-b08c-8ab4d552b412",
  "layers": [
    {
      "id": "layer-uuid",
      "name": "Sublayer Name"
    }
  ]
}
```

---

## Category Mapping (EA Hazards Watch)

| ID | Type | Count | Examples |
|----|------|-------|----------|
| 1 | Rainfall Hazards | 12 | Exceptional Rainfall, Forecasts |
| 4 | Agriculture | 3 | Crops, Rangelands, Forage |
| 5 | Health | 1 | Outbreak Probability |
| 7 | Drought | 1 | CDI |
| 10 | Cyclones | 1 | Cyclone Tracks |
| 12 | Infrastructure | 9 | Roads, Dams, Population |
| 18 | Temperature | 1 | Temperature Evolution |
| 22 | Boundaries | 5 | Admin levels, Protected Areas |
| 23 | Humanitarian | 2 | Displacements, Needs |

---

## Integration Steps

### Step 1: Droughtwatch Catalog
```python
# Get all available datasets
GET /api/datasets/

# Parse the response for:
response.json()
# Each dataset has:
# - id: UUID
# - name: Human readable
# - slug: Machine readable ID
# - category: Category slug
# - layers: Array of actual data layers with WMS/date params
```

### Step 2: EA Hazards Watch Catalog
```python
# Get all available datasets
GET /api/datasets

# Parse the response for:
response.json()
# Each dataset has:
# - id: UUID or slug
# - name: Human readable
# - category: Numeric category ID
# - layers: Sub-layers (may need separate calls)
```

### Step 3: Access Data
**For Droughtwatch:**
- Use WMS tiles with date parameters (year/month/dekad)
- Or query GetFeatureInfo for pixel values

**For EA Hazards Watch:**
- Follow layer links
- Query sub-layers for actual data
- May need to reverse-engineer data access

---

## Known Limitations

### Droughtwatch
- WMS tiles require separate authentication/origin headers
- Historical forecasts not shown (only latest)
- Data updates on specific cadence (dekadal)

### EA Hazards Watch
- No download/export endpoints visible
- Sub-layer data access method unclear
- Category names in Chinese/numeric codes only
- Need to map categories internally

### Not Available
- Real-time minute-level data
- Individual weather station data
- Satellite raw imagery

---

## Testing Quick Checks

```bash
# Test Droughtwatch
curl https://droughtwatch.icpac.net/api/datasets/ | jq '.[] | .name' | head -5

# Test EA Hazards Watch  
curl https://eahazardswatch.icpac.net/api/datasets | jq '.[] | .name' | head -5

# Count datasets
curl https://droughtwatch.icpac.net/api/datasets/ | jq 'length'
curl https://eahazardswatch.icpac.net/api/datasets | jq 'length'
```

---

## Next Steps

1. **Priority 1:** Build Droughtwatch integration (35 datasets available)
2. **Priority 2:** Build EA Hazards integration (36 datasets, agriculture data)
3. **Priority 3:** Reverse-engineer Agriculture Hotspots (inspect network tab)
4. **Priority 4:** Test WMS data access with actual geographic queries

---

## References

- Full investigation: `ICPAC_API_INVESTIGATION.md`
- Droughtwatch snapshot: `data/icpac_droughtwatch_snapshot.json`
- Existing fetcher script: `_scripts/fetch_icpac_droughtwatch_snapshot.py`

