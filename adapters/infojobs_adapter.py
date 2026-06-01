# infojobs renderiza as vagas no servidor, pego o html e extraio o que precisa
import requests
import pandas as pd
import re
from bs4 import BeautifulSoup

BASE = "https://www.infojobs.com.br"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
COLUNAS = ["title", "company", "location", "job_type", "is_remote",
           "date_posted", "site", "job_url", "description",
           "min_amount", "max_amount", "currency"]


def buscar(titulo: str, quantidade: int, remoto: bool, cidade: str = "", estado: str = "") -> pd.DataFrame:
    print("  [infojobs] buscando via scraping HTML...")
    slug = titulo.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    url = f"{BASE}/vagas-de-emprego-em-{slug}.aspx"

    vagas = []
    pagina = 1

    while len(vagas) < quantidade:
        params = {}
        if pagina > 1:
            params["page"] = pagina
        if remoto:
            params["workModeId"] = "2"
        if cidade:
            params["municipio"] = cidade
        if estado:
            params["provincia"] = estado

        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"  [infojobs] erro: {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")
        cards = soup.select("div.js_vacancyLoad")
        if not cards:
            break

        for card in cards:
            href      = card.get("data-href", "")
            data_id   = card.get("data-id", "")
            titulo_el = card.select_one("h2.js_vacancyTitle")
            empresa_el = card.select_one("a[href*='empresa-']")
            data_el   = card.select_one("div.js_date")
            local_els = card.select("span.text-nowrap")

            link = href if href.startswith("http") else f"{BASE}{href}"
            titulo_txt = titulo_el.get_text(strip=True) if titulo_el else "N/A"
            empresa_txt = empresa_el.get_text(strip=True) if empresa_el else "N/A"
            data_val = data_el.get("data-value", "") if data_el else ""
            data_fmt = data_val[:10] if data_val else "N/A"

            # Local: textos curtos que parecem cidade/estado
            locais = [s.get_text(strip=True) for s in local_els
                      if len(s.get_text(strip=True)) < 50 and s.get_text(strip=True)]
            local_txt = ", ".join(locais[:2]) if locais else "N/A"
            is_remote = (remoto or
                         "home office" in card.get_text().lower() or
                         "remoto" in card.get_text().lower())

            vagas.append({
                "title":       titulo_txt,
                "company":     empresa_txt,
                "location":    local_txt,
                "job_type":    None,
                "is_remote":   is_remote,
                "date_posted": data_fmt,
                "site":        "infojobs",
                "job_url":     link,
                "description": "",
                "min_amount":  None,
                "max_amount":  None,
                "currency":    "BRL",
            })

            if len(vagas) >= quantidade:
                break

        # Verificar próxima página
        proxima = soup.select_one("a[rel='next'], a[aria-label*='próxima'], [class*='pagination'] a[class*='next']")
        if not proxima:
            break
        pagina += 1

    print(f"  [infojobs] {len(vagas)} vagas encontradas")
    return pd.DataFrame(vagas[:quantidade])
