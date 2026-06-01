# gupy tem uma api interna que o proprio site usa
# da pra chamar direto sem precisar de login
import requests
import pandas as pd

BASE_URL = "https://employability-portal.gupy.io/api/v1/jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
    "Accept": "application/json",
    "Referer": "https://portal.gupy.io/",
}
COLUNAS = ["title", "company", "location", "job_type", "is_remote",
           "date_posted", "site", "job_url", "description",
           "min_amount", "max_amount", "currency"]


def buscar(titulo: str, quantidade: int, remoto: bool, estado: str = "", cidade: str = "") -> pd.DataFrame:
    print("  [gupy] buscando via API REST...")
    vagas = []
    offset = 0
    limite = min(quantidade, 10)

    while len(vagas) < quantidade:
        params = {
            "jobName":  titulo,
            "limit":    limite,
            "offset":   offset,
        }
        if remoto:
            params["workplaceType"] = "remote"
        if cidade:
            params["city"] = cidade
        if estado:
            params["state"] = estado

        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:
            print(f"  [gupy] erro: {e}")
            break

        jobs = payload.get("data", [])
        if not jobs:
            break

        for j in jobs:
            local_parts = [j.get("city", ""), j.get("state", ""), j.get("country", "")]
            local = ", ".join(p for p in local_parts if p) or "N/A"

            vagas.append({
                "title":       j.get("name", "N/A"),
                "company":     j.get("careerPageName", "N/A"),
                "location":    local,
                "job_type":    j.get("type"),
                "is_remote":   j.get("workplaceType") == "remote" or j.get("isRemoteWork", False),
                "date_posted": str(j.get("publishedDate", "N/A"))[:10],
                "site":        "gupy",
                "job_url":     j.get("jobUrl", "N/A"),
                "description": j.get("description", ""),
                "min_amount":  None,
                "max_amount":  None,
                "currency":    "BRL",
            })

        pag = payload.get("pagination", {})
        total = pag.get("total", 0)
        offset += limite
        if offset >= total:
            break

    print(f"  [gupy] {len(vagas)} vagas encontradas")
    return pd.DataFrame(vagas[:quantidade])
