# Changelog

Todas as mudanças notáveis do Analisador de XMLs Fiscais serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.2.0] - 2026-01-26

### Adicionado
- Nova aba **Notas_Duplicadas** nos relatorios de Analise NFCe (mensal e consolidado)
  - Lista notas emitidas para o mesmo pedido
  - Identifica automaticamente a nota correta (prioriza status Processada, depois menor numero)
  - Colunas: CNPJ, Data, Mod, Serie, Status, NFCe, Pedido, Valor, TipoEnv, Chave, Qtd NFCe Rep, NFCe Correta, Chave Correta

### Corrigido
- Script de build atualizado para compatibilidade com console Windows (removidos caracteres especiais)

## [1.1.0] - 2026-01-20

### Adicionado
- Suporte para XMLs autorizados e nao aprovados
- Configuracoes para ambiente local

### Melhorado
- ValidadorXMLNFe agora processa ambos os tipos de XML

## [1.0.0] - 2026-01-19

### Adicionado
- Primeira versão oficial com versionamento
- Informações de versão embarcadas no executável (.exe)
- Arquivo CHANGELOG.md para rastreamento de versões

### Melhorado
- Arquivo de notas faltantes agora é exportado ordenado por Série e NFCe
