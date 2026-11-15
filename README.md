# pytrends-test

Carpeta de pruebas de [`pytrends`](https://github.com/GeneralMills/pytrends), el wrapper no oficial de Google Trends.

## Estado

- Python 3.14.4 + venv en `.venv/`
- `pytrends 4.9.2`, `pandas 3.1.1`
- Primera consulta verificada: `inteligencia artificial`, geo `ES`, últimos 12 meses → 54 puntos + interés por región.

## Uso

```bash
cd /home/edgar/Proyectos/pytrends-test
.venv/bin/python test_pytrends.py                        # consulta por defecto
.venv/bin/python test_pytrends.py "python" "rust"        # hasta 5 términos
.venv/bin/python test_pytrends.py "bitcoin" --geo MX --timeframe "today 5-y"
```

Genera `interes_tiempo.csv` e `interes_region.csv` en esta carpeta.

## Notas / problemas conocidos

- **`method_whitelist` TypeError**: `TrendReq(retries=..., backoff_factor=...)` rompe con urllib3 ≥ 2 porque
  pytrends 4.9.2 pasa un argumento eliminado. Solución aplicada: no usar esos parámetros y reintentar manualmente
  en el script. Alternativa: `pip install "urllib3<2"`.
- **HTTP 429**: Google bloquea ráfagas de peticiones. Deja segundos entre consultas, no paralelices y evita
  `interest_over_time` masivos en bucle.
- **Series vacías**: términos con poco volumen devuelven `DataFrame` vacío; no es un fallo del código.
- `interest_over_time` devuelve la columna `isPartial` para el periodo en curso; el script la excluye al exportar.
- Límites de la API de Trends: máx. 5 términos por consulta, ventanas de tiempo válidas (`now 7-d`,
  `today 12-m`, `today 5-y`, `all`, o rangos `YYYY-MM-DD YYYY-MM-DD`).
