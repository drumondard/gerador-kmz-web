# Gerador de KMZ Web

Este projeto permite a geração interativa de arquivos KMZ com base em consultas SQL no BigQuery, acessados por um frontend simples e um backend em FastAPI.

## 🚀 Tecnologias

- Frontend: HTML + JavaScript
- Backend: Python 3 + FastAPI
- Banco de dados: Google BigQuery
- Geração de KMZ: `simplekml`, `geopandas`

## 📁 Estrutura

gerador-kmz/
├── backend/ # API com FastAPI
├── frontend/ # Interface web
├── credentials/ # JSON do GCP (não versionado)
└── README.md
