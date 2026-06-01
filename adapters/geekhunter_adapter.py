"""
Adapter para GeekHunter via Playwright.
Usa DOM renderizado — links no padrão /company/jobs/job-slug.
Requer: pip install playwright && playwright install chromium
"""
import os
import sys
import pandas as pd
import re

# Quando empacotado pelo PyInstaller, o Playwright procura os browsers
# na pasta _MEI* temporária. Aqui forçamos o caminho real de instalação.
if getattr(sys, 'frozen', False):
    _browsers_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _browsers_path

COLUNAS = ["title", "company", "location", "job_type", "is_remote",
           "date_posted", "site", "job_url", "description",
           "min_amount", "max_amount", "currency"]
BASE = "https://www.geekhunter.com.br"


def buscar(titulo: str, quantidade: int, remoto: bool) -> pd.DataFrame:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [geekhunter] Playwright nao instalado — pip install playwright && playwright install chromium")
        return pd.DataFrame(columns=COLUNAS)

    print("  [geekhunter] buscando via Playwright (DOM)...")
    vagas = []
    termos = [t.lower() for t in titulo.split()]
    pagina = 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9"})

        while len(vagas) < quantidade:
            params = f"q={titulo.replace(' ', '+')}&page={pagina}"
            if remoto:
                params += "&remoteWork=true"

            page.goto(f"{BASE}/vagas?{params}", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            # Coletar todos os links de vagas (/company/jobs/slug)
            links = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href*="/jobs/"]'))
                    .filter(a => !a.href.includes('/vagas') && a.innerText.trim().length > 5)
                    .map(a => ({
                        href: a.href,
                        text: a.innerText.trim()
                    }));
            }""")

            if not links:
                break

            for item in links:
                href = item["href"]
                texto = item["text"]
                linhas = [l.strip() for l in texto.split("\n") if l.strip()]
                if not linhas:
                    continue

                titulo_vaga = linhas[0]
                conteudo = texto.lower()

                # Filtrar por relevância
                if not any(t in conteudo for t in termos):
                    continue

                # Extrair empresa do slug da URL: /empresa/jobs/slug
                empresa = _empresa_da_url(href)
                is_remote = remoto or "remoto" in conteudo or "remote" in conteudo or "home office" in conteudo
                local = _extrair_local(linhas)
                data = _extrair_data(linhas)

                vagas.append({
                    "title":       titulo_vaga,
                    "company":     empresa,
                    "location":    local,
                    "job_type":    None,
                    "is_remote":   is_remote,
                    "date_posted": data,
                    "site":        "geekhunter",
                    "job_url":     href,
                    "description": "",
                    "min_amount":  None,
                    "max_amount":  None,
                    "currency":    "BRL",
                })

                if len(vagas) >= quantidade:
                    break

            # Verificar se há próxima página
            has_next = page.query_selector("a[aria-label*='próxima'], a[aria-label*='next'], button[aria-label*='próxima']")
            if not has_next or len(vagas) >= quantidade:
                break
            pagina += 1

        browser.close()

    print(f"  [geekhunter] {len(vagas)} vagas encontradas")
    return pd.DataFrame(vagas[:quantidade])


def _empresa_da_url(href: str) -> str:
    # Padrão: https://www.geekhunter.com.br/{empresa}/jobs/{slug}
    m = re.search(r"geekhunter\.com\.br/([^/]+)/jobs/", href)
    if m:
        slug = m.group(1)
        return slug.replace("-", " ").title()
    return "N/A"


def _extrair_local(linhas: list[str]) -> str:
    for linha in linhas[1:]:
        linha_lower = linha.lower()
        if any(w in linha_lower for w in ["são paulo", "rio de", "belo horizonte", "curitiba",
                                           "porto alegre", "brasília", "campinas", "sp", "rj", "mg"]):
            return linha
    return "N/A"


def _extrair_data(linhas: list[str]) -> str:
    for linha in linhas:
        if "publicada" in linha.lower() or "há" in linha.lower():
            return linha
    return "N/A"
