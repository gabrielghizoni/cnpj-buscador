from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import pandas as pd
from cnpj_pegador import buscar_dados_cnpj, formatar_valor
import uuid
from mangum import Mangum
import logging

# Inicializa o CORS
app = Flask(__name__)
CORS(app)  # Permite todas as origens

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =================== MUDANÇAS NECESSÁRIAS ===================
# 1. Remover referências ao frontend do Flask
app = Flask(__name__)  # Removidos static_folder e template_folder

# 2. Usar /tmp (caminho válido no Lambda)
UPLOAD_FOLDER = '/tmp/files'  # Pasta temporária específica para os arquivos
# =============================================================

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# =================== MUDANÇA OBRIGATÓRIA ====================
# 3. Remover caminho absoluto do Windows


@app.route('/')
def index():
    return "API em execução! Acesse o frontend no Amplify"  # Frontend separado


@app.route('/receber-cnpjs', methods=['POST'])
def receber_cnpjs():
    data = request.get_json()
    cnpjs_bruto = data.get('cnpjs', [])
    print(cnpjs_bruto)

    cnpjs = [
        str(cnpj).replace('.', '').replace('/', '').replace('-', '')
        for cnpj in cnpjs_bruto
    ]
    print(cnpjs)

    todos_dados = []
    logs = []

    for cnpj in cnpjs:
        log_msg = f"Buscando dados para o CNPJ: {cnpj}"
        print(log_msg)
        logs.append(log_msg)

        dados = buscar_dados_cnpj(cnpj)
        if dados:
            todos_dados.append(dados)

    if todos_dados:
        df_dados_gerais = pd.json_normalize(todos_dados)
        for coluna in df_dados_gerais.select_dtypes(include=['object']).columns:
            df_dados_gerais[coluna] = df_dados_gerais[coluna].map(
                formatar_valor)
    else:
        df_dados_gerais = pd.DataFrame()

    lista_socios = []
    for dado in todos_dados:
        cnpj_origem = dado.get('cnpj_raiz', '')
        razao_origem = dado.get('razao_social', '')
        socios = dado.get('socios', [])

        if isinstance(socios, list):
            for socio in socios:
                socio_formatado = {
                    'CNPJ': cnpj_origem,
                    'razao_social': razao_origem,
                    'CPF/CNPJ Sócio': formatar_valor(socio.get('cpf_cnpj_socio')),
                    'Nome': formatar_valor(socio.get('nome')),
                    'Tipo': formatar_valor(socio.get('tipo')),
                    'Data Entrada': formatar_valor(socio.get('data_entrada')),
                    'CPF Representante': formatar_valor(socio.get('cpf_representante_legal')),
                    'Nome Representante': formatar_valor(socio.get('nome_representante')),
                    'Faixa Etária': formatar_valor(socio.get('faixa_etaria')),
                    'Atualizado em': formatar_valor(socio.get('atualizado_em')),
                    'País': formatar_valor(socio.get('pais', {}).get('nome')),
                    'Qualificação Sócio': formatar_valor(socio.get('qualificacao_socio', {}).get('descricao'))
                }
                lista_socios.append(socio_formatado)

    df_socios = pd.DataFrame(lista_socios)

    nome_arquivo = f'dados_cnpjs_{uuid.uuid4().hex}.xlsx'
    caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)

    with pd.ExcelWriter(caminho_arquivo, engine='xlsxwriter') as writer:
        df_dados_gerais.to_excel(
            writer, sheet_name='Dados Gerais', index=False)
        df_socios.to_excel(writer, sheet_name='Sócios', index=False)

    if os.path.exists(caminho_arquivo):
        log_msg = f"Arquivo gerado com sucesso."
    else:
        log_msg = "Erro ao salvar o arquivo."

    print(log_msg)
    logs.append(log_msg)

    return jsonify({
        'message': 'Lista de CNPJs processada e arquivo gerado!',
        'arquivo': nome_arquivo,
        'logs': logs
    })


@app.route('/download/<filename>')
def download_file(filename):
    # Verifica se o arquivo existe no diretório de upload
    caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Verifica se o arquivo existe antes de tentar enviar
    if os.path.exists(caminho_arquivo):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    else:
        return jsonify({'message': 'Arquivo não encontrado'}), 404


# Handler para AWS Lambda
handler = Mangum(app)  # Esta linha é importante para integração com Lambda
