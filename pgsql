apk-gerador-kmz-web/
├── backend/
│   ├── main.py                # FastAPI app + rotas
│   ├── scripts/
│   │   ├── kmz_cabos.py      # Função gerar KMZ para cabos
│   │   ├── kmz_dutos.py      # Função gerar KMZ para dutos
│   │   ├── kmz_postes.py     # Função gerar KMZ para postes
│   │   └── kmz_poligonos.py  # Função gerar KMZ para polígonos
│   ├── templates/
│   │   └── index.html         # Formulário web estilizado
│   └── static/
│       └── style.css          # CSS separado opcional
