
# backend/exportar_poste_kmz.py

import os
from google.cloud import bigquery
from google.oauth2 import service_account
import simplekml
import urllib.request
import json
from shapely import wkt
from urllib.error import HTTPError, URLError

GITHUB_TOKEN = "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"
FILE_URL = "https://raw.githubusercontent.com/drumondard/gcp-vtal-sandbox-engenharia/main/credentials_gcp/vtal-sandbox-engenharia-bfe3a49a6e20.json"

def load_service_account_info_from_github(token, url):
    headers = {
        "Authorization": f"token {token}",
        "User-Agent": "Python-script",
        "Accept": "application/vnd.github.v3.raw"
    }
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            data = response.read()
            return json.loads(data)
    except Exception as e:
        print(f"Erro ao baixar credenciais: {e}")
    return None

def gerar_kmz_poste(COD_IBGE_VALORES):
    # Carrega o JSON da credencial do GitHub autenticado
    service_account_info = load_service_account_info_from_github(GITHUB_TOKEN, FILE_URL)
    if not service_account_info:
        raise RuntimeError("Não foi possível carregar as credenciais do GitHub.")

    credentials = service_account.Credentials.from_service_account_info(service_account_info)
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)

    # Diretório de saída
    output_kmz_base = os.path.join(os.getcwd(), "kmz")
    os.makedirs(output_kmz_base, exist_ok=True)

    arquivos_gerados = []

    for COD_IBGE in COD_IBGE_VALORES:
        kml = simplekml.Kml()
        QUERY = f"""
            SELECT 
                SIGLA_UF,
                COD_IBGE,
                NM_MUN,
                ID_POSTE,
                ID_CABO,
                CONCESSIONARIA,
                PROPRIETARIO_POSTE,
                LONGITUDE_POSTE,
                LATITUDE_POSTE,
                geom
            FROM `vtal-sandbox-engenharia.inventario_postes_equipamentos_bdgd.vw_cabos_bdgd_pbi`
            WHERE LATITUDE_POSTE IS NOT NULL AND LONGITUDE_POSTE IS NOT NULL
            AND CAST(COD_IBGE AS STRING) = '{COD_IBGE}'
        """
        query_job = client.query(QUERY)
        results = query_job.result()

        for row in results:
            pnt = kml.newpoint(name=row.ID_POSTE, coords=[(row.LONGITUDE_POSTE, row.LATITUDE_POSTE)])
            descricao = f"""
            SIGLA_UF={row.SIGLA_UF}, COD_IBGE={row.COD_IBGE}, NM_MUN={row.NM_MUN}, ID_POSTE={row.ID_POSTE},
            ID_CABO={row.ID_CABO}, CONCESSIONARIA={row.CONCESSIONARIA}, PROPRIETARIO_POSTE={row.PROPRIETARIO_POSTE},
            LONGITUDE_POSTE={row.LONGITUDE_POSTE}, LATITUDE_POSTE={row.LATITUDE_POSTE}
            """
            pnt.description = descricao

        nome_arquivo = f"Ocupacao_Poste_{COD_IBGE}.kmz"
        caminho_arquivo = os.path.join(output_kmz_base, nome_arquivo)
        kml.savekmz(caminho_arquivo)
        arquivos_gerados.append(caminho_arquivo)

    return arquivos_gerados
