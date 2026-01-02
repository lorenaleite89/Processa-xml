"""
Configuração do sistema - valores são definidos via variáveis de ambiente
ou pela interface gráfica
"""
import os


# CAMINHOS DOS ARQUIVOS - definidos via ambiente ou GUI
PATH_XML = os.environ.get('PATH_XML', '')
PATH_RELATORIOS_65 = os.environ.get('PATH_RELATORIOS_65', '')
PATH_ANALISES = os.environ.get('PATH_ANALISES', '')

# CONFIGURAÇÃO DE BANCO DE DADOS (OPCIONAL)
USE_DB = os.environ.get('USE_DB', 'False').lower() == 'true'
NOME_DB = os.environ.get('NOME_DB', '')
USER_DB = os.environ.get('USER_DB', '')
PASSWORD_DB = os.environ.get('PASSWORD_DB', '')

# Construir connection string apenas se o banco de dados estiver configurado
DB_CONNECTION_STRING = None
if USE_DB and NOME_DB and USER_DB and PASSWORD_DB:
    DB_CONNECTION_STRING = f'mssql+pyodbc://{USER_DB}:{PASSWORD_DB}@localhost:1433/{NOME_DB}?driver=ODBC+Driver+17+for+SQL+Server'
