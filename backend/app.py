from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import pandas as pd
import uuid
import logging
import json
import boto3
import base64
from cnpj_pegador import buscar_dados_cnpj, formatar_valor
from mangum import Mangum
import time

# Criando o aplicativo FastAPI
app = FastAPI()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# S3 Configuração
S3_BUCKET_NAME = 'cnpj-buscador'
S3_FOLDER = 'download/'

# Criando o cliente S3
s3_client = boto3.client('s3')

# Pasta de upload (usando pasta temporária do Lambda)
UPLOAD_FOLDER = '/tmp/files'  # Usar pasta temporária no Lambda
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.state.upload_folder = UPLOAD_FOLDER


@app.post('/receber-cnpjs')
async def receber_cnpjs(request: Request):
    # Obtém o corpo da requisição
    body = await request.body()

    # Verifica se o corpo é base64 ou JSON
    try:
        if request.headers.get('Content-Type') == 'application/json':
            data = await request.json()
        else:
            data = json.loads(base64.b64decode(body).decode('utf-8'))
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Erro ao processar a requisição: {e}")

    cnpjs_bruto = data.get('cnpjs', [])
    cnpjs = [
        str(cnpj).replace('.', '').replace('/', '').replace('-', '')
        for cnpj in cnpjs_bruto
    ]

    todos_dados = []
    logs = []

    for cnpj in cnpjs:
        log_msg = f"Buscando dados para o CNPJ: {cnpj}"
        logs.append(log_msg)

        dados = buscar_dados_cnpj(cnpj)
        if dados:
            todos_dados.append(dados)

        time.sleep(2)

    if todos_dados:
        df_dados_gerais = pd.json_normalize(todos_dados)
        for coluna in df_dados_gerais.select_dtypes(include=['object']).columns:
            df_dados_gerais[coluna] = df_dados_gerais[coluna].map(
                formatar_valor)
    else:
        df_dados_gerais = pd.DataFrame()

    lista_socios = []
    for dado in todos_dados:
        cnpj_origem = dado.get('cnpj', '')  # de cnpj_raiz para cnpj
        razao_origem = dado.get('razao_social', '')  # certo
        qsa = dado.get('qsa', [])  # de socios para qsa

        if isinstance(qsa, list):
            for socio in qsa:
                socio_formatado = {
                    'CNPJ': cnpj_origem,
                    'razao_social': razao_origem,
                    'CPF/CNPJ Sócio': formatar_valor(socio.get('cnpj_cpf_do_socio')),
                    'Nome': formatar_valor(socio.get('nome_socio')),
                    'Data Entrada': formatar_valor(socio.get('data_entrada_sociedade')),
                    'Qualificação Sócio': formatar_valor(socio.get('qualificacao_socio')),
                    'CPF Representante': formatar_valor(socio.get('cpf_representante_legal')),
                    'Nome Representante': formatar_valor(socio.get('nome_representante_legal')),
                    'Faixa Etária': formatar_valor(socio.get('faixa_etaria')),
                    'Qualificacao do Representante': formatar_valor(socio.get('qualificacao_representante_legal')),
                    'País': formatar_valor(socio.get('pais'))
                }
                lista_socios.append(socio_formatado)

    df_socios = pd.DataFrame(lista_socios)

    nome_arquivo = f'dados_cnpjs_{uuid.uuid4().hex}.xlsx'
    caminho_arquivo = os.path.join(app.state.upload_folder, nome_arquivo)

    # Cria o arquivo Excel
    with pd.ExcelWriter(caminho_arquivo, engine='xlsxwriter') as writer:
        df_dados_gerais.to_excel(
            writer, sheet_name='Dados Gerais', index=False)
        df_socios.to_excel(writer, sheet_name='Sócios', index=False)

    # Verifica se o arquivo foi gerado com sucesso
    if os.path.exists(caminho_arquivo):
        log_msg = f"Arquivo gerado com sucesso."
        logs.append(log_msg)
    else:
        log_msg = "Erro ao salvar o arquivo."
        logs.append(log_msg)

    # Faz o upload do arquivo para o S3
    s3_key = f"{S3_FOLDER}{nome_arquivo}"

    try:
        with open(caminho_arquivo, 'rb') as file_data:
            s3_client.upload_fileobj(file_data, S3_BUCKET_NAME, s3_key)
            # Gera a URL para o download
            s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            return JSONResponse({
                'message': 'Lista de CNPJs processada e arquivo gerado!',
                'arquivo': nome_arquivo,
                'url': s3_url,  # Retorna a URL do arquivo gerado no S3
                'logs': logs
            })
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao fazer upload para o S3: {str(e)}")


# Handler para AWS Lambda
handler = Mangum(app)  # Esta linha é importante para integração com Lambda

# **Correção do `lambda_handler` para repassar requisições ao FastAPI**


def lambda_handler(event, context):
    """
    Este handler recebe eventos do API Gateway e os encaminha para o Mangum,
    garantindo que o CORS seja tratado corretamente.
    """
    # Manipula requisições OPTIONS para CORS
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                # Permitir o domínio específico
                'Access-Control-Allow-Origin': 'https://main.d1oye14rstulb5.amplifyapp.com',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({'message': 'Hello from Lambda!'})
        }

    # Chama o handler do FastAPI via Mangum
    response = handler(event, context)

    # Adicionando cabeçalhos CORS à resposta do POST
    response['headers'] = response.get('headers', {})
    # Permitir o domínio específico
    response['headers']['Access-Control-Allow-Origin'] = 'https://main.d1oye14rstulb5.amplifyapp.com'
    response['headers']['Access-Control-Allow-Methods'] = 'OPTIONS,POST,GET'
    response['headers']['Access-Control-Allow-Headers'] = 'Content-Type'

    return response
