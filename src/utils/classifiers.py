from __future__ import annotations


CRIME_CATEGORIES = {
    "violencia": "Violencia",
    "roubo_furto": "Roubo/Furto",
    "trafico_armas": "Trafico/Armas",
    "outros": "Outros",
}

_VIOLENCE_KEYWORDS = (
    "homicidio",
    "homicídio",
    "lesao corporal",
    "lesão corporal",
    "morte",
    "latrocinio",
    "latrocínio",
    "corpo de delito",
)

_ROBBERY_KEYWORDS = (
    "roubo",
    "furto",
    "receptacao",
    "receptação",
    "extorsao",
    "extorsão",
    "estelionato",
    "apropriação indebita",
    "apropriação indevida",
    "dano ao patrimonio",
)

_DRUG_WEAPON_KEYWORDS = (
    "droga",
    "entorpecente",
    "arma",
    "porte ilegal",
    "porte irregular",
    "disparo",
    "munição",
    "municao",
    "explosivo",
)


def classify_crime(natureza: str) -> str:
    """Classify a crime description into a severity category.

    Returns one of: Violencia, Roubo/Furto, Trafico/Armas, Outros
    """
    if not natureza or natureza == "nan":
        return "Outros"

    lower = natureza.lower()

    for kw in _VIOLENCE_KEYWORDS:
        if kw in lower:
            return "Violencia"

    for kw in _ROBBERY_KEYWORDS:
        if kw in lower:
            return "Roubo/Furto"

    for kw in _DRUG_WEAPON_KEYWORDS:
        if kw in lower:
            return "Trafico/Armas"

    return "Outros"


def classify_crime_batch(naturezas: list[str]) -> list[str]:
    """Classify a batch of crime descriptions."""
    return [classify_crime(n) for n in naturezas]
