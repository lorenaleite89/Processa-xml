# CAMINHO DA PASTA 'Processa XML'

PATH = r"D:/Clientes/Saboreie Matriz/Processa XML"

# CAMINHO DOS ARQUIVOS XML
PATH_XML = r"D:/Clientes/Saboreie Matriz/Processa XML/Backup XML"

# CAMINHO DOS RELATÓRIOS 65
PATH_RELATORIOS_65 = r"D:/Clientes/Saboreie Matriz/Processa XML/Relatorios 65"

# CAMINHO PARA RESULTADOS DE ANALISES
PATH_ANALISES = r"D:/Clientes/Saboreie Matriz/Processa XML/Analises"

# CONFIGURAÇÃO DE BANCO DE DADOS

NOME_DB = 'MISTERCHEFNET'
USER_DB = 'sa'
PASSWORD_DB = 'MISTERCHEFNET'

DB_CONNECTION_STRING = f'mssql+pyodbc://{USER_DB}:{PASSWORD_DB}@localhost:1433/{NOME_DB}?driver=ODBC+Driver+17+for+SQL+Server'


# CORRESPONDÊNCIA ENTRE SÉRIE E CAIXA
# Formato: 'série': 'nome_caixa'
SERIE_CAIXA_MAP = {
    '2': 'Caixa 1',
    '3': 'Caixa 2', 
    '4': 'Caixa 3'
}

# CORRESPONDÊNCIA INVERSA: CAIXA PARA SÉRIE
# Formato: 'nome_caixa': 'série'
CAIXA_SERIE_MAP = {
    'Caixa 1': '2',
    'Caixa 2': '3',
    'Caixa 3': '4'
}