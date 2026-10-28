#!/usr/bin/env python3
"""
Genera data/cards.json con las cartas de Marvel Universe (MAR) y su precio en Card Kingdom.

Fuentes:
  1. Scryfall  -> lista de cartas, imágenes, número, colores y precio TCGplayer (respaldo).
  2. Card Kingdom (lista de precios pública) -> precio normal (no foil) y enlace a la carta.
  3. MTGJSON (respaldo) -> si la lista de Card Kingdom falla, toma el precio CK desde AllPricesToday.

Solo usa la biblioteca estándar de Python. Lo ejecuta GitHub Actions una vez al día.
"""
import json
import lzma
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

SET_CODE = "mar"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "cards.json")
UA = "MarCollectionTracker/1.0 (+https://github.com)"

CK_PRICELIST = "https://api.cardkingdom.com/api/v2/pricelist"
MTGJSON_SET = f"https://mtgjson.com/api/v5/{SET_CODE.upper()}.json"
MTGJSON_PRICES = "https://mtgjson.com/api/v5/AllPricesToday.json.xz"


def get(url, raw=False, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data if raw else json.loads(data)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- Scryfall
def scryfall_cards():
    url = f"https://api.scryfall.com/cards/search?q=set%3A{SET_CODE}&unique=prints&order=set"
    cards = []
    while url:
        j = get(url)
        for c in j["data"]:
            face = (c.get("card_faces") or [{}])[0]
            img = c.get("image_uris") or face.get("image_uris") or {}
            prices = c.get("prices") or {}
            tcg = prices.get("usd") or prices.get("usd_foil")
            cards.append({
                "id": c["id"],
                "num": c["collector_number"],
                "name": c["name"],
                "setName": c.get("set_name", "Marvel Universe"),
                "colors": c.get("color_identity", []),
                "image": img.get("normal") or img.get("large") or "",
                "imageLarge": img.get("large") or img.get("png") or img.get("normal") or "",
                "scryfallUrl": c.get("scryfall_uri"),
                "tcgPrice": float(tcg) if tcg else None,
                "ckPrice": None,
                "ckUrl": None,
            })
        url = j.get("next_page") if j.get("has_more") else None
        time.sleep(0.12)
    log(f"Scryfall: {len(cards)} cartas")
    return cards


# ---------------------------------------------------------------- Card Kingdom
def is_true(v):
    return v is True or str(v).lower() in ("true", "1", "yes")


def apply_ck_pricelist(cards):
    """Usa la lista de precios pública de Card Kingdom (incluye scryfall_id)."""
    j = get(CK_PRICELIST, timeout=300)
    rows = j.get("data", j if isinstance(j, list) else [])
    by_sid = {}
    for r in rows:
        sid = r.get("scryfall_id")
        if not sid or is_true(r.get("is_foil")):
            continue
        try:
            price = float(r.get("price_retail") or 0)
        except ValueError:
            continue
        if price <= 0:
            continue
        # Si hay varias filas (variantes), se queda con la más barata
        if sid not in by_sid or price < by_sid[sid]["price"]:
            url = r.get("url") or ""
            if url and not url.startswith("http"):
                url = "https://www.cardkingdom.com/" + url.lstrip("/")
            by_sid[sid] = {"price": price, "url": url or None}
    hits = 0
    for c in cards:
        m = by_sid.get(c["id"])
        if m:
            c["ckPrice"], c["ckUrl"] = m["price"], m["url"]
            hits += 1
    log(f"Card Kingdom (pricelist): {hits}/{len(cards)} con precio")
    return hits


def apply_mtgjson(cards):
    """Respaldo: precio CK desde MTGJSON (AllPricesToday) cruzando por scryfallId."""
    s = get(MTGJSON_SET, timeout=300)
    uuid_by_sid, ck_url_by_sid = {}, {}
    for card in s["data"]["cards"]:
        sid = card.get("identifiers", {}).get("scryfallId")
        if sid:
            uuid_by_sid[sid] = card["uuid"]
            ck_url_by_sid[sid] = (card.get("purchaseUrls") or {}).get("cardKingdom")
    raw = get(MTGJSON_PRICES, raw=True, timeout=600)
    prices = json.loads(lzma.decompress(raw))["data"]
    hits = 0
    for c in cards:
        uuid = uuid_by_sid.get(c["id"])
        if not uuid or c["ckPrice"] is not None:
            continue
        retail = (((prices.get(uuid) or {}).get("paper") or {}).get("cardkingdom") or {}).get("retail") or {}
        normal = retail.get("normal") or {}
        if normal:
            latest = normal[max(normal)]
            c["ckPrice"] = float(latest)
            c["ckUrl"] = c["ckUrl"] or ck_url_by_sid.get(c["id"])
            hits += 1
    log(f"Card Kingdom (MTGJSON): {hits} precios adicionales")
    return hits


# ---------------------------------------------------------------- Main
def main():
    cards = scryfall_cards()
    source = "scryfall-only"

    try:
        if apply_ck_pricelist(cards):
            source = "cardkingdom"
    except Exception as e:  # noqa: BLE001
        log(f"Aviso: falló la lista de Card Kingdom: {e}")

    if any(c["ckPrice"] is None for c in cards):
        try:
            if apply_mtgjson(cards):
                source = "cardkingdom"
        except Exception as e:  # noqa: BLE001
            log(f"Aviso: falló MTGJSON: {e}")

    # Conservar el último precio CK conocido si hoy no se obtuvo
    try:
        with open(OUT, encoding="utf-8") as f:
            prev = {c["id"]: c for c in json.load(f).get("cards", [])}
        for c in cards:
            p = prev.get(c["id"])
            if c["ckPrice"] is None and p and p.get("ckPrice") is not None:
                c["ckPrice"], c["ckUrl"] = p["ckPrice"], c["ckUrl"] or p.get("ckUrl")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    with_ck = sum(c["ckPrice"] is not None for c in cards)
    out = {
        "meta": {
            "set": SET_CODE.upper(),
            "source": source,
            "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "count": len(cards),
            "withCardKingdomPrice": with_ck,
        },
        "cards": cards,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    log(f"Listo: {len(cards)} cartas, {with_ck} con precio Card Kingdom -> {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
