from pathlib import Path
import zipfile

def gerar_kmz_mock(ibge: str, tipo: str) -> Path:
    """Gera um arquivo KMZ fictício para download"""
    kmz_dir = Path("temp")
    kmz_dir.mkdir(exist_ok=True)
    
    kml_content = f"""
    <?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Placemark>
        <name>{tipo.upper()} - {ibge}</name>
        <Point><coordinates>-43.1729,-22.9068,0</coordinates></Point>
      </Placemark>
    </kml>
    """

    kml_path = kmz_dir / f"{ibge}_{tipo}.kml"
    kmz_path = kmz_dir / f"{ibge}_{tipo}.kmz"

    with open(kml_path, "w", encoding="utf-8") as f:
        f.write(kml_content.strip())

    with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(kml_path, arcname="doc.kml")

    kml_path.unlink()  # Remove o .kml após criar o .kmz
    return kmz_path
