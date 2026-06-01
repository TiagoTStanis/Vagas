# usa a lib python-jobspy que ja lida com indeed, glassdoor e google jobs
import pandas as pd

COLUNAS = ["title", "company", "location", "job_type", "is_remote",
           "date_posted", "site", "job_url", "description",
           "min_amount", "max_amount", "currency"]

# Sites suportados pelo jobspy
SITES_DISPONIVEIS = ["linkedin", "indeed", "glassdoor", "google"]


def buscar(titulo: str, quantidade: int, horas: int, remoto: bool, sites: list[str], location: str = "Brasil") -> pd.DataFrame:
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("  [jobspy] nao instalado — pip install python-jobspy")
        return pd.DataFrame(columns=COLUNAS)

    sites_jobspy = [s for s in sites if s in SITES_DISPONIVEIS]
    if not sites_jobspy:
        return pd.DataFrame(columns=COLUNAS)

    print(f"  [jobspy] buscando em: {', '.join(sites_jobspy)}")

    try:
        kwargs = dict(
            site_name=sites_jobspy,
            search_term=titulo,
            location=location,
            results_wanted=quantidade,
            hours_old=horas,
            is_remote=remoto,
            country_indeed="Brazil",
            linkedin_fetch_description=True,
        )
        # Google Jobs usa parâmetro próprio e funciona melhor sem location
        if "google" in sites_jobspy:
            kwargs["google_search_term"] = f"{titulo} vagas emprego Brasil"
            kwargs.pop("location", None)

        jobs = scrape_jobs(**kwargs)
        for col in COLUNAS:
            if col not in jobs.columns:
                jobs[col] = None
        return jobs[COLUNAS]
    except Exception as e:
        print(f"  [jobspy] erro: {e}")
        return pd.DataFrame(columns=COLUNAS)
