# vagas.com renderiza o html no servidor, da pra pegar com requests normal
import requests
import pandas as pd
import re
from bs4 import BeautifulSoup

BASE = "https://www.vagas.com.br"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
COLUNAS = ["title", "company", "location", "job_type", "is_remote",
           "date_posted", "site", "job_url", "description",
           "min_amount", "max_amount", "currency"]


def buscar(titulo: str, quantidade: int, remoto: bool, cidade: str = "") -> pd.DataFrame:
    print("  [vagas.com] buscando via scraping HTML...")
    slug = titulo.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    url = f"{BASE}/vagas-de-{slug}"
    if cidade:
        cidade_slug = re.sub(r"[^a-z0-9\-]", "", cidade.lower().replace(" ", "-"))
        url = f"{BASE}/vagas-de-{slug}-em-{cidade_slug}"

    vagas = []
    pagina = 1

    while len(vagas) < quantidade:
        params = {}
        if pagina > 1:
            params["p"] = pagina

        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"  [vagas.com] erro: {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")
        cards = soup.select("li.vaga")
        if not cards:
            break

        for card in cards:
            link_el   = card.select_one("a.link-detalhes-vaga")
            empresa_el = card.select_one("span.emprVaga")
            local_el  = card.select_one("div.vaga-local")
            nivel_el  = card.select_one("span.nivelVaga")
            data_el   = card.select_one("span.data-publicacao")
            desc_el   = card.select_one("div.detalhes p")

            if not link_el:
                continue

            href = link_el.get("href", "")
            link = href if href.startswith("http") else f"{BASE}{href}"
            local_txt = local_el.get_text(strip=True) if local_el else "N/A"
            is_remote = remoto or "remoto" in local_txt.lower() or "home office" in local_txt.lower()

            vagas.append({
                "title":       link_el.get_text(strip=True),
                "company":     empresa_el.get_text(strip=True) if empresa_el else "N/A",
                "location":    local_txt,
                "job_type":    nivel_el.get_text(strip=True) if nivel_el else None,
                "is_remote":   is_remote,
                "date_posted": data_el.get_text(strip=True) if data_el else "N/A",
                "site":        "vagas.com",
                "job_url":     link,
                "description": desc_el.get_text(strip=True)[:500] if desc_el else "",
                "min_amount":  None,
                "max_amount":  None,
                "currency":    "BRL",
            })

            if len(vagas) >= quantidade:
                break

        # Verificar paginação
        proxima = soup.select_one("a[rel='next'], a.proxima, [class*='next-page']")
        if not proxima:
            break
        pagina += 1

    # Se filtro remoto ativo, filtrar resultados
    if remoto and vagas:
        vagas = [v for v in vagas if v["is_remote"]]

    print(f"  [vagas.com] {len(vagas)} vagas encontradas")
    return pd.DataFrame(vagas[:quantidade])
