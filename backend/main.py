from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from backend.scripts import kmz_cabos, kmz_dutos, kmz_postes, kmz_poligonos
from dotenv import load_dotenv
import os
import pathlib

load_dotenv()

app = FastAPI()

templates = Jinja2Templates(directory="backend/templates")
app.mount("/static", StaticFiles(directory="backend/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def form_get(request: Request):
    """
    Rota GET para exibir o formulário HTML.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/", response_class=JSONResponse)
async def gerar_kmz(tipo: str = Form(...), codigo_ibge: str = Form(...)):
    try:
        if tipo == "cabo":
            caminhos = kmz_cabos.gerar_kmz(codigo_ibge)
        elif tipo == "duto":
            caminhos = kmz_dutos.gerar_kmz(codigo_ibge)
        elif tipo == "poste":
            caminhos = kmz_postes.gerar_kmz(codigo_ibge)
        elif tipo == "poligono":
            caminhos = kmz_poligonos.gerar_kmz(codigo_ibge)
        else:
            return JSONResponse(status_code=400, content={"error": "Tipo inválido"})

        if isinstance(caminhos, str):
            caminhos = [caminhos]

        arquivos = [os.path.basename(c) for c in caminhos]
        links = [f"/download?file={nome}" for nome in arquivos]

        return {"arquivos": arquivos, "links": links}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Erro interno: {str(e)}"})



@app.get("/download")
async def download_arquivo(file: str):
    """
    Permite download de arquivos KMZ gerados no diretório ~/Downloads.
    Faz validação simples para evitar acesso a arquivos fora do diretório.
    """
    download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    file_path = os.path.normpath(os.path.join(download_dir, file))

    # Segurança: garante que o caminho está dentro da pasta Downloads
    if not file_path.startswith(os.path.abspath(download_dir)):
        raise HTTPException(status_code=403, detail="Acesso negado.")

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    return FileResponse(file_path, filename=file, media_type='application/vnd.google-earth.kmz')
