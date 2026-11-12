from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "valle_aburra_pm25.csv"

# Conjunto principal: nivel del año (promedio) y episodios extremos (percentil 98).
FEATURES = ["promedio", "percentil98"]

# Conjuntos usados en la ablacion (se reportan todos, no solo el ganador).
FEATURES_COMPLETAS = [
    "promedio", "mediana", "percentil98", "maximo", "minimo", "representatividad", "dias_excedencia",
]
ABLACION = {
    "solo_promedio": ["promedio"],
    "promedio_percentil98": FEATURES,
    "promedio_maximo": ["promedio", "maximo"],
    "promedio_mediana": ["promedio", "mediana"],
    "todas_las_features": FEATURES_COMPLETAS,
}

# Categorias sobre el PROMEDIO ANUAL de PM2.5 (ug/m3).
# Los cortes de 12 y 35.4 de la tabla AQI son para promedios de 24 h y con ellos
# ~90% de los promedios anuales caen en una sola clase.
LIMITE_BAJO = 15.0   # meta intermedia 3 de la OMS (guia 2021)
LIMITE_ALTO = 25.0   # limite anual de la norma colombiana (Res. 2254 de 2017)
CLASES = ["baja", "media", "alta"]

PRIMER_ANIO_TEST = 2020  # los años de origen >= este valor se evaluan (walk-forward)


def categoria_pm25(valor: float) -> str:
    if valor <= LIMITE_BAJO:
        return "baja"
    if valor <= LIMITE_ALTO:
        return "media"
    return "alta"


class GaussianNaiveBayesScratch:
    """Gaussian Naive Bayes con NumPy."""

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

        # igual que sklearn: la suavizacion es relativa a la mayor varianza de las features
        epsilon = self.var_smoothing * x.var(axis=0).max()

        theta = np.zeros((len(classes), x.shape[1]))
        sigma = np.zeros((len(classes), x.shape[1]))
        for i, c in enumerate(classes):
            xc = x[y == c]
            theta[i] = xc.mean(axis=0)
            sigma[i] = xc.var(axis=0) + epsilon
        self.theta_, self.sigma_ = theta, sigma
        return self

    def _joint_log_likelihood(self, x: np.ndarray) -> np.ndarray:
        if self.classes_ is None:
            raise RuntimeError("Llama a fit() antes de predecir.")
        jll = np.zeros((x.shape[0], len(self.classes_)))
        for i in range(len(self.classes_)):
            var = self.sigma_[i]
            log_gauss = -0.5 * np.sum(np.log(2.0 * np.pi * var))
            log_gauss = log_gauss - 0.5 * np.sum(((x - self.theta_[i]) ** 2) / var, axis=1)
            jll[:, i] = np.log(self.class_priors_[i]) + log_gauss
        return jll

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        jll = self._joint_log_likelihood(x)
        jll = jll - jll.max(axis=1, keepdims=True)  # estabilidad numerica
        p = np.exp(jll)
        return p / p.sum(axis=1, keepdims=True)

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.classes_[np.argmax(self._joint_log_likelihood(x), axis=1)]


# ----------------------------- metricas -----------------------------

@dataclass
class Metricas:
    accuracy: float
    macro_f1: float
    balanced_accuracy: float


def _prf(y_true: np.ndarray, y_pred: np.ndarray, label: str) -> Tuple[float, float, float]:
    tp = np.sum((y_true == label) & (y_pred == label))
    fp = np.sum((y_true != label) & (y_pred == label))
    fn = np.sum((y_true == label) & (y_pred != label))
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return float(prec), float(rec), float(f1)


def evaluar(y_true: np.ndarray, y_pred: np.ndarray) -> Metricas:
    # el macro se calcula sobre las clases presentes en y_true
    labels = np.unique(y_true)
    f1s = [_prf(y_true, y_pred, l)[2] for l in labels]
    recalls = [_prf(y_true, y_pred, l)[1] for l in labels]
    return Metricas(
        accuracy=float(np.mean(y_true == y_pred)),
        macro_f1=float(np.mean(f1s)),
        balanced_accuracy=float(np.mean(recalls)),
    )


def reporte_por_clase(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Dict[str, float]]:
    out = {}
    for l in CLASES:
        p, r, f = _prf(y_true, y_pred, l)
        out[l] = {"precision": p, "recall": r, "f1": f, "soporte": int(np.sum(y_true == l))}
    return out


def matriz_confusion(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Dict[str, int]]:
    m = {t: {p: 0 for p in CLASES} for t in CLASES}
    for t, p in zip(y_true, y_pred):
        m[str(t)][str(p)] += 1
    return m


# ----------------------------- datos -----------------------------

def cargar_pares(path: Path = DATA_PATH) -> pd.DataFrame:
    """Una fila por (estacion, año t) con la categoria real de t+1.

    Solo se usan años consecutivos: si a una estacion le falta t+1, no hay par.
    """
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}. Ejecuta: python src/preparar_datos.py")
    df = pd.read_csv(path).sort_values(["id_estacion", "anio"]).reset_index(drop=True)
    df["categoria"] = df["promedio"].map(categoria_pm25)

    g = df.groupby("id_estacion")
    df["anio_siguiente"] = g["anio"].shift(-1)
    df["target"] = g["categoria"].shift(-1)

    pares = df[df["anio_siguiente"] == df["anio"] + 1].copy()
    pares = pares.dropna(subset=FEATURES_COMPLETAS + ["target"])
    return pares.reset_index(drop=True)


# ----------------------------- baselines -----------------------------

def baseline_mayoritaria(y_train: np.ndarray, n: int) -> np.ndarray:
    valores, cuentas = np.unique(y_train, return_counts=True)
    return np.array([valores[np.argmax(cuentas)]] * n)


def baseline_persistencia(categoria_actual: np.ndarray) -> np.ndarray:
    """El año siguiente tendra la misma categoria que el actual."""
    return categoria_actual.copy()


# ----------------------------- evaluacion walk-forward -----------------------------

def walk_forward(pares: pd.DataFrame, features: List[str] | None = None) -> Dict[str, object]:
    """Para cada año de origen Y >= PRIMER_ANIO_TEST: entrena con origenes < Y y predice Y."""
    features = FEATURES if features is None else features
    y_true, y_nb, y_may, y_per = [], [], [], []
    por_anio = {}

    for anio in sorted(pares["anio"].unique()):
        if anio < PRIMER_ANIO_TEST:
            continue
        train = pares[pares["anio"] < anio]
        test = pares[pares["anio"] == anio]
        if train.empty or test.empty:
            continue

        x_tr = train[features].to_numpy(float)
        y_tr = train["target"].to_numpy(str)
        x_te = test[features].to_numpy(float)
        yt = test["target"].to_numpy(str)

        nb = GaussianNaiveBayesScratch().fit(x_tr, y_tr).predict(x_te)
        may = baseline_mayoritaria(y_tr, len(yt))
        per = baseline_persistencia(test["categoria"].to_numpy(str))

        y_true.append(yt); y_nb.append(nb); y_may.append(may); y_per.append(per)
        por_anio[int(anio)] = {
            "n_train": int(len(train)),
            "n_test": int(len(test)),
            "acc_nb": float(np.mean(yt == nb)),
            "acc_persistencia": float(np.mean(yt == per)),
        }

    yt = np.concatenate(y_true)
    resultados = {}
    for nombre, pred in [("mayoritaria", np.concatenate(y_may)),
                         ("persistencia", np.concatenate(y_per)),
                         ("gaussian_nb_scratch", np.concatenate(y_nb))]:
        m = evaluar(yt, pred)
        resultados[nombre] = {
            "accuracy": m.accuracy,
            "macro_f1": m.macro_f1,
            "balanced_accuracy": m.balanced_accuracy,
            "por_clase": reporte_por_clase(yt, pred),
            "matriz_confusion": matriz_confusion(yt, pred),
        }
    return {
        "n_test_total": int(len(yt)),
        "distribucion_test": {c: int(np.sum(yt == c)) for c in CLASES},
        "por_anio_origen": por_anio,
        "modelos": resultados,
    }


# ----------------------------- uso desde el agente -----------------------------

def entrenar_modelo(pares: pd.DataFrame | None = None) -> GaussianNaiveBayesScratch:
    pares = cargar_pares() if pares is None else pares
    return GaussianNaiveBayesScratch().fit(pares[FEATURES].to_numpy(float), pares["target"].to_numpy(str))


def predecir_siguiente_anio(id_estacion: int, anio: int | None = None) -> Dict[str, object]:
    """Predice la categoria del año siguiente para una estacion (usa su dato mas reciente)."""
    df = pd.read_csv(DATA_PATH)
    est = df[df["id_estacion"] == id_estacion].sort_values("anio")
    if est.empty:
        raise ValueError(f"Estacion {id_estacion} no encontrada.")
    fila = est[est["anio"] == anio] if anio is not None else est.tail(1)
    if fila.empty:
        raise ValueError(f"La estacion {id_estacion} no tiene datos del año {anio}.")
    fila = fila.iloc[0]
    if fila[FEATURES].isna().any():
        raise ValueError("Faltan indicadores para esa estacion y año.")

    # solo se entrena con pares cuyo año siguiente ya ocurrio antes del año consultado
    pares = cargar_pares()
    pares = pares[pares["anio"] < int(fila["anio"])]
    if pares["target"].nunique() < 2:
        raise ValueError("No hay suficientes datos previos para entrenar.")
    modelo = entrenar_modelo(pares)
    proba = modelo.predict_proba(fila[FEATURES].to_numpy(float).reshape(1, -1))[0]

    return {
        "id_estacion": int(id_estacion),
        "estacion": fila["estacion"],
        "municipio": fila["municipio"],
        "anio_base": int(fila["anio"]),
        "anio_predicho": int(fila["anio"]) + 1,
        "pm25_promedio_base": float(fila["promedio"]),
        "categoria_base": categoria_pm25(float(fila["promedio"])),
        "categoria_predicha": str(modelo.classes_[np.argmax(proba)]),
        "probabilidades": {str(c): float(p) for c, p in zip(modelo.classes_, proba)},
        "nota": "Estimacion estadistica con pocos datos anuales; no es un pronostico diario ni consejo medico.",
    }


# ----------------------------- main -----------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Parte 1: Naive Bayes propio sobre PM2.5 anual")
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args()

    pares = cargar_pares()
    res = walk_forward(pares)

    print("=== Parte 1: categoria de PM2.5 del año siguiente ===")
    print(f"Pares (estacion, t -> t+1): {len(pares)} | estaciones: {pares['id_estacion'].nunique()}")
    print(f"Clases (cortes {LIMITE_BAJO} y {LIMITE_ALTO} ug/m3): {pares['target'].value_counts().to_dict()}")
    print(f"Evaluacion walk-forward desde {PRIMER_ANIO_TEST}: {res['n_test_total']} predicciones")
    print(f"Distribucion real en test: {res['distribucion_test']}\n")
    for nombre, m in res["modelos"].items():
        print(f"{nombre:22s} acc={m['accuracy']:.3f}  macroF1={m['macro_f1']:.3f}  balAcc={m['balanced_accuracy']:.3f}")
    print("\nMatriz de confusion (filas = real, columnas = predicho), Naive Bayes:")
    cm = res["modelos"]["gaussian_nb_scratch"]["matriz_confusion"]
    print(pd.DataFrame(cm).T.to_string())

    ablacion = {}
    print("\nAblacion de features (Naive Bayes, mismo walk-forward):")
    for nombre, feats in ABLACION.items():
        r = walk_forward(pares, feats)["modelos"]["gaussian_nb_scratch"]
        ablacion[nombre] = {"features": feats, "accuracy": r["accuracy"], "macro_f1": r["macro_f1"]}
        print(f"  {nombre:22s} acc={r['accuracy']:.3f}  macroF1={r['macro_f1']:.3f}")

    salida = {
        "fuente": "IDEAM - Calidad del Aire en Colombia (Promedio Anual), datos.gov.co kekd-7v7h",
        "cortes_ug_m3": {"baja_hasta": LIMITE_BAJO, "media_hasta": LIMITE_ALTO},
        "features": FEATURES,
        "n_pares": int(len(pares)),
        "evaluacion": "walk-forward por año de origen",
        "resultados": res,
        "ablacion_features": ablacion,
    }
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nGuardado en {out}")


if __name__ == "__main__":
    main()
