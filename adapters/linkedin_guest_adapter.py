# linkedin tem um endpoint publico que o browser usa quando nao ta logado
# nao precisa de login nem de biblioteca externa
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

BASE_SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml",
}

COLUNAS = ["title", "company", "location", "job_type", "is_remote",
           "date_posted", "site", "job_url", "description",
           "min_amount", "max_amount", "currency"]


def buscar(titulo: str, quantidade: int, horas: int, remoto: bool, location: str = "Brasil") -> pd.DataFrame:
    print("  [linkedin] buscando via jobs-guest (sem login)...")
    vagas = []
    start = 0
    tpr = max(3600, int(horas) * 3600)

    while len(vagas) < quantidade:
        params = {
            "keywords": titulo,
            "location":  location,
            "start":     start,
            "f_TPR":     f"r{tpr}",
            "pageSize":  25,
        }
        if remoto:
            params["f_WT"] = "2"

        try:
            r = requests.get(BASE_SEARCH, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"  [linkedin] erro: {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")
        cards = soup.find_all("li")
        if not cards:
            break

        found_this_page = 0
        for card in cards:
            a = card.find("a", href=re.compile(r"linkedin\.com/jobs/view/"))
            if not a:
                continue

            h3 = card.find("h3")
            h4 = card.find("h4")
            spans = [s.get_text(strip=True) for s in card.find_all("span") if s.get_text(strip=True)]

            title   = h3.get_text(strip=True) if h3 else "N/A"
            company = h4.get_text(strip=True) if h4 else "N/A"
            location = spans[0] if spans else "N/A"
            date_raw = next((s for s in reversed(spans) if _parece_data(s)), "N/A")

            job_url = re.sub(r"\?.*", "", a.get("href", ""))
            is_remote = remoto or any(w in location.lower() for w in ("remoto", "remote", "home office"))

            vagas.append({
                "title":       title,
                "company":     company,
                "location":    location,
                "job_type":    None,
                "is_remote":   is_remote,
                "date_posted": _parse_date(date_raw),
                "site":        "linkedin",
                "job_url":     job_url,
                "description": "",
                "min_amount":  None,
                "max_amount":  None,
                "currency":    "BRL",
            })
            found_this_page += 1
            if len(vagas) >= quantidade:
                break

        if found_this_page == 0:
            break
        start += 25

    print(f"  [linkedin] {len(vagas)} vagas encontradas")
    return pd.DataFrame(vagas[:quantidade], columns=COLUNAS) if vagas else pd.DataFrame(columns=COLUNAS)


def _parece_data(text: str) -> bool:
    kw = ("ago", "hour", "day", "week", "month", "minuto", "hora", "dia", "semana", "mês", "mes")
    return any(k in text.lower() for k in kw)


def _parse_date(text: str) -> str:
    t = text.lower()
    today = datetime.now()
    m = re.search(r"(\d+)", t)
    n = int(m.group(1)) if m else 1
    if any(k in t for k in ("hour", "hora", "minuto", "minute")):
        return (today - timedelta(hours=n)).strftime("%Y-%m-%d")
    if any(k in t for k in ("day", "dia")):
        return (today - timedelta(days=n)).strftime("%Y-%m-%d")
    if any(k in t for k in ("week", "semana")):
        return (today - timedelta(weeks=n)).strftime("%Y-%m-%d")
    if any(k in t for k in ("month", "mês", "mes")):
        return (today - timedelta(days=n * 30)).strftime("%Y-%m-%d")
    return today.strftime("%Y-%m-%d")
