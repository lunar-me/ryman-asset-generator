# Ryman Asset Generator

**Synthetic ServiceNow-style IT Asset Data Generator**

Generate realistic hardware asset records that look like a ServiceNow ITAM / CMDB export. Built for demos, portfolio projects, testing, and learning around IT Asset Management.

No real organisation data is used or required.

---

## Why this exists

IT Asset Management Analysts work with large volumes of laptop, tablet, phone and accessory data. Real production extracts are sensitive. This generator creates high-quality synthetic data so you can safely practise and demonstrate:

1. **Full asset lifecycle** – planning → purchase → deployment → use → refresh → disposal  
2. **Data anomaly detection** – missing values, duplicates, impossible dates, cost outliers  
3. **Investigation of problem assets** – missing, unassigned, under-utilised and non-compliant devices  
4. **Cost, waste and forecasting analysis** – spend, residual value, refresh planning, idle-asset cost  
5. **Reporting and decision support** – clean dimensions and measures ready for Power BI, Excel or Python

---

## Quick start

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/ryman-asset-generator.git
cd ryman-asset-generator

# Install dependencies
pip install -r requirements.txt

# Generate the default dataset (15,000 rows)
python ryman-asset-generator.py
```

Output file: `ryman_assets.csv`

### Common options

```bash
# Larger dataset
python ryman-asset-generator.py --rows 25000

# Reproducible run with a fixed seed
python ryman-asset-generator.py --rows 10000 --seed 123

# Custom output name
python ryman-asset-generator.py --rows 5000 --output demo_assets.csv
```

| Flag | Default | Description |
|------|---------|-------------|
| `--rows` | 15000 | Number of asset records to generate |
| `--seed` | 42 | Random seed for reproducibility |
| `--output` | `ryman_assets.csv` | Output CSV filename |

---

## What the data looks like

Each row represents one technology asset with fields commonly found in ServiceNow Hardware Asset Management / CMDB exports.

> **Full column reference:** See [ryman_assets_metadata.md](ryman_assets_metadata.md) for a complete table of all 37 columns, data types, descriptions, and the deliberate data-quality anomalies built into the dataset.

### Core identifiers
`sys_id`, `asset_tag`, `serial_number`, `ci_name`, `model`, `manufacturer`, `asset_type`

### Status & lifecycle
`install_status`, `state`, `lifecycle_stage`  
(Lifecycle stages: Requested → Ordered → Received → Deployed → In Use → Refresh Due → Retired → Disposed)

### Assignment & location
`assigned_to`, `location`, `department`  
(~49 New Zealand and Australian village / office locations)

### Procurement & cost
`purchase_date`, `purchase_cost_nzd`, `po_number`, `cost_center`

### Warranty & compliance
`warranty_expiration`, `warranty_status`, `encryption_status`, `os_supported`, `is_non_compliant`

### Utilisation
`last_discovered`, `days_since_last_seen`, `utilisation_score` (0–100)

### Refresh & forecasting
`useful_life_years`, `planned_refresh_date`, `refresh_year`, `remaining_life_years`

### Disposal
`disposal_date`, `disposal_method`, `residual_value_nzd`

---

## Built-in data quality issues

The generator deliberately injects realistic problems so you can practise cleaning and investigation:

- Blank `assigned_to`, `location` and `serial_number`
- Duplicate serial numbers
- Future purchase dates
- Warranty end dates before purchase date
- Extreme cost outliers
- Missing / unassigned / low-utilisation / non-compliant devices

These make the dataset useful for anomaly detection, audit simulation and process-improvement demos.

---

## Example analysis ideas

Once you have the CSV you can:

- Build a Power BI or Excel dashboard showing asset health by village
- Flag all Missing + unassigned + low-utilisation devices and estimate reclaim value
- Forecast refresh volume and cost by year
- Measure non-compliance rate (encryption / unsupported OS)
- Calculate potential savings from reclaiming idle assets
- Train a simple anomaly-detection model (Isolation Forest, etc.)

---

## Upload to Supabase

After generating the CSV you can push it to a Supabase project using the official Python client.

> **Note:** The Supabase Python client cannot run DDL (`DROP` / `CREATE TABLE`).  
> Create the table **once** in the SQL Editor (the upload script will print the exact SQL if the table is missing).  
> On every run the script then clears all rows and re-loads the CSV.

### 1. Set environment variables

```bash
# Required – from Supabase Dashboard → Project Settings → API
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Optional
export SUPABASE_TABLE="ryman_assets"   # default table name
export CSV_PATH="ryman_assets.csv"     # default CSV path
```

You can also put these in a `.env` file (python-dotenv is supported).

### 2. Create the table (one-time)

Run the SQL that the script prints, or paste the definition from `upload_to_supabase.py` into the Supabase SQL Editor.

### 3. Run the upload

```bash
python upload_to_supabase.py
```

The script will:
1. Read the CSV
2. Clear all existing rows in the target table
3. Bulk-insert the data in batches
4. Print a row-count confirmation

---

## Requirements

- Python 3.8+
- pandas, numpy, faker
- supabase, python-dotenv (for Supabase upload)

Install with:

```bash
pip install -r requirements.txt
```

---

## Project structure

```
ryman-asset-generator/
├── ryman-asset-generator.py   # Generate synthetic asset CSV
├── upload_to_supabase.py      # Upload CSV to Supabase (re-creates table)
├── ryman_assets_metadata.md   # Full column reference & data-quality notes
├── requirements.txt
├── README.md
├── LICENSE
├── .env
└── .gitignore
```

---

## Customisation

All key lists live at the top of `ryman-asset-generator.py`:

- `LOCATIONS` – village / office names
- `ASSET_CATALOG` – manufacturer + model pairs
- `USEFUL_LIFE_YEARS` – expected life by asset type
- Status and lifecycle weights

Edit these to match a different organisation or scenario.

---

## Model output
*ryman_asset_generator.py*
```bash
Generating 15,000 synthetic asset records (seed=42)...

Saved to: servicenow_asset_data_simulation.csv
Rows     : 15,000
Columns  : 37
File size: 5.40 MB

--- Key distributions ---

install_status:
Installed          10326
In Stock            1331
Retired              999
Missing              713
In Repair            639
Pending Install      533
In Transit           459

lifecycle_stage:
In Use         10173
Received        1130
Retired         1082
Deployed         963
Refresh Due      918
Disposed         504
Ordered          230

asset_type:
Laptop          6790
Mobile Phone    3699
Tablet          2267
Monitor         1194
Accessory       1050

--- Data-quality / investigation flags ---
  Blank assigned_to     : 3,887
  Blank location        : 313
  Blank serial_number   : 250
  Duplicate serials     : 290
  Missing status        : 713
  Non-compliant assets  : 3,130
  Low utilisation (<30) : 3,879
  Refresh Due           : 918
  Disposed / Retired    : 1,586

Done. Dataset supports lifecycle, anomaly, utilisation, compliance,
cost-saving and forecasting analysis for Asset Management demos.
```

upload_to_supabase.py

```bash
Reading CSV: ryman_assets.csv
Rows to upload : 15,000
Target table   : ryman_assets
Connecting to Supabase ...
Clearing existing rows in 'ryman_assets' ...
  Table cleared.
Bulk inserting data ...
  Inserted 500 / 15,000 rows (3%)
  Inserted 1,000 / 15,000 rows (7%)
  Inserted 1,500 / 15,000 rows (10%)
  Inserted 2,000 / 15,000 rows (13%)
  Inserted 2,500 / 15,000 rows (17%)
  Inserted 3,000 / 15,000 rows (20%)
  Inserted 3,500 / 15,000 rows (23%)
  Inserted 4,000 / 15,000 rows (27%)
  Inserted 4,500 / 15,000 rows (30%)
  Inserted 5,000 / 15,000 rows (33%)
  Inserted 5,500 / 15,000 rows (37%)
  Inserted 6,000 / 15,000 rows (40%)
  Inserted 6,500 / 15,000 rows (43%)
  Inserted 7,000 / 15,000 rows (47%)
  Inserted 7,500 / 15,000 rows (50%)
  Inserted 8,000 / 15,000 rows (53%)
  Inserted 8,500 / 15,000 rows (57%)
  Inserted 9,000 / 15,000 rows (60%)
  Inserted 9,500 / 15,000 rows (63%)
  Inserted 10,000 / 15,000 rows (67%)
  Inserted 10,500 / 15,000 rows (70%)
  Inserted 11,000 / 15,000 rows (73%)
  Inserted 11,500 / 15,000 rows (77%)
  Inserted 12,000 / 15,000 rows (80%)
  Inserted 12,500 / 15,000 rows (83%)
  Inserted 13,000 / 15,000 rows (87%)
  Inserted 13,500 / 15,000 rows (90%)
  Inserted 14,000 / 15,000 rows (93%)
  Inserted 14,500 / 15,000 rows (97%)
  Inserted 15,000 / 15,000 rows (100%)

Upload complete.
  Table  : ryman_assets
  Rows   : 15,000

You can now query it in the Supabase Table Editor or via the API.
```

---

## Licence

MIT Licence – see [LICENSE](LICENSE).

Free to use, modify and share for personal, educational and commercial projects.

---

## Disclaimer

This project generates **completely synthetic data**.  
It is not affiliated with, endorsed by, or connected to Ryman Healthcare (or any other organisation).  
Location and naming conventions are fictionalised for realism only.
(c) 2026 lunar-me. All rights reserved.
