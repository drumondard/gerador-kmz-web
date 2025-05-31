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
                    CD_MUN as COD_IBGE,
                    NM_MUN,
                    geometry,  -- Usando a geometria diretamente sem conversões
                    AREA_KM2
                FROM `vtal-sandbox-engenharia.inventario_postes_equipamentos_bdgd.BR_Municipios_2022`  
            WHERE CAST(CD_MUN AS STRING) = '{codigo_ibge}'
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
            geometry = row.geometry  # A geometria já é do tipo GEOGRAPHY
            AREA_KM2 = row.AREA_KM2

            municipio_nome = NM_MUN
            uf_sigla = SIGLA_UF

            # Converte a geometria para objeto Shapely
            if geometry:
                geometry = wkt.loads(geometry)

                if geometry.geom_type in ['Polygon', 'MultiPolygon']:
                    # Se for MultiPolygon, pegar cada polígono separadamente
                    polygons = [geometry] if geometry.geom_type == 'Polygon' else list(geometry.geoms)

                    for poly in polygons:
                        # Simplificar a geometria com Shapely em Python (se necessário)
                        simplified_poly = poly.simplify(0.001, preserve_topology=True)

                        outer_coords = list(simplified_poly.exterior.coords)
                        pol = kml.newpolygon(name=NM_MUN, outerboundaryis=outer_coords)

                        # Definindo cor da linha, largura e opacidade
                        pol.style.linestyle.color = simplekml.Color.green  # Cor amarela
                        pol.style.linestyle.width = 4  # Largura da linha
                        pol.style.linestyle.opacity = 1  # Opacidade da linha (100%)

                        # Definindo a cor de preenchimento do polígono e a opacidade
                        pol.style.polystyle.color = simplekml.Color.changealphaint(100, simplekml.Color.green)  # Preenchimento amarelo com 100% opacidade

                        # Criar a descrição concatenada
                        descricao = f"""
                        "SIGLA_UF"={SIGLA_UF},
                        "COD_IBGE"={codigo_ibge},
                        "NM_MUN"={NM_MUN},
                        "AREA_KM2"={AREA_KM2}
                        """
                        pol.description = descricao
                else:
                    print(f"Geometria inesperada para {NM_MUN} ({geometry.geom_type}). Pulando...")

        if not dados_encontrados:
            raise ValueError(f"Nenhum dado encontrado para COD_IBGE {codigo_ibge}")
        
        # Salva o arquivo KMZ
        nome_mun_formatado = municipio_nome.replace(" ", "_").replace("/", "-")
        output_filename = f"Poligono_{uf_sigla}-{nome_mun_formatado}_COD_IBGE_{codigo_ibge}.kmz"
        output_kmz = os.path.join(output_kmz_base, output_filename)
        kml.savekmz(output_kmz)
        print(f"Arquivo KMZ salvo como {output_kmz}")
        arquivos_gerados.append(output_kmz)

    return arquivos_gerados
