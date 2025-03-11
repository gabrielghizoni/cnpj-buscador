import requests
import pandas as pd

# Função para buscar dados do CNPJ na API


def buscar_dados_cnpj(cnpj):
    url = f"https://publica.cnpj.ws/cnpj/{cnpj}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erro ao buscar CNPJ {cnpj}: {response.status_code}")
        return None

# Função para formatar corretamente os valores


def formatar_valor(valor):
    if isinstance(valor, dict):
        valor = str(valor).strip().replace('[', '').replace(']', '').replace(
            '{', '').replace('}', '').replace("'", "")
        return valor
    elif isinstance(valor, list):
        valor = str(valor).strip().replace('[', '').replace(']', '').replace(
            '{', '').replace('}', '').replace("'", "")
        return valor
    elif valor is None or valor == '':
        return ""  # Retorna string vazia ao invés de None ou ''
    else:
        return str(valor).strip().replace('[', '').replace(']', '').replace(
            '{', '').replace('}', '').replace("'", "")
