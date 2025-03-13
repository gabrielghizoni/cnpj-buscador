import requests
import time

# Função para buscar dados do CNPJ na API com retentativas


def buscar_dados_cnpj(cnpj, max_retries=3, delay=3):
    url = f"https://publica.cnpj.ws/cnpj/{cnpj}"
    headers = {"User-Agent": "Mozilla/5.0"}

    for attempt in range(max_retries):
        try:
            # Log de tentativa
            print(f"Tentativa {attempt+1}: Buscando {cnpj}...")
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                # Log de sucesso
                print(f"Sucesso: CNPJ {cnpj} encontrado!")
                return response.json()
            elif response.status_code == 429:
                print(f"API bloqueou (429). Esperando {delay} segundos...")
                time.sleep(delay)
            else:
                print(f"Erro {response.status_code} para CNPJ {cnpj}")

        except requests.exceptions.Timeout:
            print(f"Timeout ao buscar CNPJ {cnpj}. Tentando novamente...")
        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar CNPJ {cnpj}: {e}")

        time.sleep(delay)

    print(f"Falha ao buscar CNPJ {cnpj} após {max_retries} tentativas.")
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
