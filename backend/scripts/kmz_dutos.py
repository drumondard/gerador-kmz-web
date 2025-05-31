import os
from google.cloud import bigquery
from google.oauth2 import service_account
import simplekml
import urllib.request
import json
from shapely import wkt
from urllib.error import HTTPError, URLError
from dotenv import load_dotenv

load_dotenv()  # Carrega variáveis do arquivo .env

# Pega token e URL do .env
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
FILE_URL = os.getenv("GITHUB_CREDENTIALS_URL")

if not GITHUB_TOKEN or not FILE_URL:
    raise RuntimeError("Variáveis GITHUB_TOKEN ou GITHUB_CREDENTIALS_URL não definidas no ambiente.")

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
    except HTTPError as e:
        print(f"Erro HTTP ao baixar credencial: {e.code} - {e.reason}")
    except URLError as e:
        print(f"Erro de conexão ao baixar credencial: {e.reason}")
    except Exception as e:
        print(f"Erro inesperado ao baixar credencial: {e}")
    return None

# Carrega o JSON da credencial do GitHub autenticado
service_account_info = load_service_account_info_from_github(GITHUB_TOKEN, FILE_URL)
if not service_account_info:
    raise RuntimeError("Não foi possível carregar as credenciais do GitHub.")

# Cria as credenciais para o BigQuery
credentials = service_account.Credentials.from_service_account_info(service_account_info)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

home_dir = os.path.expanduser("~")
output_kmz_base = os.path.join(home_dir, "Downloads")
os.makedirs(output_kmz_base, exist_ok=True)  # garante que o diretório exista

def gerar_kmz(codigos_ibge: str) -> list:
    lista_codigos = [cod.strip() for cod in codigos_ibge.split(",") if cod.strip()]
    if not lista_codigos:
        raise ValueError("Nenhum código IBGE fornecido.")

    arquivos_gerados = []

    for codigo_ibge in lista_codigos:
        QUERY = f"""
            SELECT 
                SIGLA_UF,
                COD_IBGE,
                NM_MUN,
                LOCALIDADE,
                FID_DUTO,
                QTDE_DUTOS,
                GEOMETRY_DUTO,
                'DUTO' AS TIPO_REDE,
                'SUBTERRANEO' AS TIPO_INST
            FROM `vtal-sandbox-engenharia.inventario_dutos.vw_consolidacao_dutos` 
            WHERE CAST(COD_IBGE AS STRING) = '{codigo_ibge}'
        """

        query_job = client.query(QUERY)
        results = query_job.result()

        kml = simplekml.Kml()
        folders = {}
        subfolders = {}

        dados_encontrados = False
        municipio_nome = ""
        uf_sigla = ""

        for row in results:
            dados_encontrados = True
            SIGLA_UF = row.SIGLA_UF
            NM_MUN = row.NM_MUN
            COD_IBGE = row.COD_IBGE
            LOCALIDADE = row.LOCALIDADE
            FID_DUTO = row.FID_DUTO
            QTDE_DUTOS = row.QTDE_DUTOS
            GEOMETRY_DUTO = row.GEOMETRY_DUTO
            TIPO_REDE = row.TIPO_REDE
            TIPO_INST = row.TIPO_INST.title()

            municipio_nome = NM_MUN
            uf_sigla = SIGLA_UF

            geometry = wkt.loads(GEOMETRY_DUTO)
            if geometry.geom_type != 'LineString':
                print(f"Geometria inválida para FID_DUTO {FID_DUTO}. Ignorando...")
                continue

            coords = list(geometry.coords)

            # Criação das pastas
            if TIPO_REDE not in folders:
                folders[TIPO_REDE] = kml.newfolder(name=TIPO_REDE)
                subfolders[TIPO_REDE] = {}

            if TIPO_INST not in subfolders[TIPO_REDE]:
                subfolders[TIPO_REDE][TIPO_INST] = folders[TIPO_REDE].newfolder(name=TIPO_INST)

            linestring = subfolders[TIPO_REDE][TIPO_INST].newlinestring(name=FID_DUTO, coords=coords)

            # Estilo
            linestring.style.linestyle.color = simplekml.Color.red  # Subterrâneo = vermelho
            linestring.style.linestyle.width = 3

            descricao = f"""
            SIGLA_UF={SIGLA_UF},
            COD_IBGE={COD_IBGE},
            NM_MUN={NM_MUN},
            LOCALIDADE={LOCALIDADE},
            FID_DUTO={FID_DUTO},
            QTDE_DUTOS={QTDE_DUTOS}
            """
            linestring.description = descricao

        if not dados_encontrados:
            raise ValueError(f"Nenhum dado encontrado para COD_IBGE {codigo_ibge}")
        
        # Salva o arquivo KMZ
        nome_mun_formatado = municipio_nome.replace(" ", "_").replace("/", "-")
        output_filename = f"Ocupacao_Dutos_{uf_sigla}-{nome_mun_formatado}_COD_IBGE_{codigo_ibge}.kmz"
        output_kmz = os.path.join(output_kmz_base, output_filename)
        kml.savekmz(output_kmz)
        print(f"Arquivo KMZ salvo como {output_kmz}")
        arquivos_gerados.append(output_kmz)

    return arquivos_gerados
