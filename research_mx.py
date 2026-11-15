#!/usr/bin/env python3
"""Investigación de demanda en Google Trends para México (geo=MX).

Cada tanda incluye términos relacionados. Los valores de Google Trends son
relativos al máximo de la tanda, así que no se comparan entre tandas sin un
término ancla. Guarda un CSV por tanda y un resumen con crecimiento interanual.
"""

import time
from pathlib import Path

import pandas as pd
from pytrends.request import TrendReq

OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

BATCHES = {
    "ancla_mercado": [
        "desarrollo de software",
        "odoo",
        "erp",
        "inteligencia artificial",
        "power bi",
    ],
    "erp_competencia": [
        "odoo",
        "sap",
        "erp",
        "sistema de inventario",
        "punto de venta",
    ],
    "software_medida": [
        "software a la medida",
        "desarrollo de software",
        "aplicación móvil",
        "automatización",
        "n8n",
    ],
    "ia_automatizacion": [
        "inteligencia artificial",
        "chatgpt",
        "automatización",
        "agentes de ia",
        "chatbot",
    ],
    "finanzas_cfdi": [
        "facturación electrónica",
        "cfdi",
        "sistema contable",
        "contabilidad",
        "odoo",
    ],
    "bi_datos": [
        "power bi",
        "dashboard",
        "business intelligence",
        "excel",
        "metabase",
    ],
    "nearshoring": [
        "nearshoring",
        "outsourcing",
        "fábrica de software",
        "consultoría",
        "desarrollo de software",
    ],
}

TIMEFRAME = "today 5-y"
GEO = "MX"
PAUSE = 12


def make_client() -> TrendReq:
    # Sin retries/backoff nativos: pytrends 4.9.2 + urllib3 2.x lanzan TypeError.
    return TrendReq(hl="es-MX", tz=-360, timeout=(10, 30))


def fetch_batch(client: TrendReq, name: str, keywords: list[str]) -> pd.DataFrame | None:
    for attempt in range(1, 4):
        try:
            client.build_payload(keywords, timeframe=TIMEFRAME, geo=GEO)
            df = client.interest_over_time()
            if df.empty:
                print(f"  [{name}] serie vacía")
            return df
        except Exception as exc:  # noqa: BLE001
            print(f"  [{name}] intento {attempt} falló: {type(exc).__name__}: {exc}")
            if attempt < 3:
                time.sleep(45 * attempt)
    return None


def summarize(name: str, df: pd.DataFrame) -> list[dict]:
    df = df.drop(columns=["isPartial"], errors="ignore")
    rows = []
    last = df.tail(52)
    prev = df.iloc[-104:-52]
    for col in df.columns:
        rows.append(
            {
                "tanda": name,
                "termino": col,
                "media_5a": round(float(df[col].mean()), 1),
                "media_12m": round(float(last[col].mean()), 1),
                "media_12m_previos": round(float(prev[col].mean()), 1) if len(prev) else None,
                "crecimiento_%": (
                    round((last[col].mean() / prev[col].mean() - 1) * 100, 1)
                    if len(prev) and prev[col].mean() > 0
                    else None
                ),
                "pico": int(df[col].max()),
                "fecha_pico": df[col].idxmax().strftime("%Y-%m"),
            }
        )
    return rows


def main() -> None:
    client = make_client()
    summary: list[dict] = []
    failed: list[str] = []

    for name, keywords in BATCHES.items():
        print(f"→ {name}: {keywords}")
        df = fetch_batch(client, name, keywords)
        if df is None or df.empty:
            failed.append(name)
        else:
            df.drop(columns=["isPartial"], errors="ignore").to_csv(OUT / f"{name}.csv")
            summary.extend(summarize(name, df))
        time.sleep(PAUSE)

    pd.DataFrame(summary).to_csv(OUT / "resumen.csv", index=False)
    print(f"\nResumen: {OUT / 'resumen.csv'}")

    # Consultas relacionadas y regiones para Odoo
    for term, slug in [("odoo", "odoo"), ("software a la medida", "software_medida_rel")]:
        try:
            client.build_payload([term], timeframe=TIMEFRAME, geo=GEO)
            related = client.related_queries().get(term, {})
            for kind in ("top", "rising"):
                part = related.get(kind) if related else None
                if part is not None and not part.empty:
                    part.to_csv(OUT / f"relacionadas_{slug}_{kind}.csv", index=False)
                    print(f"  relacionadas {term}/{kind}: {len(part)} filas")
        except Exception as exc:  # noqa: BLE001
            print(f"  relacionadas {term} fallaron: {type(exc).__name__}: {exc}")
        time.sleep(PAUSE)

    try:
        client.build_payload(["odoo"], timeframe=TIMEFRAME, geo=GEO)
        regions = client.interest_by_region(resolution="REGION", inc_low_vol=True)
        if not regions.empty:
            regions.sort_values("odoo", ascending=False).to_csv(OUT / "odoo_regiones.csv")
            print(f"  regiones: {len(regions)} filas")
    except Exception as exc:  # noqa: BLE001
        print(f"  regiones fallaron: {type(exc).__name__}: {exc}")

    if failed:
        print(f"\nTandas fallidas: {', '.join(failed)}")


if __name__ == "__main__":
    main()
