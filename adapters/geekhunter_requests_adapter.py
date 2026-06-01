# geekhunter usa next.js mas renderiza no servidor
# consegui pegar as vagas so com requests, sem precisar de playwright
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re

BASE = "https://www.geekhunter.com.br"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

COLUNAS = ["title", "company", "location", "job_type", "is_remote",
           "date_posted", "site", "job_url", "description",
           "min_amount", "max_amount", "currency"]

JOB_LINK_RE = re.compile(r"^/[^/]+/jobs/[^/]+")
SALARY_RE    = re.compile(r"R\$\s?[\d\.,]+(?:\s*[–\-]\s*R\$\s?[\d\.,]+)?")
DATE_RE      = re.compile(r"(?:há|publicada há)\s+\d+\s+(?:minuto|hora|dia|semana|mês)s?", re.I)
CIDADE_RE    = re.compile(
    r"(são paulo|rio de janeiro|belo horizonte|curitiba|porto alegre|campinas"
    r"|recife|fortaleza|salvador|manaus|brasília|goiânia|florianópolis)",
    re.I,
)


def buscar(titulo: str, quantidade: int, remoto: bool, cidade: str = "") -> pd.DataFrame:
    print("  [geekhunter] buscando via HTML (sem Playwright)...")
    vagas = []
    pagina = 1
    termos = [t.lower() for t in titulo.split() if len(t) >= 3]
    seen_urls: set = set()

    while len(vagas) < quantidade:
        params: dict = {"q": titulo, "page": pagina}
        if remoto:
            params["workModel"] = "remote"
        if cidade:
            params["city"] = cidade

        try:
            r = requests.get(f"{BASE}/vagas", params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"  [geekhunter] erro página {pagina}: {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")

        # Coleta todos os <a> cujo href segue o padrão /empresa/jobs/slug
        links = soup.find_all("a", href=JOB_LINK_RE)
        if not links:
            break

        added_this_page = 0
        for a in links:
            href = a.get("href", "").split("?")[0]
            full_url = BASE + href
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            text = a.get_text(separator=" ", strip=True)

            # Relevância: pelo menos um termo do título deve aparecer
            if termos and not any(t in text.lower() for t in termos):
                continue

            # Empresa: primeiro segmento do path após /
            parts = href.strip("/").split("/")
            company_slug = parts[0] if parts else "N/A"
            company = company_slug.replace("-", " ").title()

            # Título: primeira linha com conteúdo significativo
            lines = [ln.strip() for ln in text.split()[:8]]
            title_candidate = " ".join(lines) if lines else href.split("/")[-1].replace("-", " ").title()

            # Localização
            cidade_m = CIDADE_RE.search(text)
            if cidade_m:
                location = cidade_m.group(0).title()
            elif any(w in text.lower() for w in ("remoto", "remote", "home office")):
                location = "Remoto"
            else:
                location = "Brasil"

            is_remote = remoto or any(w in text.lower() for w in ("remoto", "remote", "home office"))

            # Data
            date_m = DATE_RE.search(text)
            date_str = date_m.group(0) if date_m else "N/A"

            # Salário (descrição)
            sal_m = SALARY_RE.search(text)
            sal_str = sal_m.group(0) if sal_m else ""

            vagas.append({
                "title":       title_candidate,
                "company":     company,
                "location":    location,
                "job_type":    None,
                "is_remote":   is_remote,
                "date_posted": date_str,
                "site":        "geekhunter",
                "job_url":     full_url,
                "description": sal_str,
                "min_amount":  None,
                "max_amount":  None,
                "currency":    "BRL",
            })
            added_this_page += 1

            if len(vagas) >= quantidade:
                break

        if added_this_page == 0:
            break
        pagina += 1

    print(f"  [geekhunter] {len(vagas)} vagas encontradas")
    return pd.DataFrame(vagas[:quantidade], columns=COLUNAS) if vagas else pd.DataFrame(columns=COLUNAS)
