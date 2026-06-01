# programathor renderiza no servidor, paginacao em /jobs/page/{n}
# tem categorias por tecnologia tipo /jobs-python que ajuda a filtrar melhor
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re

BASE = "https://programathor.com.br"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}

COLUNAS = ["title", "company", "location", "job_type", "is_remote",
           "date_posted", "site", "job_url", "description",
           "min_amount", "max_amount", "currency"]

# Mapa de palavras-chave → slug de categoria no Programathor
SLUG_MAP = {
    "infraestrutura": "infraestrutura",
    "suporte":        "suporte-ti",
    "sysadmin":       "infraestrutura",
    "redes":          "infraestrutura",
    "devops":         "devops",
    "cloud":          "cloud",
    "segurança":      "seguranca",
    "firewall":       "infraestrutura",
    "windows":        "infraestrutura",
    "linux":          "linux",
    "python":         "python",
    "backend":        "back-end",
    "frontend":       "front-end",
    "dados":          "data-science",
    "analista":       "infraestrutura",
}


def _inferir_slug(titulo: str) -> str:
    t = titulo.lower()
    for palavra, slug in SLUG_MAP.items():
        if palavra in t:
            return slug
    return ""          # sem slug = usa listagem geral


def buscar(titulo: str, quantidade: int, remoto: bool) -> pd.DataFrame:
    print("  [programathor] buscando via HTML...")
    termos = [t.lower() for t in titulo.split() if len(t) >= 3]
    slug   = _inferir_slug(titulo)
    vagas: list = []
    seen:  set  = set()
    pagina = 1

    while len(vagas) < quantidade:
        # Tenta URL específica por categoria primeiro; cai na geral se falhar
        if slug and pagina == 1:
            url = f"{BASE}/jobs-{slug}/page/1"
        elif slug:
            url = f"{BASE}/jobs-{slug}/page/{pagina}"
        else:
            url = f"{BASE}/jobs/page/{pagina}"

        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 404 and slug:
                # Slug inválido — cai na listagem geral
                slug = ""
                url  = f"{BASE}/jobs/page/{pagina}"
                r    = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"  [programathor] erro pág {pagina}: {e}")
            break

        soup  = BeautifulSoup(r.text, "lxml")
        cards = soup.find_all("a", href=re.compile(r"^/jobs/\d+"))

        if not cards:
            break

        found_page = 0
        for card in cards:
            href = card.get("href", "").split("?")[0]
            if href in seen:
                continue
            seen.add(href)

            text  = card.get_text(separator=" ", strip=True)
            tlow  = text.lower()

            # Filtro por relevância ao título pesquisado
            if termos and not any(t in tlow for t in termos):
                continue

            h3     = card.find("h3")
            title  = h3.get_text(strip=True) if h3 else href.split("/")[-1].replace("-", " ").title()

            # Empresa: texto logo após o título (segundo bloco de texto significativo)
            all_texts = [s.strip() for s in card.stripped_strings if s.strip()]
            company   = all_texts[1] if len(all_texts) > 1 else "N/A"

            # Remoto / local
            is_remote = remoto or any(w in tlow for w in ("remoto", "remote", "home office"))
            if "híbrido" in tlow:
                location = "Híbrido"
            elif is_remote:
                location = "Remoto"
            else:
                # Tenta extrair cidade do texto
                cidade_m = re.search(
                    r"(são paulo|rio de janeiro|belo horizonte|curitiba|porto alegre"
                    r"|campinas|florianópolis|brasília|recife|fortaleza|salvador)",
                    tlow,
                )
                location = cidade_m.group(0).title() if cidade_m else "Brasil"

            # Contrato (CLT / PJ / Estágio)
            job_type = None
            for ct in ("CLT", "PJ", "Estágio", "Freelancer"):
                if ct.lower() in tlow:
                    job_type = ct
                    break

            # Tags de skills como descrição
            tags = [sp.get_text(strip=True) for sp in card.find_all("span") if sp.get_text(strip=True)]
            desc = ", ".join(tags[:6]) if tags else ""

            # Data: marca "NOVA" se nova
            is_new = bool(card.find(string=re.compile(r"NOVA", re.I)))
            date_str = "recente" if is_new else "N/A"

            vagas.append({
                "title":       title,
                "company":     company,
                "location":    location,
                "job_type":    job_type,
                "is_remote":   is_remote,
                "date_posted": date_str,
                "site":        "programathor",
                "job_url":     BASE + href,
                "description": desc,
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

    print(f"  [programathor] {len(vagas)} vagas encontradas")
    return pd.DataFrame(vagas[:quantidade], columns=COLUNAS) if vagas else pd.DataFrame(columns=COLUNAS)
