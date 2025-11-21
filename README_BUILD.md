# Analisador de XMLs Fiscais - Instruções de Build

## Visão Geral

Este aplicativo processa XMLs fiscais (NFe/NFCe) e gera análises detalhadas em formato Excel.

## Requisitos para Build

Para criar o executável Windows, você precisa ter:

- Python 3.8 ou superior
- Bibliotecas listadas em `requirements.txt`

## Como Criar o Executável

### Opção 1: Script Automático (Recomendado)

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Execute o script de build:
```bash
python build_windows.py
```

3. O executável será criado em `dist/Analisador_XMLs_Fiscais.exe`

### Opção 2: Manual com PyInstaller

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name=Analisador_XMLs_Fiscais app_gui.py
```

## Estrutura do Projeto

- `app_gui.py` - Interface gráfica do aplicativo
- `processa_xml.py` - Lógica de processamento dos XMLs
- `config.py` - Configurações (agora dinâmicas via GUI)
- `requirements.txt` - Dependências do projeto
- `build_windows.py` - Script automático para criar o executável

## Funcionalidades

### Configurações Obrigatórias:
- **Pasta dos XMLs**: Diretório contendo os arquivos XML fiscais
- **Pasta dos Relatórios 65**: Diretório com os relatórios 65
- **Pasta de Análises**: Onde os resultados serão salvos (deve ser diferente da pasta de relatórios)
- **Período**: Datas de início e fim para filtrar os XMLs pela data de emissão

### Configurações Opcionais (Banco de Dados):
- Nome do Banco
- Usuário
- Senha

Se configurado, o sistema realizará análise cruzada com a tabela ECF Log.

## Mudanças Importantes

### Remoções:
1. ✅ Variável `PATH` removida
2. ✅ Mapeamentos de Série/Caixa removidos
3. ✅ Todas as referências a correspondência Série-Caixa removidas

### Alterações:
1. ✅ Filtro de período agora usa `<dhEmi>` do XML (data de emissão) ao invés da data de criação do arquivo
2. ✅ Configurações de banco de dados são opcionais
3. ✅ `criar_analise_ecf_log` só executa se houver configuração de BD
4. ✅ Todas as configurações são agora inputadas via interface gráfica

## Estrutura do XML Processada

O sistema busca a data de emissão no seguinte caminho do XML:
```xml
<nfeProc>
  <NFe>
    <infNFe>
      <ide>
        <dhEmi>2025-11-21T09:03:54-03:00</dhEmi>
      </ide>
    </infNFe>
  </NFe>
</nfeProc>
```

## Distribuição

O executável gerado (`Analisador_XMLs_Fiscais.exe`) pode ser distribuído e executado em qualquer máquina Windows sem necessidade de ter Python instalado.

### Observações Importantes:
- O executável é standalone (não precisa de Python)
- Recomenda-se ter o ODBC Driver 17 for SQL Server instalado se for usar a integração com banco de dados
- O aplicativo mantém todas as configurações na memória durante a sessão

## Suporte

Em caso de dúvidas ou problemas, verifique:
1. Se todas as pastas configuradas existem e são acessíveis
2. Se as datas estão no formato correto (DD/MM/AAAA)
3. Se a pasta de análises é diferente da pasta de relatórios
4. Os logs na área de "Log de Processamento" da interface
