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
                ID_POSTE,
                ID_CABO,
                CONCESSIONARIA,
                PROPRIETARIO_POSTE,
                LONGITUDE_POSTE,
                LATITUDE_POSTE,
                geom
            FROM `vtal-sandbox-engenharia.inventario_postes_equipamentos_bdgd.vw_cabos_bdgd_pbi`
            WHERE 1=1
            AND LATITUDE_POSTE IS NOT NULL AND LONGITUDE_POSTE IS NOT NULL
            AND CAST(CD_MUN AS STRING) = '{codigo_ibge}'
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
            ID_POSTE = row.ID_POSTE
            ID_CABO = row.ID_CABO
            CONCESSIONARIA = row.CONCESSIONARIA
            PROPRIETARIO_POSTE = row.PROPRIETARIO_POSTE
            LONGITUDE_POSTE = row.LONGITUDE_POSTE
            LATITUDE_POSTE = row.LATITUDE_POSTE

            municipio_nome = NM_MUN
            uf_sigla = SIGLA_UF

            # Converte a geometria para objeto Shapely >> Criar ponto
            pnt = kml.newpoint(name=ID_POSTE, coords=[(LONGITUDE_POSTE, LATITUDE_POSTE)])

            # Criar a descrição concatenada
            descricao = f"""
            "SIGLA_UF"={SIGLA_UF}, 
            "COD_IBGE"={codigo_ibge}, 
            "NM_MUN"={NM_MUN}, 
            "ID_POSTE"={ID_POSTE},
            "ID_CABO"={ID_CABO}, "CONCESSIONARIA"={CONCESSIONARIA}, 
            "PROPRIETARIO_POSTE"={PROPRIETARIO_POSTE},
            "LONGITUDE_POSTE"={LONGITUDE_POSTE}, 
            "LATITUDE_POSTE"={LATITUDE_POSTE}
            """

            # Definir a descrição do ponto
            pnt.description = descricao

        
        # Salva o arquivo KMZ
        nome_mun_formatado = municipio_nome.replace(" ", "_").replace("/", "-")
        output_filename = f"Ocupacao_Poste_{uf_sigla}-{nome_mun_formatado}_COD_IBGE_{codigo_ibge}.kmz"
        output_kmz = os.path.join(output_kmz_base, output_filename)
        kml.savekmz(output_kmz)
        print(f"Arquivo KMZ salvo como {output_kmz}")
        arquivos_gerados.append(output_kmz)

    return arquivos_gerados
