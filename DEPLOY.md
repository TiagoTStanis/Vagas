# Deploy — Buscador de Vagas Web

## Render.com (recomendado — grátis)

1. Crie uma conta em https://render.com
2. "New Web Service" → conecte o repositório Git
3. Configure:
   - **Root Directory:** `web`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Clique em "Deploy"

> O app dorme após 15 min de inatividade no plano free. Primeira requisição pode demorar ~30s para "acordar".

---

## Rodar localmente

```powershell
cd web
pip install -r requirements.txt
uvicorn main:app --reload --port 8766
# Abrir: http://localhost:8766
```

---

## Notas

- GeekHunter (Playwright) não está disponível nesta versão web — requer navegador headless.
- LinkedIn e Indeed usam `python-jobspy` que pode ser bloqueado em alguns momentos; os demais adapters (Gupy API, Remotar API, Remote OK API, Vagas.com scraping, InfoJobs scraping) são mais estáveis.
