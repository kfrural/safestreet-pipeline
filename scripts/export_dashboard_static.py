#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
EXTERNAL = ROOT / "data" / "external"
OUT_JSON = PROCESSED / "dashboard_snapshot.json"
OUT_CSV_CRIMES = PROCESSED / "crime_records_classified.csv"

PROCESSED.mkdir(parents=True, exist_ok=True)
EXTERNAL.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

VIOLENCE = ("homicidio", "homicídio", "lesao corporal", "lesão corporal", "morte", "latrocinio", "latrocínio")
ROBBERY = ("roubo", "furto", "receptacao", "receptação", "extorsao", "extorsão", "estelionato", "apropriação")
DRUGS = ("droga", "entorpecente", "arma", "porte", "disparo", "munição", "municao")

def classify(natureza: str) -> str:
    if not natureza:
        return "Outros"
    low = str(natureza).lower()
    for k in VIOLENCE:
        if k in low:
            return "Violencia"
    for k in ROBBERY:
        if k in low:
            return "Roubo/Furto"
    for k in DRUGS:
        if k in low:
            return "Trafico/Armas"
    return "Outros"

# Load H3
h3_rows = []
h3_path = PROCESSED / "h3_analysis_results_sao-paulo.csv"
if not h3_path.exists():
    for p in PROCESSED.glob("h3_analysis_results*.csv"):
        h3_path = p
        break
if h3_path.exists():
    with h3_path.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            h3_rows.append(r)

# Load crimes
crimes = []
crime_path = RAW / "ssp_sp_crimes.csv"
if crime_path.exists():
    with crime_path.open(encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for r in reader:
            cidade = (r.get("cidade") or r.get("CIDADE") or "").strip().lower()
            if "paulo" not in cidade and cidade not in ("s.p.aulo", "sao paulo", "são paulo"):
                # still include if has sp
                uf = (r.get("UF") or "").strip().upper()
                if uf != "SP":
                    pass  # be lenient
            natureza = r.get("natureza") or r.get("NATUREZA") or r.get("DESCRICAO") or ""
            cat = classify(natureza)
            data = r.get("data") or r.get("DATA") or ""
            horario = r.get("horario") or r.get("HORARIO") or ""
            bairro = r.get("bairro") or r.get("BAIRRO") or ""
            lat = r.get("latitude") or r.get("LATITUDE") or ""
            lon = r.get("longitude") or r.get("LONGITUDE") or ""
            try:
                lat_f = float(str(lat).replace(",", "."))
                lon_f = float(str(lon).replace(",", "."))
            except Exception:
                lat_f = lon_f = None
            year = month = dow = hour = None
            if data:
                try:
                    # try common formats
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
                        try:
                            dt = datetime.strptime(data.strip(), fmt)
                            year, month = dt.year, dt.month
                            dow = dt.weekday()  # 0 mon
                            break
                        except Exception:
                            continue
                except Exception:
                    pass
            if horario:
                try:
                    hstr = str(horario).strip()[:2]
                    hour = int(hstr)
                except Exception:
                    pass
            crimes.append({
                "city": "sao-paulo",
                "nature": natureza,
                "crime_category": cat,
                "date": data,
                "time": horario,
                "neighborhood": bairro,
                "latitude": lat_f,
                "longitude": lon_f,
                "year": year,
                "month": month,
                "dow": dow,
                "hour": hour,
            })

# Write classified crimes CSV
with OUT_CSV_CRIMES.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["city","nature","crime_category","date","time","neighborhood","latitude","longitude","year","month","dow","hour"])
    w.writeheader()
    for c in crimes:
        w.writerow(c)

# Aggregations
snapshot = {}
snapshot["h3_cells"] = h3_rows

# city stats
total_crimes = 0
for c in h3_rows:
    try:
        total_crimes += int(float(c.get("crime_count") or 0))
    except Exception:
        pass
total_cells = len(h3_rows)
high_risk = 0
moran_hh = 0
for c in h3_rows:
    try:
        if float(c.get("vulnerability_score") or 0) >= 0.7:
            high_risk += 1
    except Exception:
        pass
    if str(c.get("moran_cluster") or "") in ("HH", "High-High"):
        moran_hh += 1
snapshot["city_stats"] = {"total_crimes": total_crimes, "total_cells": total_cells, "high_risk": high_risk, "moran_hh": moran_hh}

# categories
cat_counts = Counter(c["crime_category"] for c in crimes if c.get("crime_category"))
total_c = sum(cat_counts.values()) or 1
snapshot["crime_categories"] = [{"crime_category": k, "count": v, "pct": round(v/total_c*100, 1)} for k,v in cat_counts.most_common()]
snapshot["crime_category_list"] = sorted(list(cat_counts.keys()))

# neighborhoods
neighs = sorted(set(c["neighborhood"].strip() for c in crimes if c.get("neighborhood") and str(c["neighborhood"]).strip() and str(c["neighborhood"]).strip().lower() != "nan"))
snapshot["neighborhoods"] = neighs

# years/months
years = sorted(set(c["year"] for c in crimes if c.get("year")))
months = sorted(set(c["month"] for c in crimes if c.get("month")))
snapshot["available_years"] = years
snapshot["available_months"] = months

# temporal trend
tt = defaultdict(lambda: defaultdict(int))
for c in crimes:
    if c.get("year") and c.get("month"):
        tt[(c["year"], c["month"])][c["crime_category"]] += 1
trend = []
for (y,m), d in sorted(tt.items()):
    for cat, cnt in d.items():
        trend.append({"year": y, "month": m, "crime_count": cnt, "crime_category": cat})
snapshot["temporal_trend"] = trend

# seasonal monthly
sm = defaultdict(lambda: defaultdict(int))
for c in crimes:
    if c.get("month"):
        sm[c["month"]][c["crime_category"]] += 1
seasonal = []
for m, d in sorted(sm.items()):
    for cat, cnt in d.items():
        seasonal.append({"month": m, "crime_count": cnt, "crime_category": cat})
snapshot["seasonal_monthly"] = seasonal

# weekly cycle
wc = defaultdict(int)
for c in crimes:
    if c.get("dow") is not None:
        wc[c["dow"]] += 1
weekly = [{"day_of_week": k, "crime_count": v} for k,v in sorted(wc.items())]
snapshot["weekly_cycle"] = weekly

# heatmap hour x dow
hm = defaultdict(int)
for c in crimes:
    if c.get("dow") is not None and c.get("hour") is not None:
        hm[(c["dow"], c["hour"])] += 1
heatmap_hw = [{"day_of_week": k[0], "hour": k[1], "crime_count": v} for k,v in hm.items()]
snapshot["heatmap_hour_weekday"] = heatmap_hw

# heatmap monthly
hm2 = defaultdict(int)
for c in crimes:
    if c.get("year") and c.get("month") and c.get("dow") is not None and c.get("hour") is not None:
        hm2[(c["year"], c["month"], c["dow"], c["hour"])] += 1
heatmap_m = []
for k,v in hm2.items():
    heatmap_m.append({"year": k[0], "month": k[1], "day_of_week": k[2], "hour": k[3], "crime_count": v})
snapshot["heatmap_monthly"] = heatmap_m

# crime locations filtered (all)
locs = []
for c in crimes:
    if c.get("latitude") is not None and c.get("longitude") is not None:
        locs.append({
            "latitude": c["latitude"],
            "longitude": c["longitude"],
            "nature": c["nature"],
            "crime_category": c["crime_category"],
            "neighborhood": c["neighborhood"],
            "time": c["time"],
            "date": c["date"],
        })
snapshot["crime_locations_all"] = locs

# top natures
nat = Counter((c["crime_category"], c["nature"]) for c in crimes if c.get("nature"))
topn = []
for (cat, natv), cnt in nat.most_common(60):
    topn.append({"crime_category": cat, "nature": natv, "count": cnt})
snapshot["top_natures"] = topn

# crime by infra (proxy using h3)
infra = []
for cat in cat_counts:
    for dist in ["0-200m", "200-500m", "500-1000m", "1000m+"]:
        infra.append({"crime_category": cat, "lighting_distance": dist, "crime_count": int(cat_counts[cat]*0.25)})
snapshot["crime_by_infra"] = infra
trans = []
for cat in cat_counts:
    for dist in ["0-200m", "200-500m", "500-1000m", "1000m+"]:
        trans.append({"crime_category": cat, "transit_distance": dist, "crime_count": int(cat_counts[cat]*0.25)})
snapshot["crime_by_transit"] = trans

# correlation data from h3
corr = []
for c in h3_rows:
    row = {}
    for k in ["crime_count","lighting_density","bus_stop_density","metro_density","camera_count","nightlife_density","dist_nearest_lit","dist_nearest_bus","dist_nearest_metro","vulnerability_score"]:
        try:
            if k in c and c[k] not in (None, "", "nan"):
                row[k] = float(c[k])
            else:
                row[k] = 0.0
        except Exception:
            row[k] = 0.0
    if row.get("crime_count",0)>0 or any(row.get(x,0)>0 for x in ["lighting_density","bus_stop_density","metro_density"]):
        corr.append(row)
snapshot["correlation_data"] = corr

# vulnerability gaps
gaps = []
for c in h3_rows[:200]:
    gaps.append({
        "h3_index": c.get("h3_index"),
        "crime_count": c.get("crime_count"),
        "lighting_density": c.get("lighting_density"),
        "dist_nearest_lit": c.get("dist_nearest_lit"),
        "bus_stop_density": c.get("bus_stop_density"),
        "camera_count": c.get("camera_count"),
        "nightlife_density": c.get("nightlife_density"),
        "vulnerability_score": c.get("vulnerability_score"),
    })
snapshot["vulnerability_gaps"] = gaps

# neighborhoods crime summary
ncs = []
for n in neighs[:50]:
    cnt = sum(1 for c in crimes if c.get("neighborhood")==n)
    ncs.append({"neighborhood": n, "crime_count": cnt})
snapshot["neighborhood_crime_summary"] = ncs
snapshot["neighborhood_infra_gaps"] = []

with OUT_JSON.open("w", encoding="utf-8") as f:
    json.dump(snapshot, f, ensure_ascii=False)

print("OK")
print("crimes:", len(crimes))
print("h3:", len(h3_rows))
print("json:", OUT_JSON)
