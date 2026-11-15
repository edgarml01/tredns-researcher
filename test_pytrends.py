#!/usr/bin/env python3
"""Prueba básica de pytrends: interés en el tiempo y por región.

Uso:
    .venv/bin/python test_pytrends.py
    .venv/bin/python test_pytrends.py "inteligencia artificial" "machine learning"
"""

import argparse
import sys
import time

import pandas as pd
from pytrends.request import TrendReq


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba de pytrends")
    parser.add_argument(
        "keywords",
        nargs="*",
        default=["inteligencia artificial"],
        help="Hasta 5 términos separados por espacio",
    )
    parser.add_argument("--geo", default="ES", help="País (ES, MX, US...) o '' para mundial")
    parser.add_argument("--timeframe", default="today 12-m", help="Rango temporal de Google Trends")
    parser.add_argument("--hl", default="es-ES", help="Idioma de la interfaz")
    args = parser.parse_args()

    kw = args.keywords[:5]
    print(f"Consulta: {kw} | geo={args.geo or 'mundial'} | timeframe={args.timeframe}")

    # No usamos retries/backoff_factor de TrendReq: pytrends 4.9.2 pasa
    # method_whitelist a urllib3 2.x y revienta con TypeError. Reintentamos a mano.
    pytrends = TrendReq(hl=args.hl, tz=0, timeout=(10, 25))

    try:
        for attempt in range(1, 4):
            try:
                pytrends.build_payload(kw, timeframe=args.timeframe, geo=args.geo)
                df = pytrends.interest_over_time()
                break
            except Exception:  # noqa: BLE001
                if attempt == 3:
                    raise
                print(f"  reintento {attempt}/3 tras error...", file=sys.stderr)
                time.sleep(5 * attempt)
    except Exception as exc:  # noqa: BLE001 - queremos ver el error real
        print(f"\n✗ Falló la petición: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if df.empty:
        print("\n⚠ Google Trends devolvió una serie vacía (términos sin volumen suficiente).")
        return 2

    print(f"\n✓ {len(df)} puntos obtenidos ({df.index.min().date()} → {df.index.max().date()})")
    print(df[kw].tail(5).to_string())

    out = "interes_tiempo.csv"
    df.drop(columns=["isPartial"], errors="ignore").to_csv(out)
    print(f"\nGuardado: {out}")

    time.sleep(2)  # evita 429 entre peticiones

    try:
        by_region = pytrends.interest_by_region(resolution="REGION", inc_low_vol=True)
    except Exception as exc:  # noqa: BLE001
        print(f"\n⚠ Interés por región no disponible: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 0

    if not by_region.empty:
        by_region = by_region.sort_values(by=by_region.columns[0], ascending=False)
        print("\nTop 5 regiones:")
        print(by_region.head(5).to_string())
        by_region.to_csv("interes_region.csv")
        print("\nGuardado: interes_region.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
