from flask import Flask, request, jsonify, send_from_directory
import os
import pandas as pd
from cnpj_pegador import buscar_dados_cnpj, formatar_valor
import uuid

app = Flask(__name__)

# Caminho onde os arquivos gerados serão salvos
UPLOAD_FOLDER = 'static/files'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
def index():
    return open('C:/Users/GABRIEL/Desktop/cnpj-pegador/index.html').read()


@app.route('/receber-cnpjs', methods=['POST'])
def receber_cnpjs():
    data = request.get_json()
    cnpjs_bruto = data.get('cnpjs', [])
    print(cnpjs_bruto)
    cnpjs = []
    for cnpj in cnpjs_bruto:
        cnpj = str(cnpj).replace('.', '').replace('/', '').replace('-', '')
        cnpjs.append(cnpj)
    print(cnpjs)

    todos_dados = []
    logs = []  # Lista para armazenar as mensagens de log

    for cnpj in cnpjs:
        log_msg = f"Buscando dados para o CNPJ: {cnpj}"
        print(log_msg)  # Continua exibindo no console
        logs.append(log_msg)  # Adiciona a mensagem à lista

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
    logs.append(log_msg)  # Adiciona ao log

    return jsonify({
        'message': 'Lista de CNPJs processada e arquivo gerado!',
        'arquivo': nome_arquivo,
        'logs': logs  # Envia os logs para o frontend
    })


# Rota para fazer o download do arquivo gerado
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)
