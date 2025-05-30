from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from backend.gerar_kmz import gerar_kmz_mock

app = FastAPI()

# Liberar acesso ao frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ou especifique seu IP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "API funcionando!"}

@app.get("/generate_kmz")
def generate_kmz(ibge: str = Query(...), tipo: str = Query(...)):
    try:
        path = gerar_kmz_mock(ibge, tipo)
        return FileResponse(
            path,
            media_type="application/vnd.google-earth.kmz",
            filename=path.name
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
