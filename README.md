


# Analisador de XMLs Fiscais (NFe/NFCe)

## Visao Geral

Aplicativo Windows para processamento e analise de XMLs fiscais (NFe/NFCe) do sistema Totvs Chef. O sistema processa os arquivos XML, identifica notas processadas, canceladas e inutilizadas, e gera relatorios detalhados em formato Excel.

## Funcionalidades Principais

- Processamento de XMLs de notas fiscais eletronicas (NFe/NFCe)
- Identificacao automatica de notas processadas, canceladas e inutilizadas
- Filtragem por periodo (data de emissao)
- Verificacao de notas faltantes na sequencia numerica
- Identificacao de notas e pedidos duplicados
- Analise cruzada com Relatorios 65 e ECF Log (opcional)
- Exportacao de relatorios detalhados em Excel

## Relatorios Gerados

### 1. Analise NFCe Mensal
**Arquivo:** `CNPJ-AAAAMMDD_HHMM-Analise_NFCe_MM_AAAA.xlsx`

Relatorio mensal contendo:

| Aba | Descricao |
|-----|-----------|
| **Dados_Principais** | Todas as notas do mes com detalhes: CNPJ, Data, Serie, Status, NFCe, Pedido, Valor, Chave, etc. |
| **Resumo_por_Serie** | Totalizacao por serie: quantidade de notas, valor total, processadas, canceladas e seus respectivos valores |
| **Notas_Faltantes** | Lista de numeros de NFCe faltantes na sequencia do mes |
| **Estatisticas** | Metricas do mes: total de notas, valores, quantidade por status, etc. |

### 2. Notas Faltantes Consolidado
**Arquivo:** `CNPJ-AAAAMMDD_HHMM-Notas_Faltantes_MM-AAAA.xlsx`

Relatorio consolidado de todas as notas faltantes no periodo:

| Aba | Descricao |
|-----|-----------|
| **Notas_Faltantes** | Lista completa de NFCes faltantes com Serie e Numero |
| **Resumo_por_Serie** | Quantidade de notas faltantes por serie |
| **Sequencias_Analisadas** | Intervalos analisados por serie (inicio e fim) |

### 3. Analise NFCe Consolidado (quando ha multiplos meses)
**Arquivo:** `CNPJ-AAAAMMDD_HHMM-Analise_NFCe_Consolidado_MM-AAAA.xlsx`

Visao consolidada de todos os meses processados:

| Aba | Descricao |
|-----|-----------|
| **Dados_Consolidados** | Todas as notas do periodo |
| **Resumo_Mensal** | Totalizacao por mes |
| **Arquivos_Gerados** | Lista de arquivos mensais gerados |

### 4. Analise Cruzada Mensal (quando configurado Relatorios 65)
**Arquivo:** `CNPJ-AAAAMMDD_HHMM-Analise_Cruzada_MM_AAAA.xlsx`

Comparacao entre XMLs, Relatorio 65 e ECF Log:

| Aba | Descricao |
|-----|-----------|
| **XML_Analise** | Dados dos XMLs processados |
| **ECF_Log_Analise** | Dados da ECF Log (se banco configurado) |
| **Relatorio_65_Analise** | Dados do Relatorio 65 |
| **Resumo_Mes** | Inconsistencias encontradas no mes |

### 5. Analise Cruzada Consolidado
**Arquivo:** `CNPJ-AAAAMMDD_HHMM-Analise_Cruzada_Consolidado_MM-AAAA.xlsx`

Consolidacao da analise cruzada:

| Aba | Descricao |
|-----|-----------|
| **XML_Consolidado** | Todos os XMLs do periodo |
| **ECF_Log_Consolidado** | Todos os registros ECF Log |
| **Relatorio_65_Consolidado** | Todos os registros do Relatorio 65 |
| **Resumo_Inconsistencias** | Resumo de todas as inconsistencias encontradas |

## Nomenclatura dos Arquivos

Todos os arquivos seguem o padrao:
```
CNPJ-AAAAMMDD_HHMM-NomeDoRelatorio.xlsx
```

Onde:
- **CNPJ**: CNPJ do emitente (extraido automaticamente dos XMLs)
- **AAAAMMDD_HHMM**: Data e hora da geracao do relatorio
- **NomeDoRelatorio**: Tipo do relatorio gerado

**Exemplo:** `12345678000190-20250115_1430-Analise_NFCe_12_2025.xlsx`

## Como Usar

### 1. Faça o download do app
- Faça o download do app em /dist/Analizador_XMLs_Fiscais_v... (clique sobre o arquivo e depois em Raw para baixar ou copie o repositório com git clone)
- A versão atual é a 1.0.

### 2. Configuracoes Obrigatorias

- **Pasta dos XMLs**: Diretorio contendo os arquivos XML fiscais (busca recursiva em subpastas)
- **Pasta de Analises**: Diretorio onde os relatorios serao salvos
- **Periodo**: Data de inicio e fim para filtrar os XMLs

### 3. Configuracoes Opcionais

- **Pasta dos Relatorios 65**: Para realizar analise cruzada com relatorios do sistema
- **Banco de Dados**: Para analise cruzada com ECF Log
  - Nome do Banco
  - Usuario
  - Senha

### 4. Execucao

1. Preencha as configuracoes
2. Digite as datas (apenas numeros, as barras sao inseridas automaticamente)
3. Clique em "Processar XMLs"
4. Acompanhe o progresso no Log de Processamento
5. Os arquivos serao salvos na pasta de analises configurada

## Tipos de XML Processados

### Notas Enviadas (NFe/NFCe)
```xml
<nfeProc>
  <NFe>
    <infNFe>
      <ide>
        <dhEmi>2025-11-21T09:03:54-03:00</dhEmi>
      </ide>
      <emit>
        <CNPJ>12345678000190</CNPJ>
      </emit>
    </infNFe>
  </NFe>
</nfeProc>
```

### Notas Canceladas (Evento)
```xml
<procEventoNFe>
  <evento>
    <infEvento>
      <tpEvento>110111</tpEvento>
      <chNFe>...</chNFe>
      <dhEvento>2025-11-21T10:00:00-03:00</dhEvento>
    </infEvento>
  </evento>
</procEventoNFe>
```

### Notas Inutilizadas
```xml
<ProcInutNFe>
  <retInutNFe>
    <infInut>
      <dhRecbto>2025-11-21T08:00:00-03:00</dhRecbto>
      <nNFIni>100</nNFIni>
      <nNFFin>110</nNFFin>
    </infInut>
  </retInutNFe>
</ProcInutNFe>
```

## Status das Notas

| Status | Descricao |
|--------|-----------|
| **Processada** | Nota fiscal autorizada normalmente |
| **Cancelada** | Nota fiscal cancelada (evento 110111 ou 110112) |
| **Inutilizada** | Numero de nota inutilizado |

## Requisitos

- Windows 10 ou superior
- Para usar integracao com banco de dados: ODBC Driver 17 for SQL Server

## Instalacao

O executavel `Analisador_XMLs_Fiscais.exe` e standalone e nao requer instalacao de Python ou outras dependencias.

## Build (Para Desenvolvedores)

Consulte o arquivo [README_BUILD.md](README_BUILD.md) para instrucoes de como gerar o executavel a partir do codigo fonte.

## Estrutura do Projeto

```
Processa-xml/
├── app_gui.py           # Interface grafica
├── processa_xml.py      # Logica de processamento
├── config.py            # Configuracoes
├── build_windows.py     # Script de build
├── requirements.txt     # Dependencias Python
├── README.md            # Este arquivo
└── README_BUILD.md      # Instrucoes de build
```

## Suporte

Em caso de problemas, verifique:

1. Se todas as pastas configuradas existem e sao acessiveis
2. Se as datas estao corretas (formato DD/MM/AAAA)
3. Se ha XMLs no periodo especificado
4. Os logs na area de "Log de Processamento" da interface
5. Se a pasta de analises e diferente da pasta de relatorios
