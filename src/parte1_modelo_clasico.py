#!/usr/bin/env python3
"""Parte 1 del proyecto: modelo clasico con datos reales de calidad del aire.

Fuente de datos:
https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv

Este script:
1) Descarga datos reales desde la API.
2) Construye un dataset tabular por estacion-anio.
3) Define la categoria objetivo de PM2.5 del siguiente anio.
4) Entrena un Gaussian Naive Bayes implementado desde cero.
5) Compara contra una linea base de clase mayoritaria.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

DATA_URL = "https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv"


@dataclass
class EvaluationResult:
    accuracy: float
    macro_f1: float
    balanced_accuracy: float


class GaussianNaiveBayesScratch:
    """Gaussian Naive Bayes implementado desde cero con NumPy."""

    def __init__(self, var_smoothing: float = 1e-9) -> None:
        self.var_smoothing = var_smoothing
        self.classes_: np.ndarray | None = None
        self.class_priors_: np.ndarray | None = None
        self.theta_: np.ndarray | None = None
        self.sigma_: np.ndarray | None = None

    def fit(self, x: np.ndarray, y: np.ndarray) -> "GaussianNaiveBayesScratch":
        classes, counts = np.unique(y, return_counts=True)
        self.classes_ = classes
        self.class_priors_ = counts / counts.sum()

        n_classes = len(classes)
        n_features = x.shape[1]

        theta = np.zeros((n_classes, n_features), dtype=float)
        sigma = np.zeros((n_classes, n_features), dtype=float)

        for idx, cls in enumerate(classes):
            x_c = x[y == cls]
            theta[idx, :] = x_c.mean(axis=0)
            sigma[idx, :] = x_c.var(axis=0) + self.var_smoothing

        self.theta_ = theta
        self.sigma_ = sigma
        return self

    def _joint_log_likelihood(self, x: np.ndarray) -> np.ndarray:
        if any(v is None for v in (self.classes_, self.class_priors_, self.theta_, self.sigma_)):
            raise RuntimeError("El modelo debe entrenarse con fit() antes de predecir.")

        assert self.class_priors_ is not None
        assert self.theta_ is not None
        assert self.sigma_ is not None

        n_samples = x.shape[0]
        n_classes = self.theta_.shape[0]
        jll = np.zeros((n_samples, n_classes), dtype=float)

        for idx in range(n_classes):
            mean = self.theta_[idx]
            var = self.sigma_[idx]
            log_prior = math.log(self.class_priors_[idx])
            # log de la gaussiana por feature y suma sobre features
            log_prob = -0.5 * np.sum(np.log(2.0 * np.pi * var))
            log_prob -= 0.5 * np.sum(((x - mean) ** 2) / var, axis=1)
            jll[:, idx] = log_prior + log_prob

        return jll

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.classes_ is None:
            raise RuntimeError("El modelo debe entrenarse con fit() antes de predecir.")
        jll = self._joint_log_likelihood(x)
        class_indexes = np.argmax(jll, axis=1)
        return self.classes_[class_indexes]


class MajorityClassBaseline:
    """Linea base: siempre predice la clase mas frecuente del entrenamiento."""

    def __init__(self) -> None:
        self.majority_class_: str | None = None

    def fit(self, y: np.ndarray) -> "MajorityClassBaseline":
        values, counts = np.unique(y, return_counts=True)
        self.majority_class_ = str(values[np.argmax(counts)])
        return self

    def predict(self, n_samples: int) -> np.ndarray:
        if self.majority_class_ is None:
            raise RuntimeError("La linea base debe entrenarse antes de predecir.")
        return np.array([self.majority_class_] * n_samples)


def normalize_column_name(name: str) -> str:
    cleaned = name.strip().lower()
    out = []
    for ch in cleaned:
        if ch.isalnum():
            out.append(ch)
        else:
            out.append("_")
    compact = "".join(out)
    while "__" in compact:
        compact = compact.replace("__", "_")
    return compact.strip("_")


def find_column(columns: List[str], candidates: List[str], contains: bool = False) -> str:
    normalized = [normalize_column_name(c) for c in columns]
    for cand in candidates:
        cand_norm = normalize_column_name(cand)
        for i, col in enumerate(normalized):
            if contains:
                if cand_norm in col:
                    return columns[i]
            else:
                if cand_norm == col:
                    return columns[i]
    raise KeyError(f"No se encontro columna para candidatos: {candidates}")


def find_column_by_tokens(columns: List[str], token_groups: List[List[str]]) -> str:
    normalized = [normalize_column_name(c) for c in columns]
    for tokens in token_groups:
        norm_tokens = [normalize_column_name(t) for t in tokens]
        for i, col in enumerate(normalized):
            if all(token in col for token in norm_tokens):
                return columns[i]
    raise KeyError(f"No se encontro columna por tokens: {token_groups}")


def label_pm25_category(value: float) -> str:
    if value <= 12.0:
        return "buena"
    if value <= 35.4:
        return "moderada"
    return "danina"


def macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    labels = np.unique(np.concatenate([y_true, y_pred]))
    f1_scores = []
    for label in labels:
        tp = np.sum((y_true == label) & (y_pred == label))
        fp = np.sum((y_true != label) & (y_pred == label))
        fn = np.sum((y_true == label) & (y_pred != label))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        f1_scores.append(f1)
    return float(np.mean(f1_scores))


def balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    labels = np.unique(y_true)
    recalls = []
    for label in labels:
        tp = np.sum((y_true == label) & (y_pred == label))
        fn = np.sum((y_true == label) & (y_pred != label))
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        recalls.append(rec)
    return float(np.mean(recalls))


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> EvaluationResult:
    acc = float(np.mean(y_true == y_pred))
    return EvaluationResult(
        accuracy=acc,
        macro_f1=macro_f1(y_true, y_pred),
        balanced_accuracy=balanced_accuracy(y_true, y_pred),
    )


def confusion_matrix_counts(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Dict[str, int]]:
    labels = sorted(np.unique(np.concatenate([y_true, y_pred])).tolist())
    matrix: Dict[str, Dict[str, int]] = {
        true_label: {pred_label: 0 for pred_label in labels} for true_label in labels
    }
    for true_label, pred_label in zip(y_true, y_pred):
        matrix[str(true_label)][str(pred_label)] += 1
    return matrix


def load_and_prepare(url: str) -> Tuple[pd.DataFrame, int]:
    raw = pd.read_csv(url, low_memory=False)

    # Mapeo robusto por nombres potencialmente con codificacion irregular.
    cols = raw.columns.tolist()
    variable_col = find_column(cols, ["variable"])
    exposure_col = find_column_by_tokens(cols, [["exposici", "horas"], ["tiempo", "horas"]])
    year_col = find_column_by_tokens(cols, [["a_o"], ["ano"]])
    station_col = find_column_by_tokens(cols, [["id", "estacion"]])
    average_col = find_column(cols, ["promedio"], contains=True)

    # Columnas numericas de apoyo para el modelo (se detectan de forma flexible).
    numeric_optional: Dict[str, List[List[str]]] = {
        "mediana": [["mediana"]],
        "percentil98": [["percentil", "98"]],
        "maximo": [["m_ximo"], ["maximo"]],
        "minimo": [["m_nimo"], ["minimo"]],
        "num_datos": [["no_de_datos"], ["datos"]],
        "representatividad": [["representatividad"]],
    }

    selected_cols = {
        "id_estacion": station_col,
        "ano": year_col,
        "variable": variable_col,
        "exposicion_horas": exposure_col,
        "promedio": average_col,
    }

    for alias, token_sets in numeric_optional.items():
        try:
            selected_cols[alias] = find_column_by_tokens(cols, token_sets)
        except KeyError:
            # Si una columna no existe, el pipeline sigue con las disponibles.
            pass

    work = raw[list(selected_cols.values())].copy()
    work.columns = list(selected_cols.keys())

    for numeric_col in [c for c in work.columns if c not in {"id_estacion", "variable"}]:
        work[numeric_col] = pd.to_numeric(work[numeric_col], errors="coerce")

    work["variable"] = (
        work["variable"].astype(str).str.strip().str.lower().str.replace(" ", "", regex=False)
    )

    work = work.dropna(subset=["id_estacion", "ano", "variable", "exposicion_horas", "promedio"])
    work = work[work["exposicion_horas"] == 24]
    work = work[work["variable"].str.contains("pm2", na=False)]

    if work.empty:
        raise ValueError("No hay registros PM2.5 de 24 horas disponibles en la fuente.")

    work["target"] = work["promedio"].apply(label_pm25_category)

    feature_cols = [
        c
        for c in work.columns
        if c
        not in {
            "id_estacion",
            "ano",
            "variable",
            "exposicion_horas",
            "promedio",
            "target",
        }
        and np.issubdtype(work[c].dtype, np.number)
    ]

    if not feature_cols:
        raise ValueError("No se encontraron features numericas para entrenar el modelo.")

    dataset = work[["id_estacion", "ano", "target"] + feature_cols].dropna()
    return dataset, len(raw)


def temporal_split(df: pd.DataFrame, ratio_train: float = 0.8) -> Tuple[pd.DataFrame, pd.DataFrame]:
    years = sorted(df["ano"].unique().tolist())
    if len(years) < 2:
        raise ValueError("No hay suficientes anios para hacer split temporal de entrenamiento/prueba.")

    if len(years) < 4:
        cutoff_year = years[-2]
    else:
        cutoff_idx = max(1, int(len(years) * ratio_train) - 1)
        cutoff_year = years[cutoff_idx]

    train = df[df["ano"] <= cutoff_year].copy()
    test = df[df["ano"] > cutoff_year].copy()

    if train.empty or test.empty:
        raise ValueError("El split temporal produjo conjuntos vacios; revise el dataset.")

    return train, test


def run(url: str, output_json: str | None = None) -> Dict[str, object]:
    dataset, raw_rows = load_and_prepare(url)
    train, test = temporal_split(dataset)

    feature_cols = [c for c in dataset.columns if c not in {"id_estacion", "ano", "target"}]

    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = train["target"].to_numpy(dtype=str)

    x_test = test[feature_cols].to_numpy(dtype=float)
    y_test = test["target"].to_numpy(dtype=str)

    # Baseline
    baseline = MajorityClassBaseline().fit(y_train)
    baseline_pred = baseline.predict(len(y_test))
    baseline_metrics = evaluate(y_test, baseline_pred)

    # Modelo clasico implementado
    model = GaussianNaiveBayesScratch().fit(x_train, y_train)
    model_pred = model.predict(x_test)
    model_metrics = evaluate(y_test, model_pred)

    baseline_conf = confusion_matrix_counts(y_test, baseline_pred)
    model_conf = confusion_matrix_counts(y_test, model_pred)

    class_counts = dataset["target"].value_counts().sort_index()
    class_distribution = {str(k): int(v) for k, v in class_counts.items()}

    print("=== Parte 1: Modelo clasico sobre datos reales ===")
    print(f"Fuente: {url}")
    print(f"Filas crudas: {raw_rows:,}")
    print(f"Muestras finales: {len(dataset):,}")
    print(f"Train: {len(train):,} | Test: {len(test):,}")
    print(f"Features numericas: {len(feature_cols)}")
    print()
    print("Linea base (clase mayoritaria):")
    print(f"  Accuracy:           {baseline_metrics.accuracy:.4f}")
    print(f"  Macro F1:           {baseline_metrics.macro_f1:.4f}")
    print(f"  Balanced Accuracy:  {baseline_metrics.balanced_accuracy:.4f}")
    print()
    print("Gaussian Naive Bayes (from scratch):")
    print(f"  Accuracy:           {model_metrics.accuracy:.4f}")
    print(f"  Macro F1:           {model_metrics.macro_f1:.4f}")
    print(f"  Balanced Accuracy:  {model_metrics.balanced_accuracy:.4f}")
    print()

    delta_f1 = model_metrics.macro_f1 - baseline_metrics.macro_f1
    print(f"Mejora en Macro F1 vs baseline: {delta_f1:+.4f}")

    result: Dict[str, object] = {
        "source_url": url,
        "rows_raw": int(raw_rows),
        "rows_final": int(len(dataset)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "feature_count": int(len(feature_cols)),
        "features": feature_cols,
        "class_distribution": class_distribution,
        "baseline": {
            "model": "majority_class",
            "accuracy": baseline_metrics.accuracy,
            "macro_f1": baseline_metrics.macro_f1,
            "balanced_accuracy": baseline_metrics.balanced_accuracy,
            "confusion_matrix": baseline_conf,
        },
        "gaussian_nb_scratch": {
            "model": "gaussian_nb_scratch",
            "accuracy": model_metrics.accuracy,
            "macro_f1": model_metrics.macro_f1,
            "balanced_accuracy": model_metrics.balanced_accuracy,
            "confusion_matrix": model_conf,
        },
        "improvement_vs_baseline": {
            "delta_accuracy": model_metrics.accuracy - baseline_metrics.accuracy,
            "delta_macro_f1": model_metrics.macro_f1 - baseline_metrics.macro_f1,
            "delta_balanced_accuracy": model_metrics.balanced_accuracy
            - baseline_metrics.balanced_accuracy,
        },
    }

    if output_json:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
        print(f"Resultados guardados en: {output_path}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parte 1: modelo clasico con datos de datos.gov.co")
    parser.add_argument("--url", default=DATA_URL, help="URL CSV de la API de datos abiertos")
    parser.add_argument(
        "--output-json",
        default=None,
        help="Ruta para guardar metricas y matrices de confusion en JSON",
    )
    args = parser.parse_args()
    run(args.url, output_json=args.output_json)
