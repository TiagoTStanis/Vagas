from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import List
import asyncio
import threading
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

app = FastAPI()

GRUPOS_TI = {
    "Alta Chance — Suporte / Helpdesk": [
        "Analista de Suporte N2 Remoto",
        "Analista de Suporte N3 Remoto",
        "Analista de Suporte TI Pleno",
        "Analista de Field Support Pleno",
        "Especialista de Suporte TI Remoto",
    ],
    "Alta Chance — SysAdmin / Windows": [
        "Analista de Infraestrutura Windows",
        "Administrador Active Directory",
        "Analista Azure AD Infraestrutura",
        "SysAdmin Pleno",
        "Analista Endpoint Management Intune",
        "Analista Identidade e Acesso IAM",
    ],
    "Média-Alta — Infraestrutura": [
        "Analista de Infraestrutura TI Pleno",
        "Analista de Infraestrutura Redes",
        "Analista de Datacenter Pleno",
        "Analista NOC Pleno",
    ],
    "Média-Alta — Redes / Segurança": [
        "Analista de Redes Pleno",
        "Analista de Firewall Fortinet",
        "Especialista FortiGate",
        "Analista de Segurança de Redes",
    ],
    "Média-Alta — Cloud Híbrido": [
        "Analista Infraestrutura Cloud",
        "Analista Azure GCP Infraestrutura",
        "Cloud Infrastructure Analyst",
    ],
    "Média — Expansão": [
        "Analista DevOps Jr",
        "Analista de Automação Infraestrutura",
        "Engenheiro de Infraestrutura Jr",
        "Analista Segurança da Informação",
    ],
}

TITULOS_RH = [
    "Gestão de Pessoas",
    "Desenvolvimento Organizacional",
    "Psicóloga Organizacional",
    "Psicóloga Clínica",
    "Psicóloga do Trabalho",
    "Psicóloga Saúde do Trabalho",
    "RH Estratégico",
    "Business Partner RH",
    "HRBP",
    "Coordenadora Desenvolvimento Organizacional",
    "Treinamento e Desenvolvimento",
    "Recrutamento e Seleção",
    "Gerente de RH",
    "Gerente de Recursos Humanos",
    "Saúde do Trabalho",
    "People Partner",
    "Head of People",
    "Coordenadora Psicologia",
    "Analista Sênior Desenvolvimento Organizacional",
    "Coordenadora Treinamento e Desenvolvimento",
    "Gestão de Talentos Sênior",
    "People Analytics Manager",
    "Coordenadora Curso Psicologia",
    "Docente Psicologia",
]

SITES_TI = {
    "linkedin":     "LinkedIn",
    "indeed":       "Indeed",
    "glassdoor":    "Glassdoor",
    "google":       "Google Jobs",
    "gupy":         "Gupy",
    "remotar":      "Remotar",
    "programathor": "Programathor",
    "vagas.com":    "Vagas.com",
    "infojobs":     "InfoJobs",
    "remoteok":     "Remote OK",
    "geekhunter":   "GeekHunter",
}

SITES_RH = {
    "linkedin":  "LinkedIn",
    "indeed":    "Indeed",
    "glassdoor": "Glassdoor",
    "google":    "Google Jobs",
    "gupy":      "Gupy",
    "infojobs":  "InfoJobs",
    "jooble":    "Jooble",
    "vagas.com": "Vagas.com",
}


class BuscarPayload(BaseModel):
    modo: str
    titulo: str
    sites: List[str]
    quantidade: int = 20
    horas: int = 168
    remoto: bool = False
    estado: str = ""
    cidade: str = ""


@app.get("/")
async def index():
    html = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/api/config")
async def config():
    return {
        "grupos_ti": GRUPOS_TI,
        "titulos_rh": TITULOS_RH,
        "sites_ti": SITES_TI,
        "sites_rh": SITES_RH,
    }


@app.post("/api/buscar")
async def buscar_endpoint(payload: BuscarPayload):
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def emit(event: dict):
        asyncio.run_coroutine_threadsafe(queue.put(event), loop)

    def run_search():
        try:
            import pandas as pd
            frames = []

            sites  = payload.sites
            titulo = payload.titulo
            qtd    = payload.quantidade
            horas  = payload.horas
            remoto = payload.remoto
            estado = payload.estado
            cidade = payload.cidade

            loc_parts = [p for p in [cidade, estado] if p]
            location_str = ", ".join(loc_parts + ["Brasil"]) if loc_parts else "Brasil"
            emit({"type": "log", "msg": f'Título: "{titulo}"'})
            emit({"type": "log", "msg": f"Local: {location_str} | últimas {horas}h | remoto: {'sim' if remoto else 'não'}"})

            def _emit_vagas(df, nome):
                if not df.empty:
                    frames.append(df)
                    emit({"type": "log", "msg": f"  {nome}: {len(df)} vagas"})
                    for _, row in df.iterrows():
                        emit({"type": "vaga", "data": _row_to_dict(row)})

            if "linkedin" in sites:
                emit({"type": "log", "msg": "Buscando no LinkedIn..."})
                try:
                    from adapters import linkedin_guest_adapter
                    _emit_vagas(linkedin_guest_adapter.buscar(titulo, qtd, horas, remoto, location_str), "LinkedIn")
                except Exception as e:
                    emit({"type": "log", "msg": f"  Erro LinkedIn: {e}"})

            jobspy_sites = [s for s in sites if s in ("indeed", "glassdoor", "google")]
            if jobspy_sites:
                labels = {"indeed": "Indeed", "glassdoor": "Glassdoor", "google": "Google Jobs"}
                nomes  = ", ".join(labels[s] for s in jobspy_sites)
                emit({"type": "log", "msg": f"Buscando em {nomes}..."})
                try:
                    from adapters import jobspy_adapter
                    _emit_vagas(jobspy_adapter.buscar(titulo, qtd, horas, remoto, jobspy_sites, location_str), nomes)
                except Exception as e:
                    emit({"type": "log", "msg": f"  Erro {nomes}: {e}"})

            if "gupy" in sites:
                emit({"type": "log", "msg": "Buscando no Gupy..."})
                try:
                    from adapters import gupy_adapter
                    _emit_vagas(gupy_adapter.buscar(titulo, qtd, remoto, estado, cidade), "Gupy")
                except Exception as e:
                    emit({"type": "log", "msg": f"  Erro Gupy: {e}"})

            if "remotar" in sites:
                emit({"type": "log", "msg": "Buscando no Remotar..."})
                try:
                    from adapters import remotar_adapter
                    _emit_vagas(remotar_adapter.buscar(titulo, qtd), "Remotar")
                except Exception as e:
                    emit({"type": "log", "msg": f"  Erro Remotar: {e}"})

            if "remoteok" in sites:
                emit({"type": "log", "msg": "Buscando no Remote OK..."})
                try:
                    from adapters import remoteok_adapter
                    _emit_vagas(remoteok_adapter.buscar(titulo, qtd), "Remote OK")
                except Exception as e:
                    emit({"type": "log", "msg": f"  Erro Remote OK: {e}"})

            if "programathor" in sites:
                emit({"type": "log", "msg": "Buscando no Programathor..."})
                try:
                    from adapters import programathor_adapter
                    _emit_vagas(programathor_adapter.buscar(titulo, qtd, remoto), "Programathor")
                except Exception as e:
                    emit({"type": "log", "msg": f"  Erro Programathor: {e}"})

            if "jooble" in sites:
                emit({"type": "log", "msg": "Buscando no Jooble..."})
                try:
                    from adapters import jooble_adapter
                    _emit_vagas(jooble_adapter.buscar(titulo, qtd, remoto, estado, cidade), "Jooble")
                except Exception as e:
                    emit({"type": "log", "msg": f"  Erro Jooble: {e}"})

            if "vagas.com" in sites:
                emit({"type": "log", "msg": "Buscando no Vagas.com..."})
                try:
                    from adapters import vagas_adapter
                    _emit_vagas(vagas_adapter.buscar(titulo, qtd, remoto, cidade), "Vagas.com")
                except Exception as e:
                    emit({"type": "log", "msg": f"  Erro Vagas.com: {e}"})

            if "geekhunter" in sites:
                emit({"type": "log", "msg": "Buscando no GeekHunter..."})
                try:
                    from adapters import geekhunter_requests_adapter
                    _emit_vagas(geekhunter_requests_adapter.buscar(titulo, qtd, remoto, cidade), "GeekHunter")
                except Exception as e:
                    emit({"type": "log", "msg": f"  Erro GeekHunter: {e}"})

            if "infojobs" in sites:
                emit({"type": "log", "msg": "Buscando no InfoJobs..."})
                try:
                    from adapters import infojobs_adapter
                    _emit_vagas(infojobs_adapter.buscar(titulo, qtd, remoto, cidade, estado), "InfoJobs")
                except Exception as e:
                    emit({"type": "log", "msg": f"  Erro InfoJobs: {e}"})

            total = 0
            if frames:
                combined = pd.concat(frames, ignore_index=True)
                if "job_url" in combined.columns:
                    combined = combined.drop_duplicates(subset=["job_url"], keep="first")
                if "title" in combined.columns and "company" in combined.columns:
                    combined = combined.drop_duplicates(subset=["title", "company"], keep="first")
                total = len(combined)

            emit({"type": "done", "total": total})

        except Exception as e:
            emit({"type": "log", "msg": f"Erro geral: {e}"})
            emit({"type": "done", "total": 0})

    thread = threading.Thread(target=run_search, daemon=True)
    thread.start()

    async def generate():
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
                yield json.dumps(event, ensure_ascii=False) + "\n"
                if event.get("type") == "done":
                    break
            except asyncio.TimeoutError:
                yield json.dumps({"type": "done", "total": 0}) + "\n"
                break

    return StreamingResponse(generate(), media_type="application/x-ndjson")


def _row_to_dict(row) -> dict:
    def clean(v):
        if v is None:
            return None
        s = str(v)
        return None if s in ("nan", "None", "") else s

    sal_min = clean(row.get("min_amount"))
    sal_max = clean(row.get("max_amount"))
    salario = None
    if sal_min:
        moeda = clean(row.get("currency")) or "BRL"
        salario = f"{moeda} {sal_min}"
        if sal_max:
            salario += f" – {sal_max}"

    return {
        "titulo":    clean(row.get("title")) or "Sem título",
        "empresa":   clean(row.get("company")) or "N/A",
        "local":     clean(row.get("location")) or "N/A",
        "remoto":    bool(row.get("is_remote")),
        "tipo":      clean(row.get("job_type")),
        "data":      clean(row.get("date_posted")),
        "site":      clean(row.get("site")) or "N/A",
        "url":       clean(row.get("job_url")) or "#",
        "salario":   salario,
        "descricao": (str(row.get("description") or "")[:300] or None),
    }
