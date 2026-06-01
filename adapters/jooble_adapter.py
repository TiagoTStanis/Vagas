# jooble agrega vagas de varios sites, html renderizado no servidor
# os links sao redirects deles mas funcionam normal
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import unicodedata
from urllib.parse import quote

BASE = "https://br.jooble.org"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}

COLUNAS = ["title", "company", "location", "job_type", "is_remote",
           "date_posted", "site", "job_url", "description",
           "min_amount", "max_amount", "currency"]

DATE_RE   = re.compile(r"há\s+(\d+)\s+(minuto|hora|dia|semana|mês|mes)s?\s+atrás", re.I)
SALARY_RE = re.compile(r"R\$\s?[\d\.,]+")


def _slugify(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_str.lower()).strip("-")
    return slug


def buscar(titulo: str, quantidade: int, remoto: bool, estado: str = "", cidade: str = "") -> pd.DataFrame:
    print("  [jooble] buscando via HTML...")
    slug  = _slugify(titulo)
    vagas = []
    pagina = 1
    seen: set = set()

    while len(vagas) < quantidade:
        url = f"{BASE}/vagas-de-emprego-{slug}"
        params: dict = {}
        if pagina > 1:
            params["p"] = pagina
        if cidade:
            params["l"] = cidade + (f", {estado}" if estado else "")
        elif estado:
            params["l"] = estado
        if remoto:
            params["remoteType"] = "1"

        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"  [jooble] erro pág {pagina}: {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")

        # Cada vaga é um <li> contendo um <a href="/away/...">
        items = soup.find_all("li")
        found_page = 0

        for li in items:
            link = li.find("a", href=re.compile(r"/away/\d+"))
            if not link:
                continue

            href = link.get("href", "")
            # Limpa parâmetros de tracking — mantém só o ID
            job_id_m = re.search(r"/away/(\d+)", href)
            if not job_id_m:
                continue
            clean_url = f"{BASE}/away/{job_id_m.group(1)}"

            if clean_url in seen:
                continue
            seen.add(clean_url)

            text = li.get_text(separator=" ", strip=True)

            # Título: texto do link
            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            # Empresa: logo tem classe dteCompanyLogo; empresa fica após o link
            logo = li.find("img", class_=re.compile(r"[Cc]ompany[Ll]ogo|Logo"))
            company_el = logo.find_next_sibling(string=True) if logo else None
            if company_el:
                company = company_el.strip()
            else:
                # Fallback: segundo bloco de texto do li
                all_texts = [s.strip() for s in li.stripped_strings if s.strip()]
                company = all_texts[1] if len(all_texts) > 1 else "N/A"

            # Localização
            loc_m = re.search(r"([A-ZÀ-Ú][a-zà-ú\s]+),\s*([A-Z]{2})", text)
            location = loc_m.group(0) if loc_m else (cidade or estado or "Brasil")
            is_remote = remoto or any(w in text.lower() for w in ("remoto", "home office", "remote"))
            if is_remote:
                location = "Remoto" if not loc_m else location + " (Remoto)"

            # Data
            date_m = DATE_RE.search(text)
            date_str = date_m.group(0) if date_m else "N/A"

            # Salário
            sal_m = SALARY_RE.search(text)
            sal_str = sal_m.group(0) if sal_m else None

            vagas.append({
                "title":       title,
                "company":     company,
                "location":    location,
                "job_type":    None,
                "is_remote":   is_remote,
                "date_posted": date_str,
                "site":        "jooble",
                "job_url":     clean_url,
                "description": "",
                "min_amount":  None,
                "max_amount":  None,
                "currency":    "BRL",
            })
            found_page += 1

            if len(vagas) >= quantidade:
                break

        if found_page == 0:
            break
        pagina += 1

    print(f"  [jooble] {len(vagas)} vagas encontradas")
    return pd.DataFrame(vagas[:quantidade], columns=COLUNAS) if vagas else pd.DataFrame(columns=COLUNAS)
