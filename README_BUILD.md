# Analisador de XMLs Fiscais - Instruções de Build

## Visão Geral

Este aplicativo processa XMLs fiscais (NFCe) do sistema Totvs Chef e gera análises detalhadas em formato Excel.

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

3. O executavel sera criado em `dist/Analisador_XMLs_Fiscais_vX.X.X.exe`

### Opcao 2: Manual com PyInstaller

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name=Analisador_XMLs_Fiscais_v1.3.0 app_gui.py
```

**Nota:** Atualize o numero da versao no nome conforme necessario.

## Estrutura do Projeto

- `app_gui.py` - Interface grafica do aplicativo
- `processa_xml.py` - Logica de processamento dos XMLs
- `config.py` - Configuracoes (agora dinamicas via GUI)
- `requirements.txt` - Dependencias do projeto
- `build_windows.py` - Script automatico para criar o executavel
- `CHANGELOG.md` - Historico de versoes e mudancas

## Funcionalidades

### Validacao Automatica
- **Validacao de CNPJ unico**: O sistema verifica se todos os XMLs sao do mesmo CNPJ antes de processar. Se forem encontrados CNPJs diferentes, o processamento e interrompido com uma mensagem de alerta.

### Configurações Obrigatórias:
- **Pasta dos XMLs**: Diretório contendo os arquivos XML fiscais (todos devem ser do mesmo CNPJ)
- **Pasta de Análises**: Onde os resultados serão salvos (deve ser diferente da pasta de relatórios)
- **Período**: Datas de início e fim para filtrar os XMLs pela data de emissão

### Configurações Opcionais
- **Pasta dos Relatórios 65**: Diretório com os relatórios 65 (Opcional)
- **Banco de Dados**: Se configurado, o sistema realizará análise cruzada com a tabela ECF Log.
- Nome do Banco
- Usuário
- Senha

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

O executavel gerado (`\dist\Analisador_XMLs_Fiscais_vX.X.X.exe`) pode ser distribuido e executado em qualquer maquina Windows sem necessidade de ter Python instalado.

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
