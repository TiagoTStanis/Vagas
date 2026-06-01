# remotar tem api aberta, so chamar o endpoint e filtrar pelo titulo
import requests
import pandas as pd
from datetime import datetime, timezone

BASE_URL = "https://api.remotar.com.br/timeline"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
    "Accept": "application/json",
    "Referer": "https://remotar.com.br/",
    "Origin": "https://remotar.com.br",
}
COLUNAS = ["title", "company", "location", "job_type", "is_remote",
           "date_posted", "site", "job_url", "description",
           "min_amount", "max_amount", "currency"]


def buscar(titulo: str, quantidade: int) -> pd.DataFrame:
    print("  [remotar] buscando via API REST...")
    vagas = []
    pagina = 1
    termos = [t.lower() for t in titulo.split()]
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    while len(vagas) < quantidade:
        params = {
            "page":          pagina,
            "firstFetchTs":  timestamp,
        }
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            print(f"  [remotar] erro: {e}")
            break

        jobs = payload.get("data", [])
        if not jobs:
            break

        for j in jobs:
            titulo_vaga = j.get("title", "")
            desc = j.get("description", "")
            conteudo = (titulo_vaga + " " + desc).lower()

            # Filtrar por relevância ao título pesquisado
            if not any(t in conteudo for t in termos):
                continue

            company_obj = j.get("company") or {}
            empresa = (
                j.get("companyDisplayName") or
                company_obj.get("name") or
                company_obj.get("displayName") or
                "N/A"
            )

            link = j.get("externalLink") or ""
            if not link:
                job_id = j.get("id", "")
                link = f"https://remotar.com.br/job/{job_id}" if job_id else "N/A"

            sal = j.get("jobSalary") or {}
            sal_min = sal.get("minValue") or sal.get("min")
            sal_max = sal.get("maxValue") or sal.get("max")

            vagas.append({
                "title":       titulo_vaga or "N/A",
                "company":     empresa,
                "location":    _formatar_local(j),
                "job_type":    j.get("type"),
                "is_remote":   True,
                "date_posted": str(j.get("createdAt", "N/A"))[:10],
                "site":        "remotar",
                "job_url":     link,
                "description": _limpar_html(desc),
                "min_amount":  sal_min,
                "max_amount":  sal_max,
                "currency":    "BRL",
            })

        meta = payload.get("meta", {})
        total_paginas = meta.get("lastPage") or meta.get("totalPages", 1)
        if pagina >= total_paginas:
            break
        pagina += 1

    print(f"  [remotar] {len(vagas)} vagas encontradas")
    return pd.DataFrame(vagas[:quantidade])


def _formatar_local(j: dict) -> str:
    partes = [j.get("city", ""), j.get("state", "")]
    pais   = (j.get("country") or {}).get("name", "")
    partes.append(pais)
    return ", ".join(p for p in partes if p) or "Brasil (Remoto)"


def _limpar_html(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", " ", html).strip()
