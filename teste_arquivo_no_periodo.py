"""
Arquivo de teste para validar a função _arquivo_no_periodo do processa_xml.py
Testa a extração de datas de emissão dos XMLs e o filtro por período
"""

import pandas as pd
import xml.etree.ElementTree as ET
import os
from datetime import datetime, date
from pathlib import Path
from processa_xml import ValidadorXMLNFe


def extrair_dados_xml(caminho_arquivo):
    """
    Extrai informações básicas do XML para teste
    
    Returns:
        dict com nome_arquivo, data_emissao, tipo_xml
    """
    try:
        tree = ET.parse(caminho_arquivo)
        root = tree.getroot()
        
        # Define namespace
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Busca o campo dhEmi
        dh_emi = root.find('.//nfe:dhEmi', ns)
        
        if dh_emi is None:
            # Se não encontrou com namespace, tenta sem
            dh_emi = root.find('.//dhEmi')
        
        # Identifica o tipo de XML
        tipo_xml = 'Desconhecido'
        if root.find('.//{http://www.portalfiscal.inf.br/nfe}NFe') is not None:
            tipo_xml = 'NFe/NFCe'
        elif root.find('.//{http://www.portalfiscal.inf.br/nfe}infEvento') is not None:
            tipo_xml = 'Evento (Cancelamento)'
        elif root.find('.//{http://www.portalfiscal.inf.br/nfe}retInutNFe') is not None:
            tipo_xml = 'Inutilização'
        
        # Extrai a data de emissão
        data_emissao = None
        data_emissao_str = None
        
        if dh_emi is not None and dh_emi.text:
            data_emissao_str = dh_emi.text
            # Extrai apenas a data (formato: 2025-11-21T09:03:54-03:00)
            data_parte = dh_emi.text.split('T')[0]
            data_emissao = datetime.strptime(data_parte, '%Y-%m-%d').date()
        
        return {
            'nome_arquivo': os.path.basename(caminho_arquivo),
            'caminho_completo': caminho_arquivo,
            'tipo_xml': tipo_xml,
            'data_emissao': data_emissao,
            'data_emissao_str': data_emissao_str,
            'tem_data': dh_emi is not None,
            'erro': None
        }
        
    except Exception as e:
        return {
            'nome_arquivo': os.path.basename(caminho_arquivo),
            'caminho_completo': caminho_arquivo,
            'tipo_xml': 'ERRO',
            'data_emissao': None,
            'data_emissao_str': None,
            'tem_data': False,
            'erro': str(e)
        }


def testar_extracao_datas(diretorio_xml):
    """
    Testa a extração de datas de todos os XMLs no diretório
    
    Args:
        diretorio_xml: Pasta contendo os XMLs para teste
        
    Returns:
        DataFrame com informações de todos os XMLs
    """
    print("=" * 80)
    print("TESTE DE EXTRAÇÃO DE DATAS DE EMISSÃO DOS XMLs")
    print("=" * 80)
    print(f"\nDiretório: {diretorio_xml}")
    print(f"Diretório existe: {os.path.exists(diretorio_xml)}")
    
    if not os.path.exists(diretorio_xml):
        print(f"\n❌ ERRO: Diretório não encontrado!")
        return pd.DataFrame()
    
    # Lista todos os arquivos XML no diretório (incluindo subpastas)
    arquivos_xml = []
    for root, dirs, files in os.walk(diretorio_xml):
        for arquivo in files:
            if arquivo.lower().endswith('.xml'):
                arquivos_xml.append(os.path.join(root, arquivo))
    
    print(f"\n✓ Encontrados {len(arquivos_xml)} arquivos XML")
    
    if not arquivos_xml:
        print(f"\n⚠️  Nenhum arquivo XML encontrado!")
        return pd.DataFrame()
    
    # Extrai dados de cada XML
    print("\nProcessando XMLs...")
    dados = []
    for i, arquivo in enumerate(arquivos_xml, 1):
        if i % 10 == 0:
            print(f"  Processando arquivo {i}/{len(arquivos_xml)}...")
        
        info = extrair_dados_xml(arquivo)
        dados.append(info)
    
    # Cria DataFrame
    df = pd.DataFrame(dados)
    
    # Estatísticas
    print("\n" + "=" * 80)
    print("ESTATÍSTICAS")
    print("=" * 80)
    print(f"\nTotal de arquivos: {len(df)}")
    print(f"Arquivos com data: {df['tem_data'].sum()}")
    print(f"Arquivos sem data: {(~df['tem_data']).sum()}")
    print(f"Arquivos com erro: {df['erro'].notna().sum()}")
    
    if df['data_emissao'].notna().any():
        print(f"\nData mais antiga: {df['data_emissao'].min()}")
        print(f"Data mais recente: {df['data_emissao'].max()}")
    
    print("\nDistribuição por tipo de XML:")
    print(df['tipo_xml'].value_counts().to_string())
    
    # Mostra arquivos com erro, se houver
    if df['erro'].notna().any():
        print("\n⚠️  ARQUIVOS COM ERRO:")
        erros = df[df['erro'].notna()][['nome_arquivo', 'erro']]
        for idx, row in erros.iterrows():
            print(f"  - {row['nome_arquivo']}: {row['erro']}")
    
    return df


def testar_funcao_arquivo_no_periodo(diretorio_xml, data_inicio=None, data_fim=None):
    """
    Testa a função _arquivo_no_periodo com diferentes períodos
    
    Args:
        diretorio_xml: Pasta contendo os XMLs
        data_inicio: Data inicial do filtro (str 'YYYY-MM-DD' ou date)
        data_fim: Data final do filtro (str 'YYYY-MM-DD' ou date)
        
    Returns:
        Tupla (df_todos, df_filtrados, df_excluidos)
    """
    print("\n" + "=" * 80)
    print("TESTE DA FUNÇÃO _arquivo_no_periodo")
    print("=" * 80)
    
    # Converte datas se necessário
    if isinstance(data_inicio, str):
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if isinstance(data_fim, str):
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    
    print(f"\nPeríodo de filtro:")
    print(f"  Data início: {data_inicio if data_inicio else 'Não definida'}")
    print(f"  Data fim: {data_fim if data_fim else 'Não definida'}")
    
    # Inicializa o validador com o período
    validador = ValidadorXMLNFe(
        diretorio_xml=diretorio_xml,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    # Lista todos os arquivos XML
    arquivos_xml = []
    for root, dirs, files in os.walk(diretorio_xml):
        for arquivo in files:
            if arquivo.lower().endswith('.xml'):
                arquivos_xml.append(os.path.join(root, arquivo))
    
    print(f"\n✓ Total de arquivos XML encontrados: {len(arquivos_xml)}")
    
    # Testa a função para cada arquivo
    resultados = []
    for arquivo in arquivos_xml:
        # Extrai data de emissão
        info = extrair_dados_xml(arquivo)
        
        # Testa a função _arquivo_no_periodo
        passa_filtro = validador._arquivo_no_periodo(arquivo)
        
        resultados.append({
            'nome_arquivo': info['nome_arquivo'],
            'data_emissao': info['data_emissao'],
            'data_emissao_str': info['data_emissao_str'],
            'tipo_xml': info['tipo_xml'],
            'passa_filtro': passa_filtro,
            'caminho_completo': arquivo
        })
    
    # Cria DataFrame
    df_todos = pd.DataFrame(resultados)
    
    # Separa filtrados e excluídos
    df_filtrados = df_todos[df_todos['passa_filtro']].copy()
    df_excluidos = df_todos[~df_todos['passa_filtro']].copy()
    
    # Estatísticas
    print("\n" + "-" * 80)
    print("RESULTADOS DO FILTRO")
    print("-" * 80)
    print(f"\nArquivos que PASSARAM no filtro: {len(df_filtrados)}")
    print(f"Arquivos EXCLUÍDOS pelo filtro: {len(df_excluidos)}")
    
    if not df_filtrados.empty:
        print("\n📋 ARQUIVOS FILTRADOS (primeiros 10):")
        print(df_filtrados[['nome_arquivo', 'data_emissao', 'tipo_xml']].head(10).to_string(index=False))
        
        if df_filtrados['data_emissao'].notna().any():
            print(f"\nData mais antiga (filtrados): {df_filtrados['data_emissao'].min()}")
            print(f"Data mais recente (filtrados): {df_filtrados['data_emissao'].max()}")
    
    if not df_excluidos.empty:
        print("\n🚫 ARQUIVOS EXCLUÍDOS (primeiros 10):")
        print(df_excluidos[['nome_arquivo', 'data_emissao', 'tipo_xml']].head(10).to_string(index=False))
        
        if df_excluidos['data_emissao'].notna().any():
            print(f"\nData mais antiga (excluídos): {df_excluidos['data_emissao'].min()}")
            print(f"Data mais recente (excluídos): {df_excluidos['data_emissao'].max()}")
    
    return df_todos, df_filtrados, df_excluidos


def testar_cenarios_multiplos(diretorio_xml):
    """
    Testa a função com múltiplos cenários de período
    """
    print("\n" + "=" * 80)
    print("TESTE DE MÚLTIPLOS CENÁRIOS")
    print("=" * 80)
    
    # Primeiro, extrai todas as datas para definir cenários de teste
    df_base = testar_extracao_datas(diretorio_xml)
    
    if df_base.empty or df_base['data_emissao'].isna().all():
        print("\n⚠️  Não foi possível extrair datas para criar cenários de teste")
        return
    
    # Define cenários baseados nas datas encontradas
    datas_validas = df_base['data_emissao'].dropna()
    data_min = datas_validas.min()
    data_max = datas_validas.max()
    
    cenarios = [
        ("Sem filtro (todos os arquivos)", None, None),
        ("Apenas data início", data_min, None),
        ("Apenas data fim", None, data_max),
        ("Período completo", data_min, data_max),
        ("Período restrito (meio do mês)", date(2025, 11, 10), date(2025, 11, 20)),
    ]
    
    resultados_cenarios = []
    
    for nome_cenario, data_inicio, data_fim in cenarios:
        print(f"\n{'=' * 80}")
        print(f"CENÁRIO: {nome_cenario}")
        print(f"{'=' * 80}")
        
        df_todos, df_filtrados, df_excluidos = testar_funcao_arquivo_no_periodo(
            diretorio_xml, data_inicio, data_fim
        )
        
        resultados_cenarios.append({
            'cenario': nome_cenario,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'total': len(df_todos),
            'filtrados': len(df_filtrados),
            'excluidos': len(df_excluidos)
        })
    
    # Resumo de todos os cenários
    print("\n" + "=" * 80)
    print("RESUMO DE TODOS OS CENÁRIOS")
    print("=" * 80)
    df_resumo = pd.DataFrame(resultados_cenarios)
    print("\n" + df_resumo.to_string(index=False))


def main():
    """
    Função principal de teste
    """
    # Diretório configurado pelo usuário
    diretorio_teste = r"C:\Clientes\Saboreie Matriz\Processa XML\Processa teste\112025"
    
    print("\n" + "=" * 80)
    print("VALIDAÇÃO DA FUNÇÃO _arquivo_no_periodo")
    print("=" * 80)
    print(f"\nDiretório de teste: {diretorio_teste}")
    
    # Verifica se o diretório existe
    if not os.path.exists(diretorio_teste):
        print(f"\n❌ ERRO: Diretório não encontrado!")
        print(f"Por favor, verifique o caminho: {diretorio_teste}")
        return
    
    # Teste 1: Extração básica de datas
    print("\n\n")
    print("🔍 TESTE 1: Extração de Datas de Emissão")
    print("-" * 80)
    df_extracao = testar_extracao_datas(diretorio_teste)
    
    if df_extracao.empty:
        print("\n❌ Não foi possível continuar os testes (nenhum XML encontrado)")
        return
    
    # Salva resultado da extração
    arquivo_saida_extracao = r"c:\Python\Processa-xml\teste_extracao_datas.xlsx"
    df_extracao.to_excel(arquivo_saida_extracao, index=False)
    print(f"\n✓ Resultado da extração salvo em: {arquivo_saida_extracao}")
    
    # Teste 2: Função com período específico (novembro 2025)
    print("\n\n")
    print("🔍 TESTE 2: Filtro por Período Específico (Novembro 2025)")
    print("-" * 80)
    df_todos, df_filtrados, df_excluidos = testar_funcao_arquivo_no_periodo(
        diretorio_teste,
        data_inicio=date(2025, 11, 1),
        data_fim=date(2025, 11, 30)
    )
    
    # Salva resultados do teste 2
    arquivo_saida_filtro = r"c:\Python\Processa-xml\teste_filtro_periodo.xlsx"
    with pd.ExcelWriter(arquivo_saida_filtro, engine='openpyxl') as writer:
        df_todos.to_excel(writer, sheet_name='Todos', index=False)
        df_filtrados.to_excel(writer, sheet_name='Filtrados', index=False)
        df_excluidos.to_excel(writer, sheet_name='Excluidos', index=False)
    print(f"\n✓ Resultado do filtro salvo em: {arquivo_saida_filtro}")
    
    # Teste 3: Múltiplos cenários
    print("\n\n")
    print("🔍 TESTE 3: Múltiplos Cenários de Filtro")
    print("-" * 80)
    testar_cenarios_multiplos(diretorio_teste)
    
    print("\n\n" + "=" * 80)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 80)
    print(f"\nArquivos de saída gerados:")
    print(f"  1. {arquivo_saida_extracao}")
    print(f"  2. {arquivo_saida_filtro}")
    print("\nVerifique os arquivos Excel para análise detalhada dos resultados.")


if __name__ == "__main__":
    main()
