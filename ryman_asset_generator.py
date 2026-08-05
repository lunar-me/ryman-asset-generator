#!/usr/bin/env python3
"""
Ryman Asset Generator
=====================
Synthetic ServiceNow-style IT Asset Data Generator.

Generates realistic hardware asset records that mimic a ServiceNow
ITAM / CMDB export (alm_hardware / cmdb_ci_computer style).

Designed to support demos of:
  1. Full asset lifecycle (planning → purchase → use → disposal)
  2. Data anomaly detection
  3. Investigation of missing / unassigned / under-utilised / non-compliant assets
  4. Cost-saving, waste reduction, budgeting & forecasting analysis
  5. Reporting and decision-support insights

No real organisation data is used.

Usage:
    python ryman-asset-generator.py
    python ryman-asset-generator.py --rows 20000 --output my_assets.csv
    python ryman-asset-generator.py --rows 5000 --seed 123

Requirements:
    pip install -r requirements.txt
"""

import argparse
import os
import random
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker


# ---------------------------------------------------------------------------
# Configuration – edit these lists to customise
# ---------------------------------------------------------------------------

LOCATIONS = [
    # New Zealand
    "Christchurch Head Office",
    "Ryman Christchurch Village",
    "Ryman Auckland Village",
    "Ryman Wellington Village",
    "Ryman Hamilton Village",
    "Ryman Tauranga Village",
    "Ryman Dunedin Village",
    "Ryman Nelson Village",
    "Ryman Palmerston North Village",
    "Ryman New Plymouth Village",
    "Ryman Rotorua Village",
    "Ryman Whangarei Village",
    "Ryman Invercargill Village",
    "Ryman Napier Village",
    "Ryman Hastings Village",
    "Ryman Queenstown Village",
    "Ryman Blenheim Village",
    "Ryman Timaru Village",
    "Ryman Gisborne Village",
    "Ryman Masterton Village",
    "Ryman Whanganui Village",
    "Ryman Kapiti Village",
    "Ryman Hutt Valley Village",
    "Ryman North Shore Village",
    "Ryman Manukau Village",
    # Australia
    "Ryman Melbourne Village",
    "Ryman Sydney Village",
    "Ryman Brisbane Village",
    "Ryman Adelaide Village",
    "Ryman Perth Village",
    "Ryman Canberra Village",
    "Ryman Gold Coast Village",
    "Ryman Newcastle Village",
    "Ryman Geelong Village",
    "Ryman Hobart Village",
    "Ryman Townsville Village",
    "Ryman Cairns Village",
    "Ryman Wollongong Village",
    "Ryman Sunshine Coast Village",
    "Ryman Ballarat Village",
    "Ryman Bendigo Village",
    "Ryman Toowoomba Village",
    "Ryman Launceston Village",
    "Ryman Darwin Village",
    "Ryman Alice Springs Village",
    "Ryman Albury Village",
    "Ryman Wagga Wagga Village",
    "Ryman Mildura Village",
    "Ryman Bundaberg Village",
]

ASSET_CATALOG = {
    "Laptop": [
        ("Dell", "Latitude 5440"),
        ("Dell", "Latitude 5540"),
        ("Dell", "Latitude 7440"),
        ("HP", "EliteBook 840 G10"),
        ("HP", "EliteBook 860 G10"),
        ("HP", "ProBook 450 G10"),
        ("Lenovo", "ThinkPad T14 Gen 4"),
        ("Lenovo", "ThinkPad X1 Carbon Gen 11"),
        ("Lenovo", "ThinkPad L14 Gen 4"),
        ("Microsoft", "Surface Laptop 5"),
        ("Microsoft", "Surface Laptop Studio"),
        ("Apple", "MacBook Pro 14"),
        ("Apple", "MacBook Air M2"),
        ("Apple", "MacBook Pro 16"),
    ],
    "Tablet": [
        ("Apple", "iPad Pro 12.9"),
        ("Apple", "iPad Air 5th Gen"),
        ("Apple", "iPad 10th Gen"),
        ("Microsoft", "Surface Pro 9"),
        ("Microsoft", "Surface Go 3"),
        ("Samsung", "Galaxy Tab S9"),
        ("Samsung", "Galaxy Tab A8"),
        ("Samsung", "Galaxy Tab S8"),
    ],
    "Mobile Phone": [
        ("Apple", "iPhone 15"),
        ("Apple", "iPhone 15 Pro"),
        ("Apple", "iPhone 14"),
        ("Apple", "iPhone 13"),
        ("Samsung", "Galaxy S24"),
        ("Samsung", "Galaxy S23"),
        ("Samsung", "Galaxy A54"),
        ("Google", "Pixel 8"),
        ("Google", "Pixel 7a"),
        ("Google", "Pixel 8 Pro"),
    ],
    "Monitor": [
        ("Dell", "UltraSharp U2723QE"),
        ("Dell", "P2422H"),
        ("HP", "E27u G5"),
        ("HP", "P27h G5"),
        ("LG", "27UK850"),
        ("LG", "27UP850"),
        ("Samsung", "Odyssey G5"),
        ("Samsung", "ViewFinity S6"),
    ],
    "Accessory": [
        ("Dell", "WD19TB Dock"),
        ("HP", "Thunderbolt Dock 120W"),
        ("Logitech", "MX Master 3S"),
        ("Logitech", "MX Keys"),
        ("Apple", "Magic Keyboard"),
        ("Apple", "Magic Mouse"),
        ("Jabra", "Evolve2 65"),
        ("Poly", "Voyager 4320"),
        ("Poly", "Sync 20"),
    ],
}

ASSET_TYPE_WEIGHTS = {
    "Laptop": 0.45,
    "Mobile Phone": 0.25,
    "Tablet": 0.15,
    "Monitor": 0.08,
    "Accessory": 0.07,
}

# Typical useful life (years) used for refresh planning
USEFUL_LIFE_YEARS = {
    "Laptop": 4,
    "Tablet": 3,
    "Mobile Phone": 3,
    "Monitor": 5,
    "Accessory": 4,
}

INSTALL_STATUSES = [
    "Installed",
    "In Stock",
    "In Transit",
    "Pending Install",
    "Retired",
    "Missing",
    "In Repair",
]
STATUS_WEIGHTS = [0.68, 0.09, 0.03, 0.04, 0.07, 0.05, 0.04]

# Full lifecycle stages (planning → disposal)
LIFECYCLE_STAGES = [
    "Requested",
    "Ordered",
    "Received",
    "Deployed",
    "In Use",
    "Refresh Due",
    "Retired",
    "Disposed",
]

STATE_MAP = {
    "Installed": "In Use",
    "In Stock": "Available",
    "In Transit": "In Transit",
    "Pending Install": "Reserved",
    "Retired": "Retired",
    "Missing": "Lost",
    "In Repair": "In Repair",
}

DEPARTMENTS = [
    "Clinical",
    "Administration",
    "Facilities",
    "Technology",
    "Finance",
    "Procurement",
    "Village Management",
    "Care Services",
    "Kitchen",
    "Maintenance",
    "Reception",
    "HR",
]

DISPOSAL_METHODS = [
    "Secure wipe + resale",
    "Secure wipe + recycle",
    "Manufacturer return",
    "Certified destruction",
    "Donation",
    "Parts harvest",
]

NOTES_OPTIONS = [
    "Pending audit verification",
    "Reported missing by village manager",
    "Awaiting return from staff member",
    "Warranty claim in progress",
    "Scheduled for refresh",
    "Loan device",
    "Spare stock",
    "Damaged - under investigation",
    "Transferred between villages",
    "Non-compliant - encryption not enabled",
    "OS version no longer supported",
]


def _choose_lifecycle_stage(status: str, age_years: float, useful_life: float) -> str:
    """Map install_status + age to a realistic lifecycle stage."""
    if status == "Missing":
        return random.choice(["In Use", "Refresh Due", "Retired"])
    if status == "Retired":
        return random.choice(["Retired", "Disposed"])
    if status == "In Transit":
        return random.choice(["Ordered", "Received"])
    if status == "Pending Install":
        return random.choice(["Received", "Deployed"])
    if status == "In Stock":
        return random.choice(["Received", "Deployed"])
    if status == "In Repair":
        return "In Use"
    # Installed
    if age_years >= useful_life + 0.5:
        return random.choice(["Refresh Due", "Retired"])
    if age_years >= useful_life - 0.5:
        return random.choice(["In Use", "Refresh Due"])
    return "In Use"


def generate_assets(n_rows: int = 15000, seed: int = 42) -> pd.DataFrame:
    """Generate a DataFrame of synthetic ServiceNow-style asset records."""
    fake = Faker(["en_NZ", "en_AU"])
    Faker.seed(seed)
    np.random.seed(seed)
    random.seed(seed)

    now = datetime.now()
    records = []
    asset_types = list(ASSET_TYPE_WEIGHTS.keys())
    type_weights = list(ASSET_TYPE_WEIGHTS.values())

    for i in range(n_rows):
        asset_type = random.choices(asset_types, weights=type_weights)[0]
        manufacturer, model = random.choice(ASSET_CATALOG[asset_type])
        useful_life = USEFUL_LIFE_YEARS[asset_type]

        # --- Purchase date (bias toward more recent) ---
        days_ago = int(np.random.exponential(scale=550))
        days_ago = min(max(days_ago, 20), 2500)
        purchase_date = now - timedelta(days=days_ago)
        age_years = (now - purchase_date).days / 365.25

        # --- Cost (NZD) ---
        if asset_type == "Laptop":
            cost = round(random.uniform(1100, 3800), 2)
        elif asset_type == "Tablet":
            cost = round(random.uniform(380, 1900), 2)
        elif asset_type == "Mobile Phone":
            cost = round(random.uniform(450, 2300), 2)
        elif asset_type == "Monitor":
            cost = round(random.uniform(220, 950), 2)
        else:
            cost = round(random.uniform(40, 480), 2)

        # --- Warranty ---
        warranty_years = random.choices([1, 2, 3], weights=[0.25, 0.50, 0.25])[0]
        warranty_end = purchase_date + timedelta(
            days=365 * warranty_years + random.randint(-20, 40)
        )
        warranty_status = "Active" if warranty_end > now else "Expired"

        # --- Install status & state ---
        status = random.choices(INSTALL_STATUSES, weights=STATUS_WEIGHTS)[0]
        state = STATE_MAP.get(status, "In Use")

        # --- Lifecycle stage ---
        lifecycle_stage = _choose_lifecycle_stage(status, age_years, useful_life)

        # --- Assignment ---
        if status in ("Installed", "In Repair", "Pending Install") and lifecycle_stage not in (
            "Retired",
            "Disposed",
        ):
            assigned_to = fake.name()
            department = random.choice(DEPARTMENTS)
        else:
            assigned_to = fake.name() if random.random() < 0.10 else ""
            department = (
                random.choice(["Technology", "Procurement", ""])
                if random.random() > 0.45
                else ""
            )

        location = random.choice(LOCATIONS)

        # --- Last discovered / utilisation ---
        if status == "Installed" and lifecycle_stage == "In Use":
            last_seen_days = min(int(np.random.exponential(scale=10)), 90)
        elif status == "Missing":
            last_seen_days = random.randint(45, 950)
        elif status in ("Retired",) or lifecycle_stage == "Disposed":
            last_seen_days = random.randint(30, 700)
        elif lifecycle_stage == "Refresh Due":
            last_seen_days = min(int(np.random.exponential(scale=25)), 180)
        else:
            last_seen_days = random.randint(2, 60)

        last_discovered = now - timedelta(days=last_seen_days)
        days_since_last_seen = (now - last_discovered).days

        # Simple utilisation score 0–100 (higher = more recently seen / active)
        if status == "Missing" or assigned_to == "":
            utilisation_score = random.randint(0, 15)
        elif days_since_last_seen <= 7:
            utilisation_score = random.randint(85, 100)
        elif days_since_last_seen <= 30:
            utilisation_score = random.randint(55, 84)
        elif days_since_last_seen <= 90:
            utilisation_score = random.randint(25, 54)
        else:
            utilisation_score = random.randint(0, 24)

        # --- Refresh planning ---
        planned_refresh = purchase_date + timedelta(days=int(useful_life * 365.25))
        # Add small variance
        planned_refresh += timedelta(days=random.randint(-60, 90))
        refresh_year = planned_refresh.year
        remaining_life_years = round(max(0, (planned_refresh - now).days / 365.25), 2)

        # --- Disposal fields (only for end-of-life assets) ---
        disposal_date = ""
        disposal_method = ""
        residual_value = ""
        if lifecycle_stage in ("Retired", "Disposed") or status == "Retired":
            # Disposal happens after retirement
            dispose_days_after = random.randint(10, 180)
            disp = purchase_date + timedelta(days=int(age_years * 365) + dispose_days_after)
            if disp > now:
                disp = now - timedelta(days=random.randint(5, 120))
            disposal_date = disp.strftime("%Y-%m-%d")
            disposal_method = random.choice(DISPOSAL_METHODS)
            # Rough residual value declining with age
            residual_pct = max(0.02, 0.35 - (age_years * 0.07))
            residual_value = round(cost * residual_pct * random.uniform(0.7, 1.1), 2)

        # --- Compliance flags ---
        # Encryption more likely on newer / corporate devices
        if asset_type in ("Laptop", "Tablet", "Mobile Phone"):
            encryption_status = random.choices(
                ["Enabled", "Disabled", "Unknown"],
                weights=[0.78, 0.12, 0.10],
            )[0]
        else:
            encryption_status = "N/A"

        # OS support – older devices more likely unsupported
        if asset_type in ("Laptop", "Tablet", "Mobile Phone"):
            if age_years > useful_life:
                os_supported = random.choices(
                    ["Supported", "Unsupported", "Unknown"], weights=[0.25, 0.60, 0.15]
                )[0]
            else:
                os_supported = random.choices(
                    ["Supported", "Unsupported", "Unknown"], weights=[0.82, 0.08, 0.10]
                )[0]
        else:
            os_supported = "N/A"

        # Overall compliance helper
        is_non_compliant = (
            encryption_status == "Disabled"
            or os_supported == "Unsupported"
            or (status == "Installed" and assigned_to == "")
        )

        # --- Serial & identifiers ---
        serial = fake.bothify(
            text="??########", letters="ABCDEFGHJKLMNPQRSTUVWXYZ"
        )
        asset_tag = f"RYM-{asset_type[:3].upper()}-{100000 + i}"
        sys_id = uuid.uuid4().hex
        po_number = (
            f"PO-{random.randint(20230000, 20269999)}"
            if random.random() > 0.10
            else ""
        )

        notes = ""
        if is_non_compliant and random.random() < 0.4:
            notes = random.choice(
                [
                    "Non-compliant - encryption not enabled",
                    "OS version no longer supported",
                    "Unassigned device - ownership unclear",
                ]
            )
        elif random.random() < 0.06:
            notes = random.choice(NOTES_OPTIONS)

        # ------------------------------------------------------------------
        # Deliberate data-quality / anomaly injection (~10%)
        # ------------------------------------------------------------------
        if random.random() < 0.035:
            assigned_to = ""  # unassigned
        if random.random() < 0.022:
            location = ""  # missing location
        if random.random() < 0.018:
            serial = ""  # missing serial

        # Occasional date / cost anomalies
        if random.random() < 0.012:
            # Future purchase date (impossible)
            purchase_date = now + timedelta(days=random.randint(10, 120))
        if random.random() < 0.010:
            # Warranty ends before purchase
            warranty_end = purchase_date - timedelta(days=random.randint(30, 200))
            warranty_status = "Invalid"
        if random.random() < 0.008:
            # Extreme cost outlier
            cost = round(cost * random.uniform(4.5, 9.0), 2)

        records.append(
            {
                # Core identifiers
                "sys_id": sys_id,
                "asset_tag": asset_tag,
                "serial_number": serial,
                "ci_name": f"{manufacturer} {model}",
                "model": model,
                "manufacturer": manufacturer,
                "asset_type": asset_type,
                "category": "Hardware",
                "subcategory": asset_type,
                # Status & lifecycle
                "install_status": status,
                "state": state,
                "lifecycle_stage": lifecycle_stage,
                # Assignment & location
                "assigned_to": assigned_to,
                "location": location,
                "department": department,
                # Procurement & cost
                "purchase_date": purchase_date.strftime("%Y-%m-%d"),
                "purchase_cost_nzd": cost,
                "po_number": po_number,
                "cost_center": f"CC-{random.randint(1000, 1999)}",
                # Warranty & compliance
                "warranty_expiration": warranty_end.strftime("%Y-%m-%d"),
                "warranty_status": warranty_status,
                "encryption_status": encryption_status,
                "os_supported": os_supported,
                "is_non_compliant": is_non_compliant,
                # Utilisation
                "last_discovered": last_discovered.strftime("%Y-%m-%d %H:%M:%S"),
                "days_since_last_seen": days_since_last_seen,
                "utilisation_score": utilisation_score,
                # Refresh / forecasting
                "useful_life_years": useful_life,
                "planned_refresh_date": planned_refresh.strftime("%Y-%m-%d"),
                "refresh_year": refresh_year,
                "remaining_life_years": remaining_life_years,
                # Disposal
                "disposal_date": disposal_date,
                "disposal_method": disposal_method,
                "residual_value_nzd": residual_value,
                # Ownership
                "owned_by": "Ryman Healthcare",
                "company": "Ryman Healthcare Limited",
                "notes": notes,
            }
        )

    df = pd.DataFrame(records)

    # Inject duplicate serials (data quality issue)
    n_dups = max(25, n_rows // 350)
    for _ in range(n_dups):
        idx1, idx2 = random.sample(range(len(df)), 2)
        if df.at[idx1, "serial_number"] and df.at[idx2, "serial_number"]:
            df.at[idx2, "serial_number"] = df.at[idx1, "serial_number"]

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic ServiceNow-style IT asset data (CSV) "
        "supporting full lifecycle, anomaly detection, utilisation, "
        "compliance, cost analysis and forecasting."
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=15000,
        help="Number of asset records to generate (default: 15000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="ryman_assets.csv",
        help="Output CSV filename (default: ryman_assets.csv)",
    )
    args = parser.parse_args()

    print(f"Generating {args.rows:,} synthetic asset records (seed={args.seed})...")
    df = generate_assets(n_rows=args.rows, seed=args.seed)

    df.to_csv(args.output, index=False)
    size_mb = os.path.getsize(args.output) / (1024 * 1024)

    print(f"\nSaved to: {args.output}")
    print(f"Rows     : {len(df):,}")
    print(f"Columns  : {len(df.columns)}")
    print(f"File size: {size_mb:.2f} MB")

    print("\n--- Key distributions ---")
    print("\ninstall_status:")
    print(df["install_status"].value_counts().to_string())
    print("\nlifecycle_stage:")
    print(df["lifecycle_stage"].value_counts().to_string())
    print("\nasset_type:")
    print(df["asset_type"].value_counts().to_string())

    print("\n--- Data-quality / investigation flags ---")
    print(f"  Blank assigned_to     : {(df['assigned_to'] == '').sum():,}")
    print(f"  Blank location        : {(df['location'] == '').sum():,}")
    print(f"  Blank serial_number   : {(df['serial_number'] == '').sum():,}")
    print(f"  Duplicate serials     : {df['serial_number'].duplicated().sum():,}")
    print(f"  Missing status        : {(df['install_status'] == 'Missing').sum():,}")
    print(f"  Non-compliant assets  : {df['is_non_compliant'].sum():,}")
    print(f"  Low utilisation (<30) : {(df['utilisation_score'] < 30).sum():,}")
    print(f"  Refresh Due           : {(df['lifecycle_stage'] == 'Refresh Due').sum():,}")
    print(f"  Disposed / Retired    : {df['lifecycle_stage'].isin(['Retired', 'Disposed']).sum():,}")

    print("\nDone. Dataset supports lifecycle, anomaly, utilisation, compliance,")
    print("cost-saving and forecasting analysis for Asset Management demos.")


if __name__ == "__main__":
    main()
