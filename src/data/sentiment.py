from __future__ import annotations

import re
from urllib.request import urlopen
from xml.etree import ElementTree

from loguru import logger

POSITIVE_KEYWORDS = [
    "seguranca", "seguro", "melhoria", "investimento", "iluminacao",
    "reducao", "queda", "diminuiu", "menos crimes", "paz", "protecao",
    "cameras", "patrulha", "policiamento", "acao", "programa",
    "seguranca publica", "qualidade de vida", "revitalizacao",
]

NEGATIVE_KEYWORDS = [
    "crime", "assassinato", "homicidio", "roubo", "furto", "latrocinio",
    "violencia", "agressao", "estupro", "sequestro", "tráfico",
    "tiroteio", "mortes", "vitimas", "perigo", "inseguranca",
    "descaso", "falta", "ausencia", "abandono", "negligencia",
    "escalada", "aumento", "surto", "crise", "alerta",
]

SP_NEWS_RSS = [
    "https://feeds.folha.uol.com.br/cotidiano/rss091.xml",
    "https://pox.globo.com/rss/g1/",
]


def _simple_sentiment(text: str) -> dict:
    text_lower = text.lower()
    pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)

    total = pos + neg
    if total == 0:
        score = 0.0
    else:
        score = (pos - neg) / total

    if score > 0.2:
        label = "positivo"
    elif score < -0.2:
        label = "negativo"
    else:
        label = "neutro"

    return {"score": round(score, 3), "label": label, "pos": pos, "neg": neg}


def fetch_rss_headlines(
    urls: list[str] | None = None,
    max_per_feed: int = 30,
) -> list[dict]:
    if urls is None:
        urls = SP_NEWS_RSS

    headlines: list[dict] = []
    for url in urls:
        try:
            with urlopen(url, timeout=15) as resp:
                xml_data = resp.read()
            try:
                root = ElementTree.fromstring(xml_data)
            except ElementTree.ParseError:
                cleaned = xml_data.decode("utf-8", errors="ignore")
                cleaned = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;)", "&amp;", cleaned)
                root = ElementTree.fromstring(cleaned.encode("utf-8"))
            items = root.findall(".//item")
            for item in items[:max_per_feed]:
                title_el = item.find("title")
                desc_el = item.find("description")
                pub_el = item.find("pubDate")
                title = title_el.text if title_el is not None else ""
                desc = desc_el.text if desc_el is not None else ""
                pub = pub_el.text if pub_el is not None else ""
                full_text = f"{title} {desc}".strip()
                if full_text:
                    sentiment = _simple_sentiment(full_text)
                    headlines.append({
                        "title": re.sub(r"<[^>]+>", "", title).strip(),
                        "source": url.split("/")[2],
                        "published": pub,
                        "sentiment_score": sentiment["score"],
                        "sentiment_label": sentiment["label"],
                        "positive_hits": sentiment["pos"],
                        "negative_hits": sentiment["neg"],
                    })
            logger.info("RSS {}: {} headlines", url.split("/")[2], len(items))
        except Exception as e:
            logger.warning("Erro ao buscar RSS {}: {}", url, e)

    return headlines


def compute_sentiment_summary(headlines: list[dict]) -> dict:
    if not headlines:
        return {"total": 0, "avg_score": 0, "labels": {}}

    scores = [h["sentiment_score"] for h in headlines]
    labels = {}
    for h in headlines:
        lbl = h["sentiment_label"]
        labels[lbl] = labels.get(lbl, 0) + 1

    return {
        "total": len(headlines),
        "avg_score": round(sum(scores) / len(scores), 3),
        "labels": labels,
        "most_negative": sorted(headlines, key=lambda x: x["sentiment_score"])[:5],
        "most_positive": sorted(headlines, key=lambda x: -x["sentiment_score"])[:5],
    }
