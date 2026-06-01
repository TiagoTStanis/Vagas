# remoteok tem api publica em json, so GET no /api e filtrar
import requests
import pandas as pd
import re
from datetime import datetime, timezone

BASE_URL = "https://remoteok.com/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
    "Accept": "application/json",
}
COLUNAS = ["title", "company", "location", "job_type", "is_remote",
           "date_posted", "site", "job_url", "description",
           "min_amount", "max_amount", "currency"]

# Mapeamento título → tags Remote OK
TAGS_TI = {
    "infraestrutura": ["devops", "linux", "cloud"],
    "sysadmin":       ["devops", "linux", "sysadmin"],
    "devops":         ["devops"],
    "cloud":          ["cloud", "devops"],
    "redes":          ["devops", "linux"],
    "python":         ["python", "backend"],
    "backend":        ["backend"],
    "segurança":      ["devops", "linux"],
    "suporte":        ["devops", "linux"],
}


def _inferir_tags(titulo: str) -> list[str]:
    titulo_lower = titulo.lower()
    tags = set()
    for palavra, tag_list in TAGS_TI.items():
        if palavra in titulo_lower:
            tags.update(tag_list)
    return list(tags) if tags else ["devops", "backend"]


def buscar(titulo: str, quantidade: int) -> pd.DataFrame:
    print("  [remoteok] buscando via API JSON...")
    tags = _inferir_tags(titulo)
    termos = [t.lower() for t in titulo.split()]
    vagas = []

    for tag in tags:
        if len(vagas) >= quantidade:
            break
        try:
            r = requests.get(BASE_URL, params={"tags": tag},
                             headers=HEADERS, timeout=15)
            r.raise_for_status()
            raw = r.json()
        except Exception as e:
            print(f"  [remoteok] erro ao buscar tag '{tag}': {e}")
            continue

        jobs = [j for j in raw if isinstance(j, dict) and "position" in j]
        for j in jobs:
            conteudo = (j.get("position", "") + " " + " ".join(j.get("tags", []))).lower()
            # Só incluir se houver relevância ao título buscado
            if not any(t in conteudo for t in termos):
                continue
            # Evitar duplicatas
            url = j.get("url") or f"https://remoteok.com/remote-jobs/{j.get('slug','')}"
            if any(v["job_url"] == url for v in vagas):
                continue

            vagas.append({
                "title":       _limpar(j.get("position", "N/A")),
                "company":     _limpar(j.get("company", "N/A")),
                "location":    j.get("location") or "Remote",
                "job_type":    "fulltime",
                "is_remote":   True,
                "date_posted": _formatar_data(j.get("date", "")),
                "site":        "remoteok",
                "job_url":     url,
                "description": _limpar_html(j.get("description", "")),
                "min_amount":  j.get("salary_min") or None,
                "max_amount":  j.get("salary_max") or None,
                "currency":    "USD",
            })

            if len(vagas) >= quantidade:
                break

    print(f"  [remoteok] {len(vagas)} vagas encontradas")
    return pd.DataFrame(vagas[:quantidade])


def _limpar(text: str) -> str:
    return re.sub(r"&amp;|&lt;|&gt;|&quot;|&#39;", lambda m: {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'"
    }[m.group()], text).strip()


def _limpar_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html).strip()


def _formatar_data(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso[:10] if len(iso) >= 10 else iso
