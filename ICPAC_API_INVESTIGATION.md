# ICPAC Portals Data API Investigation

**Investigation Date:** April 7, 2026

## Executive Summary

This investigation examined four ICPAC (Intergovernmental Authority on Development Climate Prediction and Applications Centre) portals to understand their data APIs and available datasets. Two portals have well-documented REST APIs, while two are JavaScript-heavy frontend applications.

### Quick Reference

| Portal | Status | API Endpoint | Datasets |
|--------|--------|-------------|----------|
| **Droughtwatch** | ✅ Fully Accessible | `https://droughtwatch.icpac.net/api` | 35 datasets, 14 categories |
| **EA Hazards Watch** | ✅ Partially Accessible | `https://eahazardswatch.icpac.net/api` | 36 datasets, 9 categories |
| **Agriculture Hotspots** | ❌ Not Accessible | None found | Unknown |
| **Seasonal Forecast** | ❌ No API | Frontend only | Visualized in web portal |
| **Data Center** | ❌ No API | Frontend only | Index/reference only |

---

## 1. Drought Watch Portal ✅

**URL:** https://droughtwatch.icpac.net  
**API Base:** https://droughtwatch.icpac.net/api  
**Status:** ✅ **FULLY OPERATIONAL**

### Available Endpoints

- `GET /api/categories/` - List all data categories
- `GET /api/datasets/` - List all available datasets

### Data Catalog (35 datasets across 14 categories)

#### Drought Indicators (6 datasets)
- Current Drought Conditions (10-day CDI)
- 10-Day Drought Recovery Classes
- Monthly Combined Drought Indicator
- Monthly Drought Recovery Classes
- Hydrological Drought Conditions
- Seasonal Combined Drought Indicator

#### Precipitation (2 datasets)
- Standardized Precipitation Index (CHIRPS)
- Monthly Precipitation (CHIRPS)

#### Precipitation Forecasts (2 datasets) 🌧️
- **Monthly Probabilistic Precipitation Forecast**
- **Seasonal Probabilistic Precipitation Forecast**

#### Temperature Conditions (8 datasets)
- Heat Waves Duration
- Maximum Temperature Anomaly
- Maximum Temperature
- Cold Waves Duration
- Minimum Temperature
- Aridity Index Classification
- Temperature Waves Diurnal Cycle

#### Temperature Forecasts (2 datasets) 🌡️
- **Monthly Probabilistic Temperature Forecast**
- **Seasonal Probabilistic Temperature Forecast**

#### Vegetation (5 datasets)
- 10-Day Vegetation Anomaly
- Monthly Vegetation Anomaly
- Seasonal Vegetation Anomaly
- 10-Day Vegetation Condition
- Monthly Vegetation Condition
- Seasonal Vegetation Condition

#### Soil Moisture (3 datasets)
- 10-Day Soil Moisture Anomaly
- Monthly Soil Moisture Anomaly
- Seasonal Soil Moisture Anomaly

#### Additional Categories
- **Geographic Background:** Köppen Climate, Soil Type, Land Use, Thermal Regions
- **Thematic Layers:** Cropland Mask, Rangeland Mask, Population Projections

### Data Format & Access

**Format:** WMS tiles + REST JSON API  
**Temporal Resolution:** 
- 10-day (dekad)
- Monthly
- Seasonal

**Geographic Coverage:** East Africa with admin level filtering  
**Time Range:** 2000-2026 (available years vary by dataset)  
**Tile Parameters:** Year, Month, Dekad (10-day period: 1st, 2nd, or 3rd)

### Example WMS Request Structure
```
https://droughtwatch.icpac.net/mapcache/?LAYERS=dekadal_cdi_chirps_tileset&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&SRS=EPSG:900913&BBOX={bbox}&WIDTH=256&HEIGHT=256&SELECTED_YEAR={year}&SELECTED_DMONTH={month}&SELECTED_TENDAYS={dekad}
```

### Strengths
✅ Complete seasonal rainfall/temperature forecast probabilities  
✅ Comprehensive drought monitoring indicators  
✅ 10-day temporal resolution available  
✅ Multi-layered forecasts (monthly + seasonal)  
✅ Clean REST API for catalog discovery  
✅ Well-structured WMS for map tiles  
✅ Historical data back to 2000  

---

## 2. East Africa Hazards Watch Portal ✅

**URL:** https://eahazardswatch.icpac.net  
**API Base:** https://eahazardswatch.icpac.net/api  
**Status:** ✅ **ACCESSIBLE - LIMITED**

### Available Endpoints

- `GET /api/datasets` - List all datasets and layers

### Data Catalog (36 datasets across 9 categories)

#### Rainfall Hazards (Category 1) - 12 datasets 🌧️
- Exceptional Rainfall
- Total Rainfall Forecast
- Rainfall Anomalies
- Risk of Heatstress
- Mean Temperature
- Seasonal Rainfall Anomalies
- Extreme Wind Speed
- *and 5 more*

#### Agricultural/Forage Conditions (Category 4) - 3 datasets 🌾
- **Available Forage Forecast**
- **Crops Conditions**
- **Rangelands Conditions**

#### Disease/Outbreaks (Category 5) - 1 dataset 🦠
- Outbreak Probability

#### Drought Indicators (Category 7) - 1 dataset 🏜️
- Combined Drought Indicator

#### Cyclones/Extreme Weather (Category 10) - 1 dataset 🌀
- GHA Cyclone Tracks

#### Infrastructure & Thematic (Category 12) - 9 datasets 🏗️
- Crop Land Area Mask
- Range Land Area Mask
- GHA Airports
- Roads
- Dams
- GHSL Population Projections
- *and 3 more*

#### Temperature/Extremes (Category 18) - 1 dataset 🌡️
- Cities Temperature Evolution

#### Administrative Boundaries (Category 22) - 5 datasets 🗺️
- Admin Level 0 Boundary
- Admin Level 1 Boundary
- Admin Level 2 Boundary
- Hydroshed Level 3 Basins
- East Africa Protected Areas

#### Humanitarian/Displacement (Category 23) - 2 datasets 👥
- Disaster Induced Displacements
- Humanitarian Needs - Persons

### API Response Structure

```json
{
  "id": "dataset-uuid-or-slug",
  "name": "Human Readable Name",
  "dataset": "dataset-identifier",
  "category": 1,
  "layer": "layer-uuid",
  "layers": [
    {
      "id": "sublayer-uuid",
      "name": "Sublayer Name",
      "description": "..."
    }
  ],
  "published": true,
  "type": "dataset"
}
```

### Data Format & Access

**Format:** JSON API (no WMS/download endpoints exposed)  
**Coverage:** East Africa  
**Structure:** Hierarchical (datasets → layers → sublayers)  
**Time Coverage:** Current/recent (exact temporal range varies)

### Strengths
✅ Comprehensive hazard warning data (rainfall, cyclones, outbreaks)  
✅ **Agricultural impact data** (crops conditions, forage, rangelands)  
✅ **Disaster displacement tracking**  
✅ **Rainfall forecast data**  
✅ Multi-layered data structure  
✅ Well-organized categories  

### Limitations
⚠️ Category IDs are numeric (not descriptive names)  
⚠️ No obvious data download endpoints in basic API  
⚠️ Cannot access sub-layer details from datasets endpoint directly  

---

## 3. Agriculture Hotspots Portal ❌

**URL:** https://agriculturehotspots.icpac.net  
**Status:** ❌ **NOT DIRECTLY ACCESSIBLE**

### Findings

- JavaScript-heavy portal (large HTML payload: 73KB)
- No direct API endpoints discovered
- No standard REST endpoints (/api/, /datasets/, /categories/)
- Data appears to be visualized through frontend only

### Potential Data (Assumed)
- Agricultural impact analysis
- Crop condition monitoring  
- Pastoral status updates
- Land use classifications

### Recommendations
- **Inspect browser network requests** to find actual data endpoints
- May use embedded map tile services (WMS/XYZ)
- May have undocumented backend APIs
- Could require web scraping or reverse engineering

---

## 4. Seasonal Forecast Portal ❌

**URL:** https://www.icpac.net/seasonal-forecast/  
**Status:** ❌ **NO DIRECT API**

### Findings

- Very large HTML payload (1.4MB) - highly JavaScript-dependent
- Found reference to `/api/tracker/` endpoint in HTML
- `/api/tracker/` requires parameters and returns 400 without them
- No accessible seasonal forecast data via standard REST API

### Advantages
- Appears to include seasonal precipitation probabilities through visualization
- Likely sourced from Droughtwatch API internally

### Recommendations
✅ **Use Droughtwatch API instead** for seasonal forecast data  
The actual seasonal forecast datasets are available through:
- `Seasonal Probabilistic Precipitation Forecast` (Droughtwatch)
- `Seasonal Probabilistic Temperature Forecast` (Droughtwatch)

---

## 5. Data Center Portal ❌

**URL:** https://www.icpac.net/data-center/  
**Status:** ❌ **NO DIRECT API**

### Findings

- Appears to be an index/reference portal
- Large HTML payload (109KB)
- Same `/api/tracker/` reference as seasonal forecast
- No direct dataset access endpoints

### Purpose
- Likely serves as navigation hub to other ICPAC portals
- May provide documentation and links

---

## Recommendations & Integration Strategy

### 🎯 For Seasonal Forecast Data
**Primary Source:** Droughtwatch API  
**Endpoint:** https://droughtwatch.icpac.net/api/datasets/

**Relevant Datasets:**
- Monthly Probabilistic Precipitation Forecast
- Seasonal Probabilistic Precipitation Forecast
- Monthly Probabilistic Temperature Forecast
- Seasonal Probabilistic Temperature Forecast

**Advantages:**
- Complete seasonal probability data
- Multiple forecast scenarios
- Historical data back to 2000
- Well-documented WMS structure

---

### 🎯 For Hazard Warnings & Alerts
**Primary Source:** EA Hazards Watch API  
**Endpoint:** https://eahazardswatch.icpac.net/api/datasets/

**Relevant Datasets:**
- Exceptional Rainfall
- Total Rainfall Forecast
- GHA Cyclone Tracks
- Outbreak Probability
- Disaster Induced Displacements

**Advantages:**
- Real-time operational hazard monitoring
- Comprehensive hazard coverage
- Structured JSON API
- Displacement/humanitarian impact data

---

### 🎯 For Agricultural Impact Data
**Primary Sources:**

1. **EA Hazards Watch API** (RECOMMENDED)
   - Crops Conditions
   - Rangelands Conditions
   - Available Forage Forecast

2. **Droughtwatch API** (SUPPLEMENTARY)
   - Vegetation Condition & Anomaly
   - Soil Moisture Anomaly

3. **Agriculture Hotspots** (INVESTIGATE)
   - Status: Unknown - requires network inspection
   - Potential: Detailed agricultural impact analysis

---

## Implementation Checklist

- [ ] **Phase 1:** Droughtwatch Integration
  - [ ] Implement `/api/categories/` fetcher
  - [ ] Implement `/api/datasets/` fetcher
  - [ ] Create WMS tile request handler
  - [ ] Test date-parameterized queries

- [ ] **Phase 2:** EA Hazards Watch Integration
  - [ ] Implement `/api/datasets` fetcher
  - [ ] Parse hierarchical dataset structure
  - [ ] Map numeric categories to names
  - [ ] Test data access patterns

- [ ] **Phase 3:** Investigation
  - [ ] Inspect Agriculture Hotspots network requests
  - [ ] Test `/api/tracker/` with reverse-engineered parameters
  - [ ] Document any additional undocumented APIs

---

## API Access & Requirements

**Authentication:** None (publicly accessible)  
**Rate Limiting:** Not documented (use reasonable intervals)  
**CORS:** Need to verify (may require proxy for frontend)  
**Data Format:** JSON via REST API or WMS tiles

## Data Quality Notes

- **Temporal Lag:** Real-time to recent (varies by dataset)
- **Geographic Precision:** Admin level filtering available (0-2)
- **Historical Depth:** Droughtwatch has 2000-2026 history
- **Forecast Horizon:** Monthly and seasonal available
- **Update Frequency:** Varies by dataset (dekadal to seasonal)

---

## Files Generated

- `icpac_droughtwatch_snapshot.json` - Complete Droughtwatch catalog
- `ICPAC_API_INVESTIGATION.md` - This document

