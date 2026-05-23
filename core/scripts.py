import requests
from core.models import ModeloVeiculo

def importar_modelos():
    url_marcas = "https://fetchicles-api.onrender.com/api/brands/car"
    response = requests.get(url_marcas)
    if response.status_code != 200:
        print("Erro ao obter marcas.")
        return

    marcas = response.json()
    for marca in marcas:
        url_modelos = f"https://fetchicles-api.onrender.com/api/brands/car/{marca.lower()}"
        resp_modelos = requests.get(url_modelos)
        if resp_modelos.status_code != 200:
            print(f"Erro ao obter modelos da marca {marca}.")
            continue

        modelos = resp_modelos.json()
        for modelo in modelos:
            ModeloVeiculo.objects.get_or_create(marca=marca, modelo=modelo)
        print(f"Importados modelos da marca {marca}.")
