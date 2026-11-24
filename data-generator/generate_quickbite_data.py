#!/usr/bin/env python3
"""
Deterministic Synthetic Dataset Generator for the QuickBite Snowflake -> GCP Migration Demo.
Uses 100% Python Standard Library (zero external dependencies) for instant execution.

Generates 12 tables (~610k rows total) into data-generator/output/:
  - 4 Apache Iceberg tables (CSV.gz -> loaded into Snowflake GCS Iceberg tables)
  - 7 Relational Native FDN tables (CSV.gz -> loaded into Snowflake Native tables)
  - 1 Semi-structured JSON table (JSONL.gz -> loaded into Snowflake VARIANT table)
  - ground_truth_manifest.json (exact row counts & cent-accurate KPI benchmarks)
"""

from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import math
import random
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SEED = 42
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def d2(val: float | Decimal) -> Decimal:
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_all() -> dict:
    rng = random.Random(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    row_counts: dict[str, int] = {}

    # ==========================================================================
    # 1. OPS_RAW.SYS_CAL_DIM (2024-01-01 to 2026-12-31 -> 1,096 rows)
    #    Fiscal year starts Feb 1 (e.g., 2025-01-15 -> FISC_YR_N = 2024, Q4)
    # ==========================================================================
    start_dt = dt.date(2024, 1, 1)
    end_dt = dt.date(2026, 12, 31)
    cal_map: dict[dt.date, tuple[int, int, int]] = {}

    with gzip.open(OUTPUT_DIR / "sys_cal_dim.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["DT_SK", "CAL_DT", "ISO_WK_N", "FISC_YR_N", "FISC_QTR_N", "IS_PEAK_HOLIDAY"])
        cur = start_dt
        cnt = 0
        peak_mmdd = {(1, 1), (2, 14), (7, 4), (10, 31), (11, 28), (12, 24), (12, 31)}
        while cur <= end_dt:
            dt_sk = int(cur.strftime("%Y%m%d"))
            iso_wk = cur.isocalendar()[1]
            if cur.month >= 2:
                fisc_yr = cur.year
                fisc_m = cur.month - 1  # Feb=1 .. Dec=11
            else:
                fisc_yr = cur.year - 1
                fisc_m = 12  # Jan=12
            fisc_qtr = (fisc_m - 1) // 3 + 1
            is_hol = 1 if (cur.month, cur.day) in peak_mmdd else 0
            w.writerow([dt_sk, cur.isoformat(), iso_wk, fisc_yr, fisc_qtr, is_hol])
            cal_map[cur] = (dt_sk, fisc_yr, fisc_qtr)
            cur += dt.timedelta(days=1)
            cnt += 1
    row_counts["OPS_RAW.SYS_CAL_DIM"] = cnt

    # ==========================================================================
    # 2. OPS_RAW.GEO_ZONE_LKP (36 delivery zones across AMER, EMEA, APAC)
    # ==========================================================================
    cities = [
        ("NYC", "New York", "US", "AMER", 32),
        ("SFO", "San Francisco", "US", "AMER", 30),
        ("CHI", "Chicago", "US", "AMER", 34),
        ("TOR", "Toronto", "CA", "AMER", 33),
        ("LON", "London", "GB", "EMEA", 30),
        ("PAR", "Paris", "FR", "EMEA", 29),
        ("BER", "Berlin", "DE", "EMEA", 31),
        ("MAD", "Madrid", "ES", "EMEA", 30),
        ("TYO", "Tokyo", "JP", "APAC", 26),
        ("SGP", "Singapore", "SG", "APAC", 28),
        ("SYD", "Sydney", "AU", "APAC", 34),
        ("SEL", "Seoul", "KR", "APAC", 27),
    ]
    sub_zones = [("01", "Downtown", 0), ("02", "Midtown", 2), ("03", "Metro East", 4)]
    zones: list[dict] = []
    with gzip.open(OUTPUT_DIR / "geo_zone_lkp.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ZONE_ID", "CITY_NM", "CNTRY_CD", "REG_CD", "SLA_TARGET_MIN"])
        for code, city_nm, cntry, reg, base_sla in cities:
            for sz_idx, sz_nm, sla_add in sub_zones:
                zid = f"ZNE-{code}-{sz_idx}"
                sla = base_sla + sla_add
                zones.append({
                    "zone_id": zid,
                    "city_nm": f"{city_nm} - {sz_nm}",
                    "cntry_cd": cntry,
                    "reg_cd": reg,
                    "sla_min": sla,
                })
                w.writerow([zid, f"{city_nm} - {sz_nm}", cntry, reg, sla])
    row_counts["OPS_RAW.GEO_ZONE_LKP"] = len(zones)
    zone_by_id = {z["zone_id"]: z for z in zones}

    # ==========================================================================
    # 3. OPS_RAW.MRC_PARTNER_MSTR (400 merchants: 300 Restaurants, 100 Grocery)
    # ==========================================================================
    rest_prefixes = ["Urban", "Golden", "Crispy", "Sakura", "Bella", "Spice", "Green", "Smoky", "Nomad", "Bistro"]
    rest_nouns = ["Burger", "Sushi", "Pizzeria", "Taco", "Ramen", "Kitchen", "Bowl", "Grill", "Noodle", "Tandoor"]
    cuisines = ["Burgers", "Japanese", "Pizza", "Mexican", "Asian Fusion", "Mediterranean", "Healthy Bowls", "Indian"]
    groc_names = ["QuickMart", "FreshDash", "PantryNow", "MetroMarket", "DailyBasket"]

    merchants: list[dict] = []
    with gzip.open(OUTPUT_DIR / "mrc_partner_mstr.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["MRC_ID", "MRC_NM", "VERT_CD", "CUISINE_CAT", "ZONE_ID", "ONBOARD_DT", "ACTIVE_FLG"])
        for i in range(1, 401):
            mrc_id = f"MRC-{i:04d}"
            z = zones[(i - 1) % len(zones)]
            vert_cd = 1 if i <= 300 else 2
            if vert_cd == 1:
                nm = f"{rest_prefixes[i % len(rest_prefixes)]} {rest_nouns[(i // 3) % len(rest_nouns)]} #{i}"
                cat = cuisines[i % len(cuisines)]
            else:
                nm = f"{groc_names[i % len(groc_names)]} Express #{i}"
                cat = "Grocery & Convenience"
            onboard = dt.date(2023, rng.randint(1, 12), rng.randint(1, 28))
            # Profile flags for deterministic Prime vs Slow-Prep trap
            if i <= 55:
                profile = "PRIME_CANDIDATE"  # Fast prep (<12m), high volume, low defect/reject
            elif i <= 80:
                profile = "HIGH_VOL_SLOW_TRAP"  # High volume, but slow prep (~22m) & higher missing items
            else:
                profile = "STANDARD"
            merchants.append({
                "mrc_id": mrc_id,
                "mrc_nm": nm,
                "vert_cd": vert_cd,
                "cat": cat,
                "zone_id": z["zone_id"],
                "reg_cd": z["reg_cd"],
                "profile": profile,
            })
            w.writerow([mrc_id, nm, vert_cd, cat, z["zone_id"], onboard.isoformat(), 1])
    row_counts["OPS_RAW.MRC_PARTNER_MSTR"] = len(merchants)
    mrc_by_id = {m["mrc_id"]: m for m in merchants}

    # ==========================================================================
    # 4. OPS_RAW.MRC_COMM_SCD2 (Trap #1: Q3 2025 Summer Relief Cut 15% vs 26%)
    # ==========================================================================
    scd_lookup: dict[str, list[tuple[dt.date, dt.date, Decimal, Decimal, int]]] = defaultdict(list)
    scd_cnt = 0
    with gzip.open(OUTPUT_DIR / "mrc_comm_scd2.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["MRC_ID", "EFF_FROM_DT", "EFF_TO_DT", "COMM_RATE_PCT", "PKG_FEE_USD", "IS_CURR_FLG"])
        for m in merchants:
            mid = m["mrc_id"]
            if m["vert_cd"] == 1:
                base_comm = d2(rng.uniform(0.24, 0.27))
                q3_comm = Decimal("0.15")  # Dramatic Q3 2025 summer relief promo!
                curr_comm = d2(base_comm + Decimal("0.02"))
                pkg = Decimal("0.75")
                rows = [
                    (dt.date(2024, 1, 1), dt.date(2025, 6, 30), base_comm, pkg, 0),
                    (dt.date(2025, 7, 1), dt.date(2025, 9, 30), q3_comm, pkg, 0),
                    (dt.date(2025, 10, 1), dt.date(9999, 12, 31), curr_comm, Decimal("0.90"), 1),
                ]
            else:
                base_comm = d2(rng.uniform(0.16, 0.19))
                curr_comm = d2(base_comm + Decimal("0.01"))
                pkg = Decimal("1.10")
                rows = [
                    (dt.date(2024, 1, 1), dt.date(2025, 8, 31), base_comm, pkg, 0),
                    (dt.date(2025, 9, 1), dt.date(9999, 12, 31), curr_comm, Decimal("1.25"), 1),
                ]
            for r in rows:
                scd_lookup[mid].append(r)
                w.writerow([mid, r[0].isoformat(), r[1].isoformat(), f"{r[2]:.4f}", f"{r[3]:.2f}", r[4]])
                scd_cnt += 1
    row_counts["OPS_RAW.MRC_COMM_SCD2"] = scd_cnt

    # ==========================================================================
    # 5. OPS_RAW.CUST_USER_MSTR (30,000 users, PII + ~45 planted fraud abusers)
    # ==========================================================================
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Emma", "Liam", "Olivia", "Noah",
                   "Sophia", "Lucas", "Mia", "Ethan", "Chloe", "Mason", "Ava", "Logan", "Zoe", "Leo"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
                  "Martinez", "Chen", "Patel", "Kim", " Dubois", "Mueller", "Silva", "Tanaka", "Walker", "Hall"]
    users: list[dict] = []
    abuser_ids: set[str] = set()
    with gzip.open(OUTPUT_DIR / "cust_user_mstr.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["USR_ID", "F_NM", "L_NM", "EMAIL_TXT", "PHONE_TXT", "SIGNUP_DT", "HOME_ZONE_ID", "QB_PASS_FLG"])
        for i in range(1, 30001):
            uid = f"USR-{i:06d}"
            fn = first_names[i % len(first_names)]
            ln = last_names[(i // 7) % len(last_names)].strip()
            email = f"{fn.lower()}.{ln.lower()}{i}@example-mail.com"
            phone = f"+1-555-{rng.randint(200, 999):03d}-{rng.randint(1000, 9999):04d}"
            s_dt = dt.date(2023, 1, 1) + dt.timedelta(days=rng.randint(0, 800))
            z = zones[i % len(zones)]
            qb_pass = 1 if (i <= 45 or rng.random() < 0.38) else 0
            is_abuser = i <= 45
            if is_abuser:
                abuser_ids.add(uid)
            users.append({"usr_id": uid, "zone_id": z["zone_id"], "qb_pass": qb_pass, "is_abuser": is_abuser})
            w.writerow([uid, fn, ln, email, phone, s_dt.isoformat(), z["zone_id"], qb_pass])
    row_counts["OPS_RAW.CUST_USER_MSTR"] = len(users)

    # ==========================================================================
    # 6. OPS_RAW.CRR_COURIER_MSTR (2,500 couriers)
    # ==========================================================================
    couriers_by_zone: dict[str, list[str]] = defaultdict(list)
    veh_types = ["EBK", "EBK", "SCT", "CAR"]
    with gzip.open(OUTPUT_DIR / "crr_courier_mstr.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["CRR_ID", "CRR_FULL_NM", "PHONE_TXT", "VEH_TP_CD", "HOME_ZONE_ID", "ACTIVE_FLG"])
        for i in range(1, 2501):
            cid = f"CRR-{i:05d}"
            nm = f"{first_names[(i * 3) % len(first_names)]} {last_names[(i * 5) % len(last_names)].strip()}"
            phone = f"+1-555-{rng.randint(200, 999):03d}-{rng.randint(1000, 9999):04d}"
            veh = veh_types[i % len(veh_types)]
            z = zones[i % len(zones)]["zone_id"]
            couriers_by_zone[z].append(cid)
            w.writerow([cid, nm, phone, veh, z, 1])
    row_counts["OPS_RAW.CRR_COURIER_MSTR"] = 2500

    # ==========================================================================
    # 7, 8, 9, 10, 12: ORDERS + ITEMS + DISPUTES + PAYOUT LEDGER + JSON PINGS
    #    Spanning 2024-04-01 to 2026-03-31 (90,000 orders)
    # ==========================================================================
    rest_items = [
        ("SKU-R01", "Double Smash Burger", Decimal("14.50")),
        ("SKU-R02", "Truffle Fries", Decimal("6.50")),
        ("SKU-R03", "Spicy Tuna Roll", Decimal("16.00")),
        ("SKU-R04", "Margherita Woodfired Pizza", Decimal("18.00")),
        ("SKU-R05", "Chicken Pad Thai", Decimal("15.50")),
        ("SKU-R06", "Harvest Quinoa Bowl", Decimal("13.75")),
    ]
    groc_items = [
        ("SKU-G01", "Organic Oat Milk 1L", Decimal("4.50")),
        ("SKU-G02", "Artisan Sourdough Loaf", Decimal("6.25")),
        ("SKU-G03", "Hass Avocados 4pk", Decimal("5.99")),
        ("SKU-G04", "Cold Brew Coffee Bottle", Decimal("4.25")),
        ("SKU-G05", "Free-Range Eggs 12ct", Decimal("5.50")),
    ]

    ticket_templates = {
        1: [
            "Missing the side fries and drink from my sealed bag.",
            "Ordered two bowls and only one arrived in the delivery.",
            "Half of the grocery items were missing when the rider dropped off.",
        ],
        2: [
            "Pizza arrived stone cold and the box was completely crushed.",
            "Soup container leaked all over the bag, food was ruined.",
            "Burger was cold and soggy after sitting on the counter.",
        ],
        3: [
            "Courier took over 65 minutes and drove in the opposite direction.",
            "Order arrived 40 minutes past the promised ETA window.",
            "Way too late, waited over an hour for a 15-minute grocery order.",
        ],
        4: [
            "Everything was inedible and missing again please refund full order immediately.",
            "Bag never showed up at my door, requesting instant full credit again.",
        ],
    }

    weighted_merchants: list[dict] = []
    for m in merchants:
        if m["profile"] in ("PRIME_CANDIDATE", "HIGH_VOL_SLOW_TRAP"):
            weighted_merchants.extend([m] * 4)
        else:
            weighted_merchants.append(m)

    ord_start = dt.date(2024, 4, 1)
    ord_days = (dt.date(2026, 3, 31) - ord_start).days + 1

    # Ground-truth accumulators
    gt_q3_2025_rest_net_rev = Decimal("0.00")
    gt_q3_2025_rest_naive_curr_comm_rev = Decimal("0.00")
    gt_fy2025_net_rev_by_vert = {1: Decimal("0.00"), 2: Decimal("0.00")}
    gt_true_approved_refunds = Decimal("0.00")
    gt_fanout_refunds_if_joined_to_lines = Decimal("0.00")
    gt_beta_bug_pings = 0

    ord_ln_cnt = 0
    dsp_cnt = 0
    ping_cnt = 0
    ledger_cnt = 0
    weekly_mrc_payout: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0.00"))

    f_hdr = gzip.open(OUTPUT_DIR / "dlv_ord_hdr.csv.gz", "wt", newline="", encoding="utf-8")
    f_ln = gzip.open(OUTPUT_DIR / "dlv_ord_item_ln.csv.gz", "wt", newline="", encoding="utf-8")
    f_dsp = gzip.open(OUTPUT_DIR / "dsp_refund_fct.csv.gz", "wt", newline="", encoding="utf-8")
    f_led = gzip.open(OUTPUT_DIR / "mrc_payout_ledger.csv.gz", "wt", newline="", encoding="utf-8")
    f_png = gzip.open(OUTPUT_DIR / "app_delivery_pings.jsonl.gz", "wt", encoding="utf-8")

    w_hdr = csv.writer(f_hdr)
    w_ln = csv.writer(f_ln)
    w_dsp = csv.writer(f_dsp)
    w_led = csv.writer(f_led)

    w_hdr.writerow([
        "ORD_ID", "ORD_DT_SK", "ORD_TS", "USR_ID", "MRC_ID", "CRR_ID", "ZONE_ID",
        "VERT_CD", "ORD_STS_CD", "DLV_FEE_USD", "SRV_FEE_USD", "TIP_USD", "CRR_PAY_USD", "PROMO_VOUCHER_USD"
    ])
    w_ln.writerow(["ORD_LN_ID", "ORD_ID", "ITEM_SKU", "ITEM_NM", "QTY_N", "UNIT_PRC_USD"])
    w_dsp.writerow(["DSP_ID", "ORD_ID", "DSP_TS", "RFND_AMT_USD", "RFND_STS_FLG", "DSP_RSN_CD", "CUST_TICKET_TXT"])
    w_led.writerow(["LEDGER_ID", "REF_DOC_TXT", "MRC_ID", "ISSUE_DT", "PAID_DT", "LEDGER_AMT_USD", "PYT_STS_FLG"])

    for i in range(1, 90001):
        oid = f"ORD-{i:07d}"
        # Reserve ~1,350 orders for the 45 planted refund abusers (~30 orders each across zones)
        if i <= 1350:
            u = users[(i - 1) % 45]
            m = weighted_merchants[rng.randint(0, len(weighted_merchants) - 1)]
        else:
            m = weighted_merchants[rng.randint(0, len(weighted_merchants) - 1)]
            u = users[45 + rng.randint(0, len(users) - 46)]

        # Slight upward growth trend toward 2025-2026
        day_offset = int(ord_days * math.sqrt(rng.random()))
        if day_offset >= ord_days:
            day_offset = ord_days - 1
        o_date = ord_start + dt.timedelta(days=day_offset)
        dt_sk, fisc_yr, _ = cal_map[o_date]

        hour = rng.choices([11, 12, 13, 18, 19, 20, 21, 15, 9], weights=[12, 18, 14, 16, 22, 18, 10, 5, 5])[0]
        o_ts = dt.datetime(o_date.year, o_date.month, o_date.day, hour, rng.randint(0, 59), rng.randint(0, 59))

        zid = m["zone_id"]
        crr_id = rng.choice(couriers_by_zone[zid])
        vert_cd = m["vert_cd"]

        # Status code based on merchant profile
        r_sts = rng.random()
        if m["profile"] == "PRIME_CANDIDATE":
            ord_sts = "D" if r_sts < 0.965 else ("C" if r_sts < 0.995 else "R")
        elif m["profile"] == "HIGH_VOL_SLOW_TRAP":
            ord_sts = "D" if r_sts < 0.89 else ("C" if r_sts < 0.96 else "R")
        else:
            ord_sts = "D" if r_sts < 0.90 else ("C" if r_sts < 0.96 else ("R" if r_sts < 0.99 else "P"))

        # Generate 1 to 4 basket line items
        n_items = rng.randint(2, 4) if vert_cd == 1 else rng.randint(2, 5)
        catalog = rest_items if vert_cd == 1 else groc_items
        chosen_items = rng.sample(catalog, k=min(n_items, len(catalog)))
        gmv = Decimal("0.00")
        for idx_ln, (sku, inm, uprc) in enumerate(chosen_items, start=1):
            qty = rng.randint(1, 3)
            ord_ln_cnt += 1
            w_ln.writerow([f"LN-{ord_ln_cnt:08d}", oid, sku, inm, qty, f"{uprc:.2f}"])
            gmv += uprc * qty

        dlv_fee = Decimal("0.00") if u["qb_pass"] == 1 else Decimal("3.99")
        srv_fee = d2(gmv * Decimal("0.08"))
        tip_usd = d2(rng.choice([0, 2, 3, 4, 5, 6])) if ord_sts == "D" else Decimal("0.00")
        crr_pay = Decimal("5.25") if ord_sts == "D" else Decimal("0.00")
        promo_v = Decimal("5.00") if (ord_sts == "D" and rng.random() < 0.12) else Decimal("0.00")

        w_hdr.writerow([
            oid, dt_sk, o_ts.strftime("%Y-%m-%d %H:%M:%S"),
            u["usr_id"], m["mrc_id"], crr_id, zid, vert_cd, ord_sts,
            f"{dlv_fee:.2f}", f"{srv_fee:.2f}", f"{tip_usd:.2f}", f"{crr_pay:.2f}", f"{promo_v:.2f}"
        ])

        # Lookup historical SCD2 commission vs current commission
        hist_comm = Decimal("0.25")
        curr_comm = Decimal("0.25")
        for eff_f, eff_t, c_pct, _, is_c in scd_lookup[m["mrc_id"]]:
            if eff_f <= o_date <= eff_t:
                hist_comm = c_pct
            if is_c == 1:
                curr_comm = c_pct

        # Telemetry JSON pings + Disputes for Delivered orders
        approved_rfnd_this_ord = Decimal("0.00")
        if ord_sts == "D":
            if m["profile"] == "PRIME_CANDIDATE":
                prep_sec = rng.randint(420, 760)  # ~7 to 12.6 min (< 14m Prime rule!)
                travel_sec = rng.randint(480, 900)
            elif m["profile"] == "HIGH_VOL_SLOW_TRAP":
                prep_sec = rng.randint(1150, 1620)  # ~19 to 27 min (fails < 14m Prime rule!)
                travel_sec = rng.randint(600, 1150)
            else:
                prep_sec = rng.randint(600, 1250)
                travel_sec = rng.randint(540, 1100)

            sla_sec = zone_by_id[zid]["sla_min"] * 60
            quoted_eta = prep_sec + travel_sec + rng.randint(-120, 120)

            # Inject 3.8.0-beta GPS timer bug on ~3% of Jan-Feb 2026 orders
            is_beta_bug = (o_date >= dt.date(2026, 1, 5) and o_date <= dt.date(2026, 2, 15) and rng.random() < 0.22)
            app_ver = "3.8.0-beta" if is_beta_bug else rng.choice(["3.7.4", "3.8.1", "3.9.0"])
            reported_prep_sec = 5400 if is_beta_bug else prep_sec
            if is_beta_bug:
                gt_beta_bug_pings += 1

            # Emit PICKED_UP ping (subset) + DELIVERED ping
            if rng.random() < 0.72:
                ping_cnt += 1
                p1_ts = o_ts + dt.timedelta(seconds=prep_sec)
                f_png.write(json.dumps({
                    "PING_ID": f"PNG-{ping_cnt:08d}",
                    "INGEST_TS": p1_ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "ORD_ID": oid,
                    "PAYLOAD": {
                        "stage": "PICKED_UP",
                        "app_ver": app_ver,
                        "metrics": {"prep_sec": reported_prep_sec, "travel_sec": 0, "eta_sec": quoted_eta},
                        "anomaly_flags": ["GPS_TIMER_OVERFLOW"] if is_beta_bug else [],
                    }
                }) + "\n")

            ping_cnt += 1
            drop_ts = o_ts + dt.timedelta(seconds=prep_sec + travel_sec)
            flags = []
            if is_beta_bug:
                flags.append("GPS_TIMER_OVERFLOW")
            if (prep_sec + travel_sec) > sla_sec:
                flags.append("SLA_EXCEEDED")
            f_png.write(json.dumps({
                "PING_ID": f"PNG-{ping_cnt:08d}",
                "INGEST_TS": drop_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "ORD_ID": oid,
                "PAYLOAD": {
                    "stage": "DELIVERED",
                    "app_ver": app_ver,
                    "metrics": {
                        "prep_sec": reported_prep_sec,
                        "travel_sec": travel_sec,
                        "eta_sec": quoted_eta,
                    },
                    "anomaly_flags": flags,
                }
            }) + "\n")

            # Disputes & Refunds
            trigger_dispute = False
            if u["is_abuser"] and rng.random() < 0.68:
                trigger_dispute = True
                rsn_cd = 4 if rng.random() < 0.55 else 1
                rfnd_sts = 9 if rng.random() < 0.60 else 1  # 9 = Rejected Fraud, 1 = Approved before caught
            elif m["profile"] == "PRIME_CANDIDATE" and rng.random() < 0.011:
                trigger_dispute = True
                rsn_cd = rng.choice([1, 2, 3])
                rfnd_sts = 1
            elif m["profile"] == "HIGH_VOL_SLOW_TRAP" and rng.random() < 0.14:
                trigger_dispute = True
                rsn_cd = rng.choice([1, 2, 2, 3])
                rfnd_sts = 1
            elif m["profile"] == "STANDARD" and rng.random() < 0.085:
                trigger_dispute = True
                rsn_cd = rng.choice([1, 2, 3])
                rfnd_sts = 1 if rng.random() < 0.88 else 0

            if trigger_dispute:
                dsp_cnt += 1
                dsp_ts = drop_ts + dt.timedelta(minutes=rng.randint(8, 90))
                rfnd_amt = d2(gmv * Decimal(str(rng.choice([0.35, 0.50, 1.00]))))
                txt = rng.choice(ticket_templates[rsn_cd])
                w_dsp.writerow([
                    f"DSP-{dsp_cnt:07d}", oid, dsp_ts.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{rfnd_amt:.2f}", rfnd_sts, rsn_cd, txt
                ])
                if rfnd_sts == 1:
                    approved_rfnd_this_ord += rfnd_amt
                    gt_true_approved_refunds += rfnd_amt
                    gt_fanout_refunds_if_joined_to_lines += rfnd_amt * len(chosen_items)

                    # Merchant-fault quality dispute (RSN_CD in 1, 2) triggers 'CBK-' || ORD_ID chargeback!
                    if rsn_cd in (1, 2):
                        ledger_cnt += 1
                        cbk_amt = d2(-rfnd_amt * Decimal("0.80"))
                        paid_dt_str = (o_date + dt.timedelta(days=7)).isoformat()
                        w_led.writerow([
                            f"LED-{ledger_cnt:07d}", f"CBK-{oid}", m["mrc_id"],
                            o_date.isoformat(), paid_dt_str, f"{cbk_amt:.2f}", 1
                        ])

            # Accumulate merchant weekly payout
            iso_yr, iso_wk, _ = o_date.isocalendar()
            mrc_net = d2(gmv * (Decimal("1.00") - hist_comm))
            weekly_mrc_payout[(m["mrc_id"], f"{iso_yr}W{iso_wk:02d}")] += mrc_net

            # Accumulate Ground-Truth Platform Net Revenue (Net Take)
            # Formula: (GMV * SCD2_Comm) + DLV_FEE + SRV_FEE - CRR_PAY - PROMO_VOUCHER - Approved_Refunds
            ord_net_take = d2(gmv * hist_comm) + dlv_fee + srv_fee - crr_pay - promo_v - approved_rfnd_this_ord
            ord_naive_take = d2(gmv * curr_comm) + dlv_fee + srv_fee - crr_pay - promo_v - approved_rfnd_this_ord

            if fisc_yr == 2025:
                gt_fy2025_net_rev_by_vert[vert_cd] += ord_net_take
            if dt.date(2025, 7, 1) <= o_date <= dt.date(2025, 9, 30) and vert_cd == 1:
                gt_q3_2025_rest_net_rev += ord_net_take
                gt_q3_2025_rest_naive_curr_comm_rev += ord_naive_take

    # Flush weekly STL- merchant settlements into MRC_PAYOUT_LEDGER
    for (mid, yw_str), amt in sorted(weekly_mrc_payout.items()):
        if rng.random() < 0.35:  # Keep ledger compact (~16k total rows)
            ledger_cnt += 1
            yr_i, wk_i = int(yw_str[:4]), int(yw_str[5:])
            iss_dt = dt.date.fromisocalendar(yr_i, min(wk_i, 52), 1)
            if iss_dt >= dt.date(2026, 3, 15):
                pyt_sts = 0
                paid_str = ""
            else:
                pyt_sts = 1
                paid_str = (iss_dt + dt.timedelta(days=4)).isoformat()
            w_led.writerow([
                f"LED-{ledger_cnt:07d}", f"STL-{mid}-{yw_str}", mid,
                iss_dt.isoformat(), paid_str, f"{d2(amt):.2f}", pyt_sts
            ])

    f_hdr.close()
    f_ln.close()
    f_dsp.close()
    f_led.close()
    f_png.close()

    row_counts["OPS_RAW.DLV_ORD_HDR"] = 90000
    row_counts["OPS_RAW.DLV_ORD_ITEM_LN"] = ord_ln_cnt
    row_counts["OPS_RAW.DSP_REFUND_FCT"] = dsp_cnt
    row_counts["OPS_RAW.MRC_PAYOUT_LEDGER"] = ledger_cnt
    row_counts["IOT_RAW.APP_DELIVERY_PINGS"] = ping_cnt

    # ==========================================================================
    # 11. OPS_RAW.ZNE_FLEET_SNAP (60,480 rows: 70 days hourly x 36 zones)
    #     Latest snapshot = 2026-03-31 20:00:00 (Dinner peak deficit in LON & NYC!)
    # ==========================================================================
    snap_start = dt.datetime(2026, 1, 21, 0, 0, 0)
    snap_end = dt.datetime(2026, 3, 31, 20, 0, 0)
    snap_cnt = 0
    latest_deficit_top: list[dict] = []
    inflated_sum_online_lon01 = 0
    latest_online_lon01 = 0

    with gzip.open(OUTPUT_DIR / "zne_fleet_snap.csv.gz", "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["SNAP_TS", "ZONE_ID", "ONLINE_CRR_N", "BUSY_CRR_N", "UNASSIGNED_ORD_N"])
        cur_ts = snap_start
        while cur_ts <= snap_end:
            is_dinner = cur_ts.hour in (18, 19, 20, 21)
            is_final_ts = (cur_ts == snap_end)
            for z in zones:
                zid = z["zone_id"]
                if is_final_ts and zid == "ZNE-LON-01":
                    online, busy, unass = 95, 89, 33  # Idle = 6 -> Deficit Ratio = 5.50!
                elif is_final_ts and zid == "ZNE-NYC-01":
                    online, busy, unass = 110, 102, 36  # Idle = 8 -> Deficit Ratio = 4.50!
                elif is_final_ts and zid == "ZNE-PAR-01":
                    online, busy, unass = 84, 76, 26  # Idle = 8 -> Deficit Ratio = 3.25!
                else:
                    online = rng.randint(55, 95) if is_dinner else rng.randint(25, 55)
                    busy = int(online * rng.uniform(0.65, 0.85))
                    unass = rng.randint(2, 12) if is_dinner else rng.randint(0, 4)

                w.writerow([cur_ts.strftime("%Y-%m-%d %H:%M:%S"), zid, online, busy, unass])
                snap_cnt += 1

                if zid == "ZNE-LON-01":
                    inflated_sum_online_lon01 += online
                    if is_final_ts:
                        latest_online_lon01 = online
                if is_final_ts:
                    idle = max(online - busy, 1)
                    latest_deficit_top.append({
                        "zone_id": zid,
                        "city_nm": z["city_nm"],
                        "online": online,
                        "busy": busy,
                        "idle": online - busy,
                        "unassigned": unass,
                        "supply_deficit_ratio": round(unass / idle, 2),
                    })
            cur_ts += dt.timedelta(hours=1)

    row_counts["OPS_RAW.ZNE_FLEET_SNAP"] = snap_cnt
    latest_deficit_top.sort(key=lambda x: x["supply_deficit_ratio"], reverse=True)

    manifest = {
        "seed": SEED,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_rows": sum(row_counts.values()),
        "table_row_counts": row_counts,
        "demo_ground_truth_benchmarks": {
            "q3_2025_calendar_restaurants_true_net_revenue_usd": str(gt_q3_2025_rest_net_rev),
            "q3_2025_calendar_restaurants_naive_current_comm_net_revenue_usd": str(gt_q3_2025_rest_naive_curr_comm_rev),
            "q3_2025_scd2_trap_overstatement_delta_usd": str(gt_q3_2025_rest_naive_curr_comm_rev - gt_q3_2025_rest_net_rev),
            "fy2025_fiscal_net_revenue_restaurants_usd": str(gt_fy2025_net_rev_by_vert[1]),
            "fy2025_fiscal_net_revenue_grocery_usd": str(gt_fy2025_net_rev_by_vert[2]),
            "all_time_true_approved_refunds_usd": str(gt_true_approved_refunds),
            "all_time_fanout_corrupted_refunds_usd": str(gt_fanout_refunds_if_joined_to_lines),
            "lon01_latest_online_couriers": latest_online_lon01,
            "lon01_snapshot_trap_summed_online_couriers": inflated_sum_online_lon01,
            "top_3_supply_deficit_zones_at_latest_snapshot": latest_deficit_top[:3],
            "planted_serial_refund_abusers_count": len(abuser_ids),
            "app_ver_3_8_0_beta_timer_bug_orders": gt_beta_bug_pings,
        },
    }

    manifest_path = OUTPUT_DIR / "ground_truth_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    summary = generate_all()
    print(f"Generated {summary['total_rows']:,} total rows across {len(summary['table_row_counts'])} tables!")
    print(json.dumps(summary, indent=2))
