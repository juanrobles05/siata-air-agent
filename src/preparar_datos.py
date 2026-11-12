#!/usr/bin/env python3
from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path

import pandas as pd

DATA_URL = "https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv"
ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "calidad_aire_ideam.csv"
OUT_PATH = ROOT / "data" / "valle_aburra_pm25.csv"

# Municipios del Area Metropolitana del Valle de Aburra (clave sin tildes, en mayusculas).
MUNICIPIOS = {
    "MEDELLIN": "Medellín",
    "BELLO": "Bello",
    "ITAGUI": "Itagüí",
    "ENVIGADO": "Envigado",
    "SABANETA": "Sabaneta",
    "LA ESTRELLA": "La Estrella",
    "CALDAS": "Caldas",
    "COPACABANA": "Copacabana",
    "GIRARDOTA": "Girardota",
    "BARBOSA": "Barbosa",
}


def sin_tildes(texto: str) -> str:
    norm = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in norm if not unicodedata.combining(c))


def cargar_crudo(forzar_descarga: bool) -> pd.DataFrame:
    if forzar_descarga or not RAW_PATH.exists():
        print(f"Descargando {DATA_URL} ...")
        RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        df = pd.read_csv(DATA_URL, low_memory=False)
        df.to_csv(RAW_PATH, index=False)
    else:
        print(f"Usando copia local: {RAW_PATH}")
        df = pd.read_csv(RAW_PATH, low_memory=False)
    return df


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["municipio_key"] = df["nombre_del_municipio"].map(lambda s: sin_tildes(s).strip().upper())
    df = df[df["municipio_key"].isin(MUNICIPIOS)]
    df = df[df["variable"].astype(str).str.strip() == "PM2.5"]
    df = df[df["tiempo_de_exposici_n_horas"] == 24]

    df["municipio"] = df["municipio_key"].map(MUNICIPIOS)
    df["estacion"] = df["estaci_n"].astype(str).str.replace("*", "", regex=False).str.strip()

    cols = {
        "id_estacion": "id_estacion",
        "estacion": "estacion",
        "municipio": "municipio",
        "latitud": "latitud",
        "longitud": "longitud",
        "a_o": "anio",
        "promedio": "promedio",
        "mediana": "mediana",
        "percentil_98": "percentil98",
        "m_ximo": "maximo",
        "m_nimo": "minimo",
        "no_de_datos": "num_datos",
        "representatividad_temporal": "representatividad",
        "d_as_de_excedencias": "dias_excedencia",
        "tipo_de_estaci_n": "tipo_estacion",
        "autoridad_ambiental": "autoridad",
    }
    df = df[list(cols)].rename(columns=cols)

    for c in ["latitud", "longitud", "anio", "promedio", "mediana", "percentil98",
              "maximo", "minimo", "num_datos", "representatividad", "dias_excedencia"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["id_estacion", "anio", "promedio"])
    df["anio"] = df["anio"].astype(int)

    # El CSV trae filas exactamente repetidas; se conserva una por estacion-año.
    df = df.drop_duplicates(subset=["id_estacion", "anio"], keep="last")

    # Un solo nombre y coordenada por estacion (el del año mas reciente).
    df = df.sort_values(["id_estacion", "anio"])
    ultimo = df.groupby("id_estacion")[["estacion", "municipio", "latitud", "longitud"]].transform("last")
    df[["estacion", "municipio", "latitud", "longitud"]] = ultimo

    return df.sort_values(["municipio", "estacion", "anio"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara el dataset PM2.5 del Valle de Aburra")
    parser.add_argument("--descargar", action="store_true", help="Fuerza una nueva descarga")
    args = parser.parse_args()

    df = preparar(cargar_crudo(args.descargar))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8")

    print(f"Guardado: {OUT_PATH}")
    print(f"Filas: {len(df)} | Estaciones: {df['id_estacion'].nunique()} | "
          f"Años: {df['anio'].min()}-{df['anio'].max()}")
    print(df.groupby("municipio")["id_estacion"].nunique().to_string())


if __name__ == "__main__":
    main()
