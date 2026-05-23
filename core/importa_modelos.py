import requests
from core.models import ModeloVeiculo

def importar_modelos():
    url_marcas = "https://fetchicles-api.onrender.com/api/brands/car"
    response = requests.get(url_marcas)
    if response.status_code != 200:
        print("Erro ao buscar marcas")
        return

    marcas = response.json()

    for marca in marcas:
        url_modelos = f"https://fetchicles-api.onrender.com/api/brands/car/{marca.lower()}"
        modelos_resp = requests.get(url_modelos)
        if modelos_resp.status_code != 200:
            print(f"Erro ao buscar modelos de {marca}")
            continue

        modelos = modelos_resp.json()
        for modelo in modelos:
            ModeloVeiculo.objects.get_or_create(marca=marca, modelo=modelo)
        print(f"✓ {marca}: {len(modelos)} modelos importados")

    print("Importação finalizada.")
