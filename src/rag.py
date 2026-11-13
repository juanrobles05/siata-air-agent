from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, List

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs_rag"

STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "los", "las", "un", "una", "que", "por", "con", "para", "del",
    "al", "es", "se", "su", "sus", "lo", "como", "o", "si", "no", "mas", "me", "mi", "cual", "cuales",
    "qué", "que", "hay", "ser", "son", "este", "esta", "esto", "le", "les", "ya", "pero",
}


def _sin_tildes(texto: str) -> str:
    norm = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in norm if not unicodedata.combining(c))


def tokenizar(texto: str) -> List[str]:
    texto = _sin_tildes(texto.lower())
    tokens = []
    for t in re.findall(r"[a-z0-9]+(?:[.,][0-9]+)?", texto):
        if t in STOPWORDS:
            continue
        # recorte simple de plurales para que "estaciones" coincida con "estacion"
        if len(t) > 4 and t.endswith("es"):
            t = t[:-2]
        elif len(t) > 3 and t.endswith("s"):
            t = t[:-1]
        tokens.append(t)
    return tokens


def _cargar_fragmentos() -> List[Dict[str, str]]:
    fragmentos = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        texto = path.read_text(encoding="utf-8")
        lineas = texto.splitlines()
        titulo = lineas[0].lstrip("# ").strip() if lineas else path.stem
        fuente = url = ""
        for l in lineas[:8]:
            if l.startswith("Fuente:"):
                fuente = l[len("Fuente:"):].strip()
            elif l.startswith("URL:"):
                url = l[len("URL:"):].strip()
        for bloque in re.split(r"\n(?=## )", "\n".join(lineas[1:])):
            bloque = bloque.strip()
            if not bloque.startswith("## "):
                continue
            seccion, _, cuerpo = bloque.partition("\n")
            fragmentos.append({
                "doc_id": path.stem,
                "titulo": titulo,
                "seccion": seccion.lstrip("# ").strip(),
                "fuente": fuente,
                "url": url,
                "texto": cuerpo.strip(),
            })
    return fragmentos


class BM25:
    def __init__(self, fragmentos: List[Dict[str, str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.fragmentos = fragmentos
        self.k1, self.b = k1, b
        # el titulo y la seccion cuentan como parte del texto del fragmento
        self.docs = [tokenizar(f"{f['titulo']} {f['seccion']} {f['texto']}") for f in fragmentos]
        self.largos = [len(d) for d in self.docs]
        self.prom = sum(self.largos) / max(len(self.docs), 1)
        df = Counter()
        for d in self.docs:
            df.update(set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.tf = [Counter(d) for d in self.docs]

    def buscar(self, consulta: str, k: int = 3) -> List[Dict[str, object]]:
        q = tokenizar(consulta)
        puntajes = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for t in q:
                if t in tf:
                    f = tf[t]
                    denom = f + self.k1 * (1 - self.b + self.b * self.largos[i] / self.prom)
                    s += self.idf[t] * f * (self.k1 + 1) / denom
            puntajes.append(s)
        orden = sorted(range(len(puntajes)), key=lambda i: puntajes[i], reverse=True)[:k]
        return [
            {**self.fragmentos[i], "puntaje": round(puntajes[i], 3)}
            for i in orden if puntajes[i] > 0
        ]


_indice: BM25 | None = None


def obtener_indice() -> BM25:
    global _indice
    if _indice is None:
        fragmentos = _cargar_fragmentos()
        if not fragmentos:
            raise FileNotFoundError(f"No hay documentos en {DOCS_DIR}")
        _indice = BM25(fragmentos)
    return _indice


def buscar(consulta: str, k: int = 3) -> List[Dict[str, object]]:
    return obtener_indice().buscar(consulta, k)
