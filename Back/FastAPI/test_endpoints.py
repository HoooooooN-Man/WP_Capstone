# -*- coding: utf-8 -*-
"""Quick smoke test for all API endpoints."""
import urllib.request
import json

BASE = "http://localhost:8001"

def get(path):
    url = BASE + path
    try:
        r = urllib.request.urlopen(url, timeout=30)
        return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

print("=== GET / ===")
print(get("/"))

print("\n=== /api/v1/stocks/versions ===")
v = get("/api/v1/stocks/versions")
print(v)

print("\n=== /api/v1/stocks/dates?model_version=v7 (first 3) ===")
d = get("/api/v1/stocks/dates?model_version=v7")
print("total dates:", len(d.get("dates", [])), " latest:", d.get("latest"))

print("\n=== /api/v1/stocks/recommendations?top_k=5&min_score=80 ===")
rec = get("/api/v1/stocks/recommendations?top_k=5&min_score=80")
print("date:", rec.get("date"), " model:", rec.get("model_version"), " total:", rec.get("total"))
for item in rec.get("items", []):
    print(
        " ",
        item["ticker"],
        (item.get("name") or "")[:15],
        (item.get("sector") or "")[:12],
        "score=" + str(item["score"]),
        "tier=" + item["tier"],
    )

print("\n=== /api/v1/stocks/sectors/summary (top 5) ===")
sec = get("/api/v1/stocks/sectors/summary")
for s in sec.get("items", [])[:5]:
    print(
        " ",
        (s["sector"] or "?")[:18],
        "avg=" + str(s["avg_score"]),
        "A-tier=" + str(s["tier_a_count"]) + "/" + str(s["stock_count"]),
    )

print("\n=== /api/v1/stocks/000660/history (first 3 rows) ===")
hist = get("/api/v1/stocks/000660/history")
if "error" in hist:
    print(hist)
else:
    print("total:", hist.get("total"))
    for row in hist.get("items", [])[:3]:
        print(" ", row["date"], "score=" + str(row["score"]), "tier=" + row["tier"])

print("\n=== /api/v1/portfolio/backtest/summary ===")
bt = get("/api/v1/portfolio/backtest/summary")
if "error" in bt:
    print(bt)
else:
    print("keys:", list(bt.keys()))
    if bt.get("v8_walk_forward"):
        print(bt["v8_walk_forward"][:300])
