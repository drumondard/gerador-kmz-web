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
                FID_LANCE_CABO,
                COD_IBGE,
                NM_MUN,
                LOCALIDADE,
                UPPER(TIPO_REDE) AS TIPO_REDE,
                UPPER(TIPO_INST) AS TIPO_INST,
                MODELO,
                cd_geometry,
                FONTE
            FROM `vtal-sandbox-engenharia.invetario_relatorio_cabos.vw_consolidacao_cabos_desmobilizacao_municipio`
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
            FID_LANCE_CABO = row.FID_LANCE_CABO
            COD_IBGE = row.COD_IBGE
            NM_MUN = row.NM_MUN
            LOCALIDADE = row.LOCALIDADE
            TIPO_REDE = row.TIPO_REDE
            TIPO_INST = row.TIPO_INST.title()
            MODELO = row.MODELO
            cd_geometry = row.cd_geometry
            FONTE = row.FONTE

            municipio_nome = NM_MUN
            uf_sigla = SIGLA_UF

            geometry = wkt.loads(cd_geometry)
            if geometry.geom_type != 'LineString':
                print(f"Geometria inválida para FID_LANCE_CABO {FID_LANCE_CABO}. Ignorando...")
                continue

            coords = list(geometry.coords)

            if TIPO_REDE not in folders:
                folders[TIPO_REDE] = kml.newfolder(name=TIPO_REDE)
                subfolders[TIPO_REDE] = {}

            if TIPO_INST not in subfolders[TIPO_REDE]:
                subfolders[TIPO_REDE][TIPO_INST] = folders[TIPO_REDE].newfolder(name=TIPO_INST)

            linestring = subfolders[TIPO_REDE][TIPO_INST].newlinestring(name=str(FID_LANCE_CABO), coords=coords)

            tipo_inst_lower = TIPO_INST.lower()
            if tipo_inst_lower == "aereo":
                linestring.style.linestyle.color = simplekml.Color.blue
            elif tipo_inst_lower in ["subterraneo", "subterrâneo"]:
                linestring.style.linestyle.color = simplekml.Color.red
            else:
                linestring.style.linestyle.color = simplekml.Color.white
            linestring.style.linestyle.width = 3

            descricao = f"""
            SIGLA_UF={SIGLA_UF},
            FID_LANCE_CABO={FID_LANCE_CABO},
            COD_IBGE={COD_IBGE},
            NM_MUN={NM_MUN},
            LOCALIDADE={LOCALIDADE},
            TIPO_REDE={TIPO_REDE},
            TIPO_INST={TIPO_INST},
            MODELO={MODELO},
            FONTE={FONTE}
            """
            linestring.description = descricao

        if not dados_encontrados:
            raise ValueError(f"Nenhum dado encontrado para COD_IBGE {codigo_ibge}")

        nome_mun_formatado = municipio_nome.replace(" ", "_").replace("/", "-")
        output_filename = f"Ocupacao_Cabos_{uf_sigla}-{nome_mun_formatado}_COD_IBGE_{codigo_ibge}.kmz"
        output_kmz = os.path.join(output_kmz_base, output_filename)
        kml.savekmz(output_kmz)
        print(f"Arquivo KMZ salvo como {output_kmz}")        
        arquivos_gerados.append(output_kmz)

    return arquivos_gerados
