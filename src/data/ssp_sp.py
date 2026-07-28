from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests
from loguru import logger

SPSAFE_URL = "https://zenodo.org/api/records/16739645/files/csv.zip/content"
SSP_TRANSPARENCY_BASE = "https://www.ssp.sp.gov"


def download_spsafe_dataset(
    dest_dir: Path,
    years: list[int] | None = None,
) -> dict[str, Path]:
    import io
    import time
    import zipfile

    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    dest_dir.mkdir(parents=True, exist_ok=True)

    zip_path = dest_dir / "SPSafe_CSV.zip"
    if not zip_path.exists():
        logger.info("Baixando SPSafe de {}", SPSAFE_URL)

        retry_strategy = Retry(
            total=10,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        for attempt in range(1, 6):
            logger.info("Tentativa {}/5...", attempt)
            existing = zip_path.stat().st_size if zip_path.exists() else 0
            headers = {}
            if existing > 0:
                headers["Range"] = f"bytes={existing}-"
                logger.info(
                    "Retomando download de {} MB",
                    existing / 1e6,
                )
            try:
                with session.get(
                    SPSAFE_URL,
                    headers=headers,
                    timeout=(30, 120),
                    stream=True,
                ) as resp:
                    if resp.status_code == 416:
                        logger.info("Download ja esta completo")
                        break
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    mode = "ab" if existing > 0 and resp.status_code == 206 else "wb"
                    downloaded = existing if mode == "ab" else 0
                    start_time = time.time()
                    with open(zip_path, mode) as f:
                        for chunk in resp.iter_content(chunk_size=262144):
                            f.write(chunk)
                            downloaded += len(chunk)
                            elapsed = time.time() - start_time
                            if elapsed > 10 and downloaded % (5 * 1024 * 1024) < 262144:
                                speed = (downloaded - existing) / elapsed
                                total_size = existing + total if resp.status_code == 206 else total
                                if total_size:
                                    pct = downloaded * 100 // total_size
                                    eta = (total_size - downloaded) / speed if speed > 0 else 0
                                    logger.info(
                                        "Download: {:.0f}% ({:.0f} MB / {:.0f} MB)"
                                        " - {:.0f} KB/s - ETA: {:.0f} min",
                                        pct, downloaded / 1e6,
                                        total_size / 1e6,
                                        speed / 1024,
                                        eta / 60,
                                    )
                logger.info(
                    "SPSafe baixado: {} bytes",
                    zip_path.stat().st_size,
                )
                break
            except Exception as e:
                logger.warning("Erro na tentativa {}: {}", attempt, e)
                time.sleep(5 * attempt)
        else:
            logger.warning("Falha ao baixar SPSafe apos 5 tentativas")
            return {}

    logger.info("Extraindo SPSafe...")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            csv_files = [
                f for f in zf.namelist()
                if f.endswith(".csv") and not f.startswith("__MACOSX")
            ]
            logger.info("Arquivos CSV no SPSafe: {}", csv_files)

            extracted = {}
            for csv_name in csv_files:
                year_match = None
                for part in csv_name.split("/"):
                    if part.isdigit() and len(part) == 4:
                        year_match = int(part)
                        break

                if years and year_match and year_match not in years:
                    continue

                data = zf.read(csv_name)
                df = pd.read_csv(io.BytesIO(data), encoding="utf-8", low_memory=False)

                out_name = Path(csv_name).name
                out_path = dest_dir / out_name
                df.to_csv(out_path, index=False)
                extracted[out_name] = out_path
                logger.info("SPSafe: {} -> {} registros", out_name, len(df))

            return extracted
    except Exception as e:
        logger.warning("Erro ao extrair SPSafe: {}", e)
        return {}


def normalize_spsafe_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {
        "ANO BO": "ano_bo",
        "NUM BO": "num_bo",
        "NATUREZA APURADA": "natureza",
        "DATA OCORRENCIA": "data",
        "HORA OCORRENCIA": "horario",
        "CIDADE": "cidade",
        "BAIRRO": "bairro",
        "LATITUDE": "latitude",
        "LONGITUDE": "longitude",
        "DELEGACIA ELABORACAO": "delegacia",
        "PERIODO OCORRENCIA": "periodo",
        "COD IBGE": "cod_ibge",
        "TIPO LOCAL": "tipo_local",
    }

    df = df.rename(columns=col_map)

    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")

    if "latitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    if "longitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    return df


def merge_ssp_datasets(
    existing_csv: Path,
    spsafe_dir: Path,
    years: list[int] | None = None,
    city_filter: str | None = "SAO PAULO",
) -> pd.DataFrame:
    existing = pd.read_csv(existing_csv, encoding="utf-8", low_memory=False)
    existing["data"] = pd.to_datetime(
        existing.get("data", existing.get("DATA", "")),
        errors="coerce",
    )

    if "latitude" in existing.columns:
        existing["latitude"] = pd.to_numeric(existing["latitude"], errors="coerce")
    if "longitude" in existing.columns:
        existing["longitude"] = pd.to_numeric(existing["longitude"], errors="coerce")

    new_frames = []
    for csv_file in sorted(spsafe_dir.glob("*.csv")):
        if csv_file.name == existing_csv.name:
            continue

        try:
            df = pd.read_csv(csv_file, encoding="utf-8", low_memory=False)
            df = normalize_spsafe_columns(df)

            if "cidade" in df.columns and city_filter:
                city_pattern = city_filter.upper()
                df = df[
                    df["cidade"].str.upper().str.contains(city_pattern, na=False)
                ]

            if years and "ano_bo" in df.columns:
                df = df[df["ano_bo"].isin(years)]

            if "latitude" in df.columns and "longitude" in df.columns:
                df = df.dropna(subset=["latitude", "longitude"])
                df = df[
                    (df["latitude"].abs() < 90)
                    & (df["longitude"].abs() < 180)
                ]

            new_frames.append(df)
            logger.info(
                "SPSafe {} OK: {} registros {}",
                csv_file.name, len(df), city_filter or "ALL",
            )
        except Exception as e:
            logger.warning("Erro ao processar {}: {}", csv_file.name, e)

    if not new_frames:
        return existing

    new_data = pd.concat(new_frames, ignore_index=True)

    merged = pd.concat([existing, new_data], ignore_index=True)
    merged = merged.drop_duplicates(
        subset=["latitude", "longitude", "data"],
        keep="first",
    )

    logger.info(
        "Merge SSP: {} (original) + {} (novo) = {} (total)",
        len(existing),
        len(new_data),
        len(merged),
    )

    return merged


def try_fetch_quarterly_stats(
    year: int,
    quarter: int,
    dest_dir: Path,
) -> dict | None:
    url = f"{SSP_TRANSPARENCY_BASE}/assets/estatistica/trimestral/arquivos/{year}-{quarter:02d}.htm"

    logger.info("Buscando estatisticas trimestrais: {}", url)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Erro ao buscar trimestre {}/{}: {}", year, quarter, e)
        return None

    from io import StringIO

    tables = pd.read_html(StringIO(resp.text), encoding="utf-8")
    if not tables:
        logger.warning("Nenhuma tabela encontrada no HTML")
        return None

    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / f"ssp_trimestral_{year}_{quarter}.csv"

    combined = pd.concat(tables, ignore_index=True)
    combined.to_csv(out_path, index=False)
    logger.info("Estatisticas trimestrais salvas: {}", out_path)

    return {"file": out_path, "rows": len(combined)}
