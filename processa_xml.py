import pandas as pd
import xml.etree.ElementTree as ET
import os
import re
from pathlib import Path
from datetime import datetime, date
import sqlalchemy
import glob
import config


class ValidadorXMLNFe:
    def __init__(self, diretorio_xml=None, data_inicio=None, data_fim=None):
        """
        Inicializa o validador de XMLs NFe/NFCe

        Args:
            diretorio_xml (str, optional): Caminho para o diretório. Se None, usa PATH_XML do config
            data_inicio (str ou date, optional): Data de início do período
            data_fim (str ou date, optional): Data de fim do período
        """
        # Usa configuração padrão se não especificado
        self.diretorio_xml = diretorio_xml or config.PATH_XML
        self.data_inicio = self._converter_data(data_inicio)
        self.data_fim = self._converter_data(data_fim)
        self.cnpj_emit = None  # CNPJ do emitente extraído dos XMLs

        print(f"📁 Diretório XML configurado: {self.diretorio_xml}")
        
        self.df_principal = pd.DataFrame(columns=[
            'CNPJ', 'Data', 'Mod', 'Serie', 'Status', 'NFCe', 'Pedido',
            'Valor', 'TipoEnv', 'Versao', 'Chave', 'Protocolo',
            'DtRecebimento', 'CPF'
        ])
        
        self.notas_canceladas = pd.DataFrame(columns=[
            'CNPJ', 'Data', 'Mod', 'Serie', 'Status', 'NFCe', 'Pedido',
            'Valor', 'TipoEnv', 'Versao', 'Chave', 'Protocolo',
            'DtRecebimento', 'CPF'
        ])



    def _converter_data(self, data):
        """
        Converte string ou objeto date para datetime
        """
        if data is None:
            return None
        if isinstance(data, str):
            return datetime.strptime(data, '%Y-%m-%d').date()
        if isinstance(data, date):
            return data
        return None

    def _gerar_prefixo_arquivo(self):
        """
        Gera o prefixo para os arquivos de saída no formato:
        CNPJ-aaaammdd_hhmm-
        O prefixo é cacheado para garantir consistência em uma mesma execução.
        """
        # Se já existe um prefixo cacheado, retorna ele
        if hasattr(self, '_prefixo_cache') and self._prefixo_cache:
            return self._prefixo_cache

        if self.cnpj_emit:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            self._prefixo_cache = f"{self.cnpj_emit}-{timestamp}-"
            return self._prefixo_cache
        return ""

    def obter_lista_xmls(self):
        """
        Obtém lista de arquivos XML no diretório e subdiretórios, 
        filtrando por período de criação se especificado
        """
        arquivos_xml = []
        pastas_processadas = []
        
        # Busca recursiva em todas as subpastas
        for root, dirs, files in os.walk(self.diretorio_xml):
            pastas_processadas.append(root)
            
            for arquivo in files:
                if arquivo.lower().endswith('.xml'):
                    caminho_completo = os.path.join(root, arquivo)
                    
                    # Verifica o filtro de data se especificado
                    if self._arquivo_no_periodo(caminho_completo):
                        arquivos_xml.append(caminho_completo)
        
        print(f"Pastas processadas: {len(pastas_processadas)}")
        for pasta in pastas_processadas:
            print(f"  - {pasta}")
        
        if self.data_inicio or self.data_fim:
            periodo_str = f"Período: {self.data_inicio or 'início'} até {self.data_fim or 'fim'}"
            print(f"Filtro aplicado - {periodo_str}")
        
        return arquivos_xml
    
    def _arquivo_no_periodo(self, caminho_arquivo):
        """
        Verifica se o arquivo está dentro do período especificado
        usando a data de emissão do XML (<dhEmi>)
        """
        if not self.data_inicio and not self.data_fim:
            return True

        try:
            # Parse do XML para extrair a data de emissão
            tree = ET.parse(caminho_arquivo)
            root = tree.getroot()

            # Define namespace
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

            # Busca o campo dhEmi
            dh_emi = root.find('.//nfe:dhEmi', ns)

            if dh_emi is None:
                # Se não encontrou com namespace, tenta sem
                dh_emi = root.find('.//dhEmi')

            if dh_emi is not None and dh_emi.text:
                # Extrai a data do formato ISO 8601 (2025-11-21T09:03:54-03:00)
                data_emissao_str = dh_emi.text.split('T')[0]
                data_emissao = datetime.strptime(data_emissao_str, '%Y-%m-%d').date()

                # Verifica se está dentro do período
                if self.data_inicio and data_emissao < self.data_inicio:
                    return False
                if self.data_fim and data_emissao > self.data_fim:
                    return False

                return True
            else:
                # Se não encontrou dhEmi, inclui o arquivo (comportamento padrão)
                return True

        except Exception as e:
            # Em caso de erro ao ler o XML, inclui o arquivo
            print(f"⚠️  Erro ao verificar data de emissão do arquivo {caminho_arquivo}: {e}")
            return True
    

    
    def processar_notas_canceladas(self, lista_xmls):
        """
        Processa notas canceladas nos XMLs de evento
        Estrutura: procEventoNFe/evento/infEvento
        Identifica eventos de cancelamento (tpEvento 110111 ou 110112)
        """
        print("Processando notas canceladas...")

        dados_notas = []
        for arquivo_xml in lista_xmls:
            try:
                tree = ET.parse(arquivo_xml)
                root = tree.getroot()

                # Busca elemento infEvento dentro de evento
                inf_evento = root.find('.//{http://www.portalfiscal.inf.br/nfe}infEvento')

                if inf_evento is not None:
                    # Verifica se é um evento de cancelamento
                    tp_evento_elem = inf_evento.find('.//{http://www.portalfiscal.inf.br/nfe}tpEvento')

                    # Processa apenas se for cancelamento (110111 ou 110112)
                    if tp_evento_elem is not None and tp_evento_elem.text in ['110111', '110112']:
                        # Extrai dados diretamente do XML
                        cnpj_elem = inf_evento.find('.//{http://www.portalfiscal.inf.br/nfe}CNPJ')
                        chave_elem = inf_evento.find('.//{http://www.portalfiscal.inf.br/nfe}chNFe')
                        data_elem = inf_evento.find('.//{http://www.portalfiscal.inf.br/nfe}dhEvento')
                        det_evento_elem = inf_evento.find('.//{http://www.portalfiscal.inf.br/nfe}detEvento/{http://www.portalfiscal.inf.br/nfe}descEvento')

                        if all(elem is not None for elem in [cnpj_elem, chave_elem, data_elem]):
                            # Filtra por período se configurado
                            if self.data_inicio or self.data_fim:
                                try:
                                    data_evento_str = data_elem.text.split('T')[0]
                                    data_evento = datetime.strptime(data_evento_str, '%Y-%m-%d').date()

                                    if self.data_inicio and data_evento < self.data_inicio:
                                        continue
                                    if self.data_fim and data_evento > self.data_fim:
                                        continue
                                except (ValueError, AttributeError):
                                    pass  # Se não conseguir parsear a data, inclui o registro

                            chave_text = chave_elem.text

                            # Extrai informações da chave (já que não temos as tags separadas no evento)
                            modelo = chave_text[20:22] if len(chave_text) >= 22 else ""
                            serie = chave_text[22:25] if len(chave_text) >= 25 else ""
                            numero = chave_text[25:34] if len(chave_text) >= 34 else ""
                            tipo_env = "Normal" if len(chave_text) >= 35 and chave_text[34] == '1' else "Contingência"

                            # Status descritivo ou padrão
                            status_desc = det_evento_elem.text if det_evento_elem is not None else "Cancelada"

                            nova_linha = {
                                'CNPJ': cnpj_elem.text,
                                'Data': data_elem.text,
                                'Mod': modelo,
                                'Serie': serie,
                                'Status': status_desc,
                                'NFCe': numero,
                                'Pedido': None,
                                'Valor': 0,
                                'TipoEnv': tipo_env,
                                'Versao': None,
                                'Chave': chave_text,
                                'Protocolo': None,
                                'DtRecebimento': None,
                                'CPF': ''
                            }

                            dados_notas.append(nova_linha)

                                   
            except Exception as e:
                print(f"Erro ao processar {arquivo_xml}: {e}")
        if dados_notas:
            self.notas_canceladas = pd.DataFrame(dados_notas)

            # Valida se há duplicados
            if self.notas_canceladas.duplicated(subset=['Chave']).any():
                notas_canceladas_duplicadas = self.notas_canceladas[self.notas_canceladas.duplicated(subset=['NFCe'], keep=False)]
                print(f"⚠️  Atenção: Foram encontradoss {len(notas_canceladas_duplicadas)} de notas canceladas com a mesma chave. Verifique os arquivos nas pastas.")
            

        else:
            # Mantém DataFrame vazio com as colunas corretas
            self.notas_canceladas = pd.DataFrame(columns=[
                'CNPJ', 'Data', 'Mod', 'Serie', 'Status', 'NFCe', 'Pedido',
                'Valor', 'TipoEnv', 'Versao', 'Chave', 'Protocolo',
                'DtRecebimento', 'CPF'
        ])
            
        print(f"Total de notas canceladas encontradas: {len(self.notas_canceladas)}")


    def processar_notas_enviadas(self, lista_xmls):
        """
        Processa notas enviadas (NFe/NFCe)
        Estrutura: nfeProc/NFe/infNFe (autorizado) ou NFe/infNFe (envio)
        """
        print("Processando notas enviadas...")
        dados_notas = []

        for arquivo_xml in lista_xmls:
            try:
                tree = ET.parse(arquivo_xml)
                root = tree.getroot()

                # Verifica se o root é o próprio elemento NFe (XML de envio)
                # ou se NFe é um descendente (XML autorizado com nfeProc)
                ns = '{http://www.portalfiscal.inf.br/nfe}'
                root_tag = root.tag.replace(ns, '')

                if root_tag == 'NFe':
                    # XML de envio - o root já é o NFe
                    nfe = root
                    xml_autorizado = False
                else:
                    # XML autorizado - busca NFe como descendente
                    nfe = root.find(f'.//{ns}NFe')
                    xml_autorizado = True

                if nfe is not None:
                    inf_nfe = nfe.find(f'.//{ns}infNFe')
                    ide = nfe.find(f'.//{ns}ide')
                    emit = nfe.find(f'.//{ns}emit')
                    total = nfe.find(f'.//{ns}total/{ns}ICMSTot')
                    inf_adic = nfe.find(f'.//{ns}infAdic')

                    if all(elem is not None for elem in [inf_nfe, ide, emit]):
                        # Extrai CNPJ do emitente (apenas uma vez)
                        if self.cnpj_emit is None:
                            cnpj_emit_elem = emit.find(f'.//{ns}CNPJ')
                            if cnpj_emit_elem is not None and cnpj_emit_elem.text:
                                self.cnpj_emit = cnpj_emit_elem.text
                                print(f"📋 CNPJ do emitente identificado: {self.cnpj_emit}")

                        # Extrai chave
                        chave = inf_nfe.get('Id', '')
                        if chave.startswith('NFe'):
                            chave = chave[3:]

                        # Extrai informações diretamente das tags
                        mod_elem = ide.find(f'.//{ns}mod')
                        serie_elem = ide.find(f'.//{ns}serie')
                        nnf_elem = ide.find(f'.//{ns}nNF')
                        tpemis_elem = ide.find(f'.//{ns}tpEmis')
                        
                        modelo = mod_elem.text if mod_elem is not None else ""
                        serie = serie_elem.text if serie_elem is not None else ""
                        numero = nnf_elem.text if nnf_elem is not None else ""
                        tipo_emis = tpemis_elem.text if tpemis_elem is not None else "1"
                        tipo_env = "Normal" if tipo_emis == "1" else "Contingência"
                        
                        # Verifica se está cancelada de forma inline (retEvento no mesmo arquivo)
                        # Define status inicial baseado no tipo de XML
                        if xml_autorizado:
                            status = "Processada"
                        else:
                            status = "Pendente"  # XML de envio sem autorização da Sefaz

                        # Primeiro, verifica se há retEvento indicando cancelamento inline
                        ret_evento = root.find(f'.//{ns}retEvento/{ns}infEvento')
                        if ret_evento is not None:
                            tp_evento_elem = ret_evento.find(f'.//{ns}tpEvento')
                            if tp_evento_elem is not None and tp_evento_elem.text in ['110111', '110112']:
                                status = "Cancelada"

                        # Se não foi cancelada inline, verifica se há XML de cancelamento separado
                        if status in ["Processada", "Pendente"] and chave in self.notas_canceladas['Chave'].values:
                            status = "Cancelada"
                        
                        # Extrai número do pedido se existir
                        pedido = None
                        if inf_adic is not None:
                            inf_cpl = inf_adic.find(f'.//{ns}infCpl')
                            if inf_cpl is not None:
                                # Extrai todo o texto, incluindo elementos filhos
                                texto_completo = ''.join(inf_cpl.itertext())
                                if texto_completo:
                                    # Aceita "Pedido 283351" ou "Pedido:288963"
                                    match = re.search(r'Pedido:?\s*(\d+)', texto_completo, re.IGNORECASE)
                                    if match:
                                        pedido = int(match.group(1))

                        # Extrai valor total
                        valor = 0
                        if total is not None:
                            v_nf = total.find(f'.//{ns}vNF')
                            if v_nf is not None:
                                valor = float(v_nf.text)

                        # Extrai protocolo e data de recebimento (somente para XMLs autorizados)
                        protocolo = None
                        dt_recebimento = None
                        if xml_autorizado:
                            prot_nfe = root.find(f'.//{ns}protNFe/{ns}infProt')
                            if prot_nfe is not None:
                                nrot = prot_nfe.find(f'.//{ns}nProt')
                                dh_recbto = prot_nfe.find(f'.//{ns}dhRecbto')
                                if nrot is not None:
                                    protocolo = nrot.text
                                if dh_recbto is not None:
                                    dt_recebimento = dh_recbto.text

                        # Extrai versão
                        versao = None
                        ver_proc = ide.find(f'.//{ns}verProc')
                        if ver_proc is not None:
                            versao = ver_proc.text

                        # Extrai data de emissão
                        data_emissao = None
                        dh_emi = ide.find(f'.//{ns}dhEmi')
                        if dh_emi is not None:
                            data_emissao = dh_emi.text

                        # Extrai CNPJ
                        cnpj = None
                        cnpj_elem = emit.find(f'.//{ns}CNPJ')
                        if cnpj_elem is not None:
                            cnpj = cnpj_elem.text
                        
                        nova_linha = {
                            'CNPJ': cnpj,
                            'Data': data_emissao,
                            'Mod': modelo,
                            'Serie': serie,
                            'Status': status,
                            'NFCe': numero,
                            'Pedido': pedido,
                            'Valor': valor,
                            'TipoEnv': tipo_env,
                            'Versao': versao,
                            'Chave': chave,  # Removida a aspas simples no início
                            'Protocolo': protocolo,
                            'DtRecebimento': dt_recebimento,
                            'CPF': ''
                        }
                        
                        dados_notas.append(nova_linha)
            
            except Exception as e:
                print(f"Erro ao processar {arquivo_xml}: {e}")

        if dados_notas:
            self.df_principal = pd.DataFrame(dados_notas)

            # Valida se há duplicados
            if self.df_principal.duplicated(subset=['NFCe']).any():
                notas_duplicadas = self.df_principal[self.df_principal.duplicated(subset=['NFCe'], keep=False)]
                print(f"⚠️  Atenção: Foram encontrados {len(notas_duplicadas)} arquivos duplicados de notas com a mesma chave. Verifique os arquivos nas pastas.")
            
        else:
            # Mantém DataFrame vazio com as colunas corretas
            self.df_principal = pd.DataFrame(columns=[
                'CNPJ', 'Data', 'Mod', 'Serie', 'Status', 'NFCe', 'Pedido',
                'Valor', 'TipoEnv', 'Versao', 'Chave', 'Protocolo',
                'DtRecebimento', 'CPF'
            ])

        print(f"Total de notas processadas: {len(self.df_principal)}")


    def processar_notas_inutilizadas(self, lista_xmls):
        """
        Processa notas inutilizadas
        Estrutura: ProcInutNFe/retInutNFe/infInut
        """
        print("Processando notas inutilizadas...")
        dados_notas = []

        for arquivo_xml in lista_xmls:
            try:
                tree = ET.parse(arquivo_xml)
                root = tree.getroot()

                # Busca elemento inutNFe para extrair a chave
                inut_nfe = root.find('.//{http://www.portalfiscal.inf.br/nfe}inutNFe')
                # Busca retInutNFe para extrair os dados processados
                ret_inut_nfe = root.find('.//{http://www.portalfiscal.inf.br/nfe}retInutNFe/{http://www.portalfiscal.inf.br/nfe}infInut')

                if inut_nfe is not None and ret_inut_nfe is not None:
                    # Extrai chave do elemento inutNFe
                    chave = inut_nfe.get('Id', '')
                    if chave.startswith('ID'):
                        chave = chave[2:]

                    # Extrai dados diretamente das tags do retInutNFe
                    cnpj_elem = ret_inut_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}CNPJ')
                    dh_recbto_elem = ret_inut_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}dhRecbto')
                    mod_elem = ret_inut_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}mod')
                    serie_elem = ret_inut_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}serie')
                    n_nf_ini_elem = ret_inut_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}nNFIni')
                    n_nf_fin_elem = ret_inut_nfe.find('.//{http://www.portalfiscal.inf.br/nfe}nNFFin')

                    if all(elem is not None for elem in [cnpj_elem, dh_recbto_elem, mod_elem, serie_elem, n_nf_ini_elem, n_nf_fin_elem]):
                        # Filtra por período se configurado
                        if self.data_inicio or self.data_fim:
                            try:
                                data_recbto_str = dh_recbto_elem.text.split('T')[0]
                                data_recbto = datetime.strptime(data_recbto_str, '%Y-%m-%d').date()

                                if self.data_inicio and data_recbto < self.data_inicio:
                                    continue
                                if self.data_fim and data_recbto > self.data_fim:
                                    continue
                            except (ValueError, AttributeError):
                                pass  # Se não conseguir parsear a data, inclui o registro

                        # Inutilização única
                        if n_nf_ini_elem.text == n_nf_fin_elem.text:
                            nova_linha = {
                                'CNPJ': cnpj_elem.text,
                                'Data': dh_recbto_elem.text,
                                'Mod': mod_elem.text,
                                'Serie': serie_elem.text,
                                'Status': 'Inutilizada',
                                'NFCe': n_nf_ini_elem.text,
                                'Pedido': None,
                                'Valor': 0,
                                'TipoEnv': None,
                                'Versao': None,
                                'Chave': chave,
                                'Protocolo': None,
                                'DtRecebimento': None,
                                'CPF': ''
                            }

                            dados_notas.append(nova_linha)

                        # Inutilização múltipla
                        else:
                            inicio = int(n_nf_ini_elem.text)
                            fim = int(n_nf_fin_elem.text)

                            for num_nf in range(inicio, fim + 1):
                                nova_linha = {
                                    'CNPJ': cnpj_elem.text,
                                    'Data': dh_recbto_elem.text,
                                    'Mod': mod_elem.text,
                                    'Serie': serie_elem.text,
                                    'Status': 'Inutilizada',
                                    'NFCe': str(num_nf),
                                    'Pedido': None,
                                    'Valor': 0,
                                    'TipoEnv': None,
                                    'Versao': None,
                                    'Chave': chave,
                                    'Protocolo': None,
                                    'DtRecebimento': None,
                                    'CPF': ''
                                }

                                dados_notas.append(nova_linha)
                                           
            except Exception as e:
                print(f"Erro ao processar {arquivo_xml}: {e}")  
        if dados_notas:
            df_inutilizadas = pd.DataFrame(dados_notas)

            # Valida se há duplicados
            if self.df_principal.duplicated(subset=['NFCe']).any():
                notas_duplicadas = self.df_principal[self.df_principal.duplicated(subset=['NFCe'], keep=False)]
                print(f"⚠️  Atenção: Foram encontrados {len(notas_duplicadas)} arquivos duplicados de notas com a mesma chave. Verifique os arquivos nas pastas.")
            
            print(f"Total de notas inutilizadas encontradas: {len(df_inutilizadas)}")
            # Adiciona ao DataFrame principal
            self.df_principal = pd.concat([self.df_principal, df_inutilizadas], ignore_index=True)


    def verificar_notas_faltantes(self):
        """
        Verifica notas faltantes na sequência
        Inicia o intervalo a partir da primeira NFCe processada (status != 'Inutilizada')
        """
        print("Verificando notas faltantes...")
        
        # Converte colunas para numéricas
        self.df_principal['Serie'] = pd.to_numeric(self.df_principal['Serie'], errors='coerce')
        self.df_principal['NFCe'] = pd.to_numeric(self.df_principal['NFCe'], errors='coerce')
        
        series_unicas = self.df_principal['Serie'].dropna().unique()
        lista_faltantes = []
        
        for serie in series_unicas:
            df_serie = self.df_principal[self.df_principal['Serie'] == serie]
            
            # Filtra apenas notas processadas (status != 'Inutilizada') para determinar o início do intervalo
            df_serie_processadas = df_serie[df_serie['Status'] != 'Inutilizada']
            numeros_processados = df_serie_processadas['NFCe'].dropna().astype(int)
            
            if len(numeros_processados) > 0:
                # Início: primeira NFCe processada (não inutilizada)
                min_nfce = numeros_processados.min()
                # Fim: última NFCe de qualquer status
                max_nfce = df_serie['NFCe'].dropna().astype(int).max()
                
                # Cria sequência completa do intervalo
                sequencia_completa = set(range(min_nfce, max_nfce + 1))
                
                # Remove todas as NFCes existentes (processadas + inutilizadas + canceladas)
                numeros_existentes = set(df_serie['NFCe'].dropna().astype(int))
                
                # Faltantes são os que não existem no intervalo
                faltantes = sequencia_completa - numeros_existentes
                
                for faltante in faltantes:
                    lista_faltantes.append({'Serie': serie, 'NFCe': faltante})

        if not lista_faltantes:
            return pd.DataFrame()

        return pd.DataFrame(lista_faltantes).sort_values(['Serie', 'NFCe']).reset_index(drop=True)
    

    def identificar_duplicatas(self):
        """
        Identifica notas e pedidos duplicados
        """
        print("Identificando duplicatas...")
        
        # Notas duplicadas
        nfce_duplicadas = self.df_principal[self.df_principal.duplicated(subset=['NFCe'], keep=False)]['NFCe']
        self.df_principal['NFDuplicada'] = self.df_principal['NFCe'].isin(nfce_duplicadas).map({True: 'Sim', False: ''})
        
        # Pedidos duplicados
        df_com_pedido = self.df_principal[self.df_principal['Pedido'].notna()]
        pedidos_duplicados = df_com_pedido[df_com_pedido.duplicated(subset=['Pedido'], keep=False)]['Pedido']
        self.df_principal['PedDuplicado'] = self.df_principal['Pedido'].isin(pedidos_duplicados).map({True: 'Sim', False: ''})
        
        # Retorna estatísticas
        nfs_duplicadas = self.df_principal[self.df_principal['NFDuplicada'] == 'Sim']
        valor_nfs_duplicadas = nfs_duplicadas['Valor'].sum()
        qtd_nfs_duplicadas = len(nfs_duplicadas)
        
        peds_duplicados = self.df_principal[self.df_principal['PedDuplicado'] == 'Sim']
        valor_peds_duplicados = peds_duplicados['Valor'].sum()
        
        return {
            'nfs_duplicadas': qtd_nfs_duplicadas,
            'valor_nfs_duplicadas': valor_nfs_duplicadas,
            'valor_pedidos_duplicados': valor_peds_duplicados
        }

    def processar_todos_xmls(self, salvar_automatico=False):  # Mudança aqui: padrão False
        """
        Executa todo o processamento
        """
        print(f"Iniciando processamento no diretório: {self.diretorio_xml}")
        if self.data_inicio or self.data_fim:
            print(f"Período de filtro: {self.data_inicio or 'início'} até {self.data_fim or 'fim'}")
        
        # Obtém lista de XMLs
        lista_xmls = self.obter_lista_xmls()
        print(f"Encontrados {len(lista_xmls)} arquivos XML no período especificado")
        
        if not lista_xmls:
            print("Nenhum arquivo XML encontrado no período especificado!")
            # Retorna valores padrão consistentes
            if salvar_automatico:
                return pd.DataFrame(), {
                    'nfs_duplicadas': 0,
                    'valor_nfs_duplicadas': 0,
                    'valor_pedidos_duplicados': 0
                }, []
            else:
                return pd.DataFrame(), {
                    'nfs_duplicadas': 0,
                    'valor_nfs_duplicadas': 0,
                    'valor_pedidos_duplicados': 0
                }
        
        # Processa cada tipo de XML
        self.processar_notas_canceladas(lista_xmls)
        self.processar_notas_enviadas(lista_xmls)
        self.processar_notas_inutilizadas(lista_xmls)
        
        # Adiciona notas canceladas que não estão nas enviadas
        chaves_enviadas = set(self.df_principal['Chave'].str.replace("'", "", regex=False))
        canceladas_nao_enviadas = self.notas_canceladas[~self.notas_canceladas['Chave'].isin(chaves_enviadas)]
        
        if not canceladas_nao_enviadas.empty:
            canceladas_nao_enviadas = canceladas_nao_enviadas.copy()
            canceladas_nao_enviadas['Chave'] = "'" + canceladas_nao_enviadas['Chave'].astype(str)
            self.df_principal = pd.concat([self.df_principal, canceladas_nao_enviadas], ignore_index=True)
        
        # Converte tipos e ordena
        self.df_principal['Serie'] = pd.to_numeric(self.df_principal['Serie'], errors='coerce')
        self.df_principal['NFCe'] = pd.to_numeric(self.df_principal['NFCe'], errors='coerce')
        self.df_principal['Pedido'] = pd.to_numeric(self.df_principal['Pedido'], errors='coerce')
        self.df_principal['Valor'] = pd.to_numeric(self.df_principal['Valor'], errors='coerce')
        
        self.df_principal = self.df_principal.sort_values(['Serie', 'NFCe']).reset_index(drop=True)
        
        # Verifica faltantes e duplicatas
        notas_faltantes = self.verificar_notas_faltantes()
        stats_duplicatas = self.identificar_duplicatas()
        
        # Exibe estatísticas
        valor_total = self.df_principal['Valor'].sum()
        print(f"\nEstatísticas:")
        print(f"Total de registros processados: {len(self.df_principal)}")
        print(f"Valor total: R$ {valor_total:,.2f}")
        print(f"Notas faltantes: {len(notas_faltantes)}")
        print(f"Notas duplicadas: {stats_duplicatas['nfs_duplicadas']}")
        print(f"Valor das notas duplicadas: R$ {stats_duplicatas['valor_nfs_duplicadas']:,.2f}")
        print(f"Valor dos pedidos duplicados: R$ {stats_duplicatas['valor_pedidos_duplicados']:,.2f}")
        
        # Retorno consistente baseado no parâmetro
        if salvar_automatico:
            arquivos_salvos = self.salvar_resultados()
            return notas_faltantes, stats_duplicatas, arquivos_salvos
        else:
            return notas_faltantes, stats_duplicatas


    def salvar_resultados(self):
        """
        Salva os resultados separados por mês na pasta de análises
        Cria um arquivo Excel para cada mês contendo dados daquele período
        """
        if self.df_principal.empty:
            print("Nenhum dado para salvar. Execute o processamento primeiro.")
            return
        
        print("Salvando resultados por mês...")
        
        # Garante que a pasta de análises existe
        os.makedirs(config.PATH_ANALISES, exist_ok=True)
        
        # Converte coluna Data para datetime para facilitar agrupamento
        df_trabalho = self.df_principal.copy()
        
        # Extrai apenas a parte da data (sem horário) e converte para datetime
        df_trabalho['DataLimpa'] = pd.to_datetime(
            df_trabalho['Data'].str[:10], 
            format='%Y-%m-%d', 
            errors='coerce'
        )
        
        # Remove registros sem data válida
        df_trabalho = df_trabalho.dropna(subset=['DataLimpa'])
        
        if df_trabalho.empty:
            print("Nenhum registro com data válida encontrado.")
            return
        
        # Cria coluna ano-mês para agrupamento
        df_trabalho['AnoMes'] = df_trabalho['DataLimpa'].dt.to_period('M')
        
        # ✅ GERA ARQUIVO DE NOTAS FALTANTES CONSOLIDADO
        notas_faltantes = self.verificar_notas_faltantes()
        self._salvar_notas_faltantes(notas_faltantes)
        
        # Agrupa por mês
        meses_unicos = df_trabalho['AnoMes'].unique()
        
        arquivos_salvos = []
        
        for mes in meses_unicos:
            # Calcula total de processadas do mês
            total_processada_mes = df_trabalho[
                (df_trabalho['AnoMes'] == mes) & (df_trabalho['Status'] == 'Processada')
            ]['Valor'].sum()

            # Filtra dados do mês
            df_mes = df_trabalho[df_trabalho['AnoMes'] == mes].copy()
            
            # Remove colunas auxiliares
            df_mes = df_mes.drop(['DataLimpa', 'AnoMes'], axis=1)
            
            # ✅ CALCULA NOTAS FALTANTES DO MÊS ESPECÍFICO
            notas_faltantes_mes = self._calcular_faltantes_mes(df_mes)
            
            # Formata nome do arquivo
            ano = mes.year
            mes_num = mes.month
            prefixo = self._gerar_prefixo_arquivo()
            nome_arquivo = f"{prefixo}Analise_NFCe_{mes_num:02d}_{ano}.xlsx"
            caminho_arquivo = os.path.join(config.PATH_ANALISES, nome_arquivo)
            
            # Salva arquivo Excel
            try:
                with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
                    # Aba principal com todos os dados
                    df_mes.to_excel(writer, sheet_name='Dados_Principais', index=False)
                    
                    # Aba com resumo por série
                    resumo_serie = df_mes.groupby('Serie').agg({
                        'NFCe': 'count',
                        'Valor': 'sum',
                        'Status': [
                            lambda x: (x == 'Processada').sum(),
                            lambda x: (x == 'Cancelada').sum()
                        ]
                    }).round(2)

                    # Achata as colunas multi-level
                    resumo_serie.columns = ['Qtd_Notas', 'Valor_Total', 'Processadas', 'Canceladas']

                    # Adiciona valores apenas para processadas e canceladas
                    resumo_serie['Valor_Processada'] = df_mes.groupby('Serie').apply(
                        lambda x: x[x['Status'] == 'Processada']['Valor'].sum(),
                    include_groups=False).round(2)

                    resumo_serie['Valor_Cancelada'] = df_mes.groupby('Serie').apply(
                        lambda x: x[x['Status'] == 'Cancelada']['Valor'].sum(),
                        include_groups=False
                    ).round(2)

                    
                    # Reordena as colunas para melhor visualização
                    colunas_ordenadas = [
                        'Qtd_Notas', 'Valor_Total', 
                        'Processadas', 'Valor_Processada',
                        'Canceladas', 'Valor_Cancelada'
                    ]
                    resumo_serie = resumo_serie[colunas_ordenadas]

                    # Adiciona valores por status
                    for status in ['Processada', 'Cancelada']:
                        resumo_serie[f'Valor_{status}'] = df_mes.groupby('Serie').apply(
                            lambda x: x[x['Status'] == status]['Valor'].sum(), include_groups=False
                        ).round(2)

                    # Reordena as colunas para melhor visualização
                    colunas_ordenadas = [
                        'Qtd_Notas', 'Valor_Total',
                        'Processadas', 'Valor_Processada',
                        'Canceladas', 'Valor_Cancelada'
                    ]
                    resumo_serie = resumo_serie[colunas_ordenadas]

                    resumo_serie.to_excel(writer, sheet_name='Resumo_por_Serie')
                    
                    # ✅ ABA COM NOTAS FALTANTES DO MÊS
                    if not notas_faltantes_mes.empty:
                        notas_faltantes_mes.to_excel(writer, sheet_name='Notas_Faltantes', index=False)
                    else:
                        # Cria aba vazia se não há faltantes
                        pd.DataFrame({'Mensagem': ['Nenhuma nota faltante encontrada neste mês']}).to_excel(
                            writer, sheet_name='Notas_Faltantes', index=False
                        )
                    
                    # Aba com estatísticas do mês
                    stats = self._gerar_estatisticas_mes(df_mes, mes)
                    # Adiciona estatística de notas faltantes
                    stats['Notas Faltantes no Mês'] = len(notas_faltantes_mes)
                    
                    stats_df = pd.DataFrame(list(stats.items()), columns=['Métrica', 'Valor'])
                    stats_df.to_excel(writer, sheet_name='Estatisticas', index=False)
                
                arquivos_salvos.append({
                    'mes': f"{mes_num:02d}/{ano}",
                    'arquivo': nome_arquivo,
                    'caminho': caminho_arquivo,
                    'registros': len(df_mes),
                    'valor_total': total_processada_mes,
                    'notas_faltantes': len(notas_faltantes_mes)
                })
                
                print(f"Salvo: {nome_arquivo} ({len(df_mes)} registros, {len(notas_faltantes_mes)} faltantes)")
                
            except Exception as e:
                print(f"Erro ao salvar arquivo {nome_arquivo}: {e}")
        
        # Relatório final
        print(f"\nResultados salvos em: {config.PATH_ANALISES}")
        print("Resumo dos arquivos criados:")
        print("-" * 70)
        
        total_faltantes = 0
        for arquivo in arquivos_salvos:
            total_faltantes += arquivo['notas_faltantes']
            print(f"📁 {arquivo['arquivo']}")
            print(f"   Mês: {arquivo['mes']}")
            print(f"   Registros: {arquivo['registros']}")
            print(f"   Valor Total: R$ {arquivo['valor_total']:,.2f}")
            print(f"   Notas Faltantes: {arquivo['notas_faltantes']}")
            print("")
        
        print(f"📊 Total de notas faltantes no período: {total_faltantes}")
        
        # Salva também um arquivo consolidado se houver múltiplos meses
        if len(arquivos_salvos) > 1:
            self._salvar_consolidado(df_trabalho, arquivos_salvos)
        
        return arquivos_salvos

    def _calcular_faltantes_mes(self, df_mes):
        """
        Calcula notas faltantes específicas do mês
        """
        if df_mes.empty:
            return pd.DataFrame()
        
        series_unicas = df_mes['Serie'].dropna().unique()
        lista_faltantes = []
        
        for serie in series_unicas:
            df_serie = df_mes[df_mes['Serie'] == serie]
            numeros_nfce = df_serie['NFCe'].dropna().astype(int)
            
            if len(numeros_nfce) > 0:
                min_nfce = numeros_nfce.min()
                max_nfce = numeros_nfce.max()
                sequencia_completa = set(range(min_nfce, max_nfce + 1))
                numeros_existentes = set(numeros_nfce)
                
                faltantes = sequencia_completa - numeros_existentes
                
                for faltante in faltantes:
                    lista_faltantes.append({
                        'Serie': serie, 
                        'NFCe': faltante
                    })
        
        if not lista_faltantes:
            return pd.DataFrame()

        return pd.DataFrame(lista_faltantes).sort_values(['Serie', 'NFCe']).reset_index(drop=True)

    def _salvar_notas_faltantes(self, notas_faltantes):
        """
        Salva arquivo Excel consolidado das notas faltantes
        """
        if notas_faltantes.empty:
            print("✅ Nenhuma nota faltante encontrada no período!")
            return
        
        try:
            # Nome do arquivo
            prefixo = self._gerar_prefixo_arquivo()
            if self.data_inicio and self.data_fim:
                data_inicio_str = self.data_inicio.strftime('%m-%Y')
                data_fim_str = self.data_fim.strftime('%m-%Y')
                if data_inicio_str == data_fim_str:
                    nome_arquivo = f"{prefixo}Notas_Faltantes_{data_inicio_str}.xlsx"
                else:
                    nome_arquivo = f"{prefixo}Notas_Faltantes_{data_inicio_str}_a_{data_fim_str}.xlsx"
            else:
                nome_arquivo = f"{prefixo}Notas_Faltantes_Consolidado.xlsx"

            caminho_arquivo = os.path.join(config.PATH_ANALISES, nome_arquivo)

            # Copia os dados das notas faltantes
            notas_faltantes_completo = notas_faltantes.copy()

            # Reordena colunas
            colunas_ordenadas = ['Serie', 'NFCe']
            if 'Sequencial_Inicio' in notas_faltantes_completo.columns:
                colunas_ordenadas.extend(['Sequencial_Inicio', 'Sequencial_Fim'])
            
            notas_faltantes_completo = notas_faltantes_completo[colunas_ordenadas]
            
            with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
                # Aba principal com todas as notas faltantes
                notas_faltantes_completo.to_excel(writer, sheet_name='Notas_Faltantes', index=False)

                # Aba com resumo por série
                resumo_faltantes = notas_faltantes_completo.groupby(['Serie']).agg({
                    'NFCe': 'count'
                }).reset_index()
                resumo_faltantes.columns = ['Serie', 'Qtd_Faltantes']
                resumo_faltantes.to_excel(writer, sheet_name='Resumo_por_Serie', index=False)

                # Aba com sequências problemáticas
                if 'Sequencial_Inicio' in notas_faltantes_completo.columns:
                    sequencias = notas_faltantes_completo.groupby(['Serie']).agg({
                        'Sequencial_Inicio': 'min',
                        'Sequencial_Fim': 'max',
                        'NFCe': 'count'
                    }).reset_index()
                    sequencias.columns = ['Serie', 'Primeiro_Numero', 'Ultimo_Numero', 'Qtd_Faltantes']
                    sequencias.to_excel(writer, sheet_name='Sequencias_Analisadas', index=False)
            
            print(f"📋 Arquivo de notas faltantes salvo: {nome_arquivo}")
            print(f"   Total de notas faltantes: {len(notas_faltantes)}")
            
            
        except Exception as e:
            print(f"Erro ao salvar arquivo de notas faltantes: {e}")

    def _gerar_estatisticas_mes(self, df_mes, periodo):
        """
        Gera estatísticas específicas do mês
        """
        # Calcula valores por status (sem inutilizadas que não têm valor)
        valor_processadas = df_mes[df_mes['Status'] == 'Processada']['Valor'].sum()
        valor_canceladas = df_mes[df_mes['Status'] == 'Cancelada']['Valor'].sum()
        
        
        stats = {
            'Período': str(periodo),
            'Total de Registros': len(df_mes),
            
            # Quantidade por status
            'Notas Processadas': len(df_mes[df_mes['Status'] == 'Processada']),
            'Notas Canceladas': len(df_mes[df_mes['Status'] == 'Cancelada']),
            'Notas Inutilizadas': len(df_mes[df_mes['Status'] == 'Inutilizada']),
            
            # Valor por status (sem inutilizadas)
            'Valor Processadas (R$)': round(valor_processadas, 2),
            'Valor Canceladas (R$)': round(valor_canceladas, 2),
            
            # Outras estatísticas
            'Séries Ativas': df_mes['Serie'].nunique(),
            'Pedidos com NFCe': df_mes['Pedido'].notna().sum(),
            'Valor Médio por Nota': round(df_mes[df_mes['Valor'] > 0]['Valor'].mean(), 2),
            'Maior Valor': round(df_mes['Valor'].max(), 2),
            'Menor Valor': round(df_mes[df_mes['Valor'] > 0]['Valor'].min(), 2)
        }

        return stats

    def _salvar_consolidado(self, df_trabalho, arquivos_salvos):
        """
        Salva um arquivo consolidado com todos os meses
        """
        try:
            # Remove colunas auxiliares
            df_consolidado = df_trabalho.drop(['DataLimpa', 'AnoMes'], axis=1)

            # Nome do arquivo consolidado baseado no período
            prefixo = self._gerar_prefixo_arquivo()
            data_inicio = df_trabalho['DataLimpa'].min().strftime('%m-%Y')
            data_fim = df_trabalho['DataLimpa'].max().strftime('%m-%Y')

            if data_inicio == data_fim:
                nome_consolidado = f"{prefixo}Analise_NFCe_Consolidado_{data_inicio}.xlsx"
            else:
                nome_consolidado = f"{prefixo}Analise_NFCe_Consolidado_{data_inicio}_a_{data_fim}.xlsx"

            caminho_consolidado = os.path.join(config.PATH_ANALISES, nome_consolidado)
            
            with pd.ExcelWriter(caminho_consolidado, engine='openpyxl') as writer:
                # Dados consolidados
                df_consolidado.to_excel(writer, sheet_name='Dados_Consolidados', index=False)
                
                # Resumo por mês
                df_trabalho['MesAno'] = df_trabalho['DataLimpa'].dt.strftime('%m/%Y')
                resumo_mensal = df_trabalho.groupby('MesAno').agg({
                    'NFCe': 'count',
                    'Valor': 'sum'
                }).round(2)
                resumo_mensal.columns = ['Qtd_Notas', 'Valor_Total']
                resumo_mensal.to_excel(writer, sheet_name='Resumo_Mensal')
                
                # Lista de arquivos gerados
                df_arquivos = pd.DataFrame(arquivos_salvos)
                df_arquivos.to_excel(writer, sheet_name='Arquivos_Gerados', index=False)
            
            print(f"📋 Arquivo consolidado salvo: {nome_consolidado}")
            
        except Exception as e:
            print(f"Erro ao salvar arquivo consolidado: {e}")

    # Adicione este método à classe ValidadorXMLNFe

    def executar_analise_completa_com_cruzamento(self, salvar_automatico=True):
        """
        Executa processamento completo incluindo análise cruzada
        """
        # Processa XMLs primeiro SEM salvar automaticamente
        notas_faltantes, stats_duplicatas = self.processar_todos_xmls(salvar_automatico=False)
        
        # Salva resultados básicos se solicitado
        arquivos_salvos = None
        if salvar_automatico:
            arquivos_salvos = self.salvar_resultados()
        
        # Executa análise cruzada
        print("\n" + "="*50)
        print("INICIANDO ANÁLISE CRUZADA")
        print("="*50)
        
        try:
            analise_cruzada = AnaliseCruzada(self)
            resultados_cruzados = analise_cruzada.executar_analise_completa()
            
            if salvar_automatico:
                caminho_analise = analise_cruzada.salvar_analise_cruzada(resultados_cruzados)
                
                return {
                    'notas_faltantes': notas_faltantes,
                    'stats_duplicatas': stats_duplicatas,
                    'arquivos_mensais': arquivos_salvos,
                    'analise_cruzada': resultados_cruzados,
                    'arquivo_analise_cruzada': caminho_analise
                }
            else:
                return {
                    'notas_faltantes': notas_faltantes,
                    'stats_duplicatas': stats_duplicatas,
                    'analise_cruzada': resultados_cruzados
                }
                
        except Exception as e:
            print(f"Erro na análise cruzada: {e}")
            import traceback
            traceback.print_exc()
            
            # Retorna resultado parcial em caso de erro
            return {
                'notas_faltantes': notas_faltantes,
                'stats_duplicatas': stats_duplicatas,
                'arquivos_mensais': arquivos_salvos,
                'analise_cruzada': None,
                'erro_analise_cruzada': str(e)
            }



class AnaliseCruzada:
    def __init__(self, validador_xml):
        """
        Inicializa a análise cruzada
        
        Args:
            validador_xml: Instância do ValidadorXMLNFe já processado
        """
        self.validador = validador_xml
        self.df_xml = validador_xml.df_principal.copy()
        self.df_relatorio_65 = pd.DataFrame()
        self.df_ecf_log = pd.DataFrame()
        
        # Prepara chaves do XML para comparação
        if not self.df_xml.empty:
            self.df_xml['ChaveLimpa'] = self.df_xml['Chave'].str.replace("'", "")
            
            # Formata Serie e NFCe no XML
            serie_xml = self.df_xml['Serie'].fillna('NA').apply(
                lambda x: str(int(float(x))) if pd.notna(x) else 'NA'
            )
            nfce_xml = self.df_xml['NFCe'].fillna('NA').apply(
                lambda x: str(int(float(x))) if pd.notna(x) else 'NA'
            )
            self.df_xml['Serie_Nro'] = serie_xml + '_' + nfce_xml
    
    def ler_relatorio_65(self):
        """
        Lê os arquivos do Relatório 65 correspondentes ao período
        """
        print("Lendo arquivos do Relatório 65...")
        print(f"Pasta configurada: {config.PATH_RELATORIOS_65}")
        print(f"Pasta existe: {os.path.exists(config.PATH_RELATORIOS_65)}")
        
        if self.df_xml.empty:
            print("Nenhum dado XML para processar")
            return
        
        # Lista todos os arquivos na pasta para debug
        try:
            arquivos_na_pasta = [f for f in os.listdir(config.PATH_RELATORIOS_65) 
                               if f.lower().endswith(('.xlsx', '.xls'))]
            print(f"Arquivos Excel encontrados na pasta ({len(arquivos_na_pasta)}):")
            for arquivo in arquivos_na_pasta[:5]:
                print(f"  - {arquivo}")
            if len(arquivos_na_pasta) > 5:
                print(f"  ... e mais {len(arquivos_na_pasta) - 5} arquivos")
        except Exception as e:
            print(f"Erro ao listar pasta: {e}")
            return
        
        # Extrai datas do XML para identificar meses necessários
        df_temp = self.df_xml.copy()
        df_temp['DataLimpa'] = pd.to_datetime(df_temp['Data'].str[:10], errors='coerce')
        meses_necessarios = df_temp['DataLimpa'].dt.to_period('M').unique()
        
        print(f"Meses necessários para busca: {meses_necessarios}")
        
        arquivos_65 = []
        for mes in meses_necessarios:
            if pd.isna(mes):
                continue
            
            # Múltiplos padrões de busca
            padroes_teste = [
                f"*{mes.strftime('%Y%m')}*.xlsx",
                f"*{mes.strftime('%Y%m')}*.xls",
                f"*{mes.strftime('%m%Y')}*.xlsx",
                f"*{mes.strftime('%m-%Y')}*.xlsx",
                f"*{mes.strftime('%Y-%m')}*.xlsx",
                f"*{mes.year}*{mes.month:02d}*.xlsx",
                f"*{mes.month:02d}*{mes.year}*.xlsx"
            ]
            
            print(f"Buscando arquivos para {mes}:")
            
            for padrao in padroes_teste:
                caminho_busca = os.path.join(config.PATH_RELATORIOS_65, padrao)
                arquivos_encontrados = glob.glob(caminho_busca)
                
                if arquivos_encontrados:
                    print(f"  Padrão '{padrao}': {len(arquivos_encontrados)} arquivo(s)")
                    for arquivo in arquivos_encontrados:
                        print(f"    - {os.path.basename(arquivo)}")
                    arquivos_65.extend(arquivos_encontrados)
                    break
            else:
                print(f"  NENHUM arquivo encontrado para {mes}")
        
        # Lê e combina todos os arquivos
        dfs_65 = []
        for arquivo in arquivos_65:
            try:
                df_temp = pd.read_excel(arquivo, skiprows=2)
                df_temp['Arquivo_Origem'] = os.path.basename(arquivo)
                dfs_65.append(df_temp)
                print(f"Lido: {os.path.basename(arquivo)} - {len(df_temp)} registros")
            except Exception as e:
                print(f"Erro ao ler {arquivo}: {e}")
        
        if dfs_65:
            self.df_relatorio_65 = pd.concat(dfs_65, ignore_index=True)
            
            # Adiciona coluna Serie_Nro para Relatório 65
            if 'Serie NFCe' in self.df_relatorio_65.columns and 'Num NFCe' in self.df_relatorio_65.columns:
                # Trata Serie NFCe (remove .0 desnecessários)
                serie_formatada = self.df_relatorio_65['Serie NFCe'].fillna('NA').apply(
                    lambda x: str(int(float(x))) if pd.notna(x) and str(x) != 'NA' else 'NA')
    
            # Trata Num NFCe
            nfce_formatada = self.df_relatorio_65['Num NFCe'].fillna('NA').apply(
                lambda x: str(int(float(x))) if pd.notna(x) and str(x) != 'NA' else 'NA')
            
            # Cria Serie_Nro
            self.df_relatorio_65['Serie_Nro'] = serie_formatada + '_' + nfce_formatada
            
            print(f"Total de registros do Relatório 65: {len(self.df_relatorio_65)}")
        else:
            print("Nenhum arquivo do Relatório 65 foi carregado")
    
    def consultar_ecf_log(self):
        """
        Consulta a tabela ECF Log do banco de dados
        Somente executa se o banco de dados estiver configurado
        """
        # Verifica se o banco está configurado
        if not config.USE_DB or not config.DB_CONNECTION_STRING:
            print("⚠️  Banco de dados não configurado. Pulando consulta ECF Log.")
            self.df_ecf_log = pd.DataFrame()
            return

        print("Consultando ECF Log no banco de dados...")

        if self.df_xml.empty:
            print("Nenhum dado XML para processar")
            return
        
        try:
            # Determina período para consulta
            df_temp = self.df_xml.copy()
            df_temp['DataLimpa'] = pd.to_datetime(df_temp['Data'].str[:10], errors='coerce')
            
            data_inicio = df_temp['DataLimpa'].min().strftime('%Y-%m-%d %H:%M:%S')
            data_fim = df_temp['DataLimpa'].max().strftime('%Y-%m-%d 23:59:59')
            
            # Query SQL
            query = f"""
            SELECT [Data/Hora Emissao], [Data Movimento], NFCE AS Eh_NFCe, 
                   COO as Nro_NFCE, Num_Serie_NF, [Cupom Fiscal], NumeroCupom, 
                   [Total Documento], Cancelado, [Nº Caixa], chave_nfe, 
                   ProtocoloSefaz, StatusNFCe, MotivoRejeicaoNFCe, MotivoRejeicaoNFe 
            FROM [ECF Log] e 
            WHERE e.[Data/Hora Emissao] >= '{data_inicio}' 
              AND e.[Data/Hora Emissao] <= '{data_fim}' 
            ORDER BY E.[Data/Hora Emissao] DESC
            """
            
            # Executa consulta
            engine = sqlalchemy.create_engine(config.DB_CONNECTION_STRING)
            self.df_ecf_log = pd.read_sql(query, engine)
            
            # Adiciona coluna Serie_Nro para ECF Log
            if not self.df_ecf_log.empty:
                # Formata Serie e NFCe na ECF Log
                serie_ecf = self.df_ecf_log['Num_Serie_NF'].fillna('NA').apply(
                    lambda x: str(int(float(x))) if pd.notna(x) else 'NA'
                )
                nfce_ecf = self.df_ecf_log['Nro_NFCE'].fillna('NA').apply(
                    lambda x: str(int(float(x))) if pd.notna(x) else 'NA'
                )
                self.df_ecf_log['Serie_Nro'] = serie_ecf + '_' + nfce_ecf
            
            print(f"Consultados {len(self.df_ecf_log)} registros da ECF Log")
            
        except Exception as e:
            print(f"Erro na consulta ECF Log: {e}")
            self.df_ecf_log = pd.DataFrame()
    
    def criar_analise_relatorio_65(self):
        """
        Cria análise do Relatório 65 com comparações
        """
        if self.df_relatorio_65.empty:
            return pd.DataFrame()
        
        df_analise = self.df_relatorio_65.copy()
        
        # Preparar dados para comparação
        ecf_cupons = set(self.df_ecf_log['NumeroCupom']) if not self.df_ecf_log.empty else set()
        ecf_chaves = set(self.df_ecf_log['chave_nfe'].dropna()) if not self.df_ecf_log.empty else set()
        ecf_serie_nro = set(self.df_ecf_log['Serie_Nro']) if not self.df_ecf_log.empty else set()
        
        xml_chaves = set(self.df_xml['ChaveLimpa']) if not self.df_xml.empty else set()
        xml_serie_nro = set(self.df_xml['Serie_Nro']) if not self.df_xml.empty else set()
        
        # Adiciona colunas de análise usando os nomes corretos
        if 'Num Cupom' in df_analise.columns:
            df_analise['Pedido consta na ECF Log?'] = df_analise['Num Cupom'].isin(ecf_cupons).map({True: 'SIM', False: 'NÃO'})
        else:
            df_analise['Pedido consta na ECF Log?'] = 'N/A - Coluna não encontrada'
        
        if 'Chave NFe' in df_analise.columns:
            df_analise['Chave consta na ECF Log?'] = df_analise['Chave NFe'].isin(ecf_chaves).map({True: 'SIM', False: 'NÃO'})
            df_analise['Tem XML?'] = df_analise['Chave NFe'].isin(xml_chaves).map({True: 'SIM', False: 'NÃO'})
        else:
            df_analise['Chave consta na ECF Log?'] = 'N/A - Coluna não encontrada'
            df_analise['Tem XML?'] = 'N/A - Coluna não encontrada'
        
        # Validações por Serie_Nro
        df_analise['Serie_Nro existe na ECF Log?'] = df_analise['Serie_Nro'].isin(ecf_serie_nro).map({True: 'SIM', False: 'NÃO'})
        df_analise['Serie_Nro existe no XML?'] = df_analise['Serie_Nro'].isin(xml_serie_nro).map({True: 'SIM', False: 'NÃO'})
        
        return df_analise
        
    def criar_analise_ecf_log(self):
        """
        Cria análise da ECF Log com comparações
        """
        if self.df_ecf_log.empty:
            return pd.DataFrame()
        
        df_analise = self.df_ecf_log.copy()
        
        # Preparar dados para comparação do Relatório 65
        rel65_cupons = set()
        rel65_chaves = set()
        rel65_serie_nro = set()
        
        if not self.df_relatorio_65.empty:
            if 'Num Cupom' in self.df_relatorio_65.columns:
                rel65_cupons = set(self.df_relatorio_65['Num Cupom'].dropna())
            if 'Chave NFe' in self.df_relatorio_65.columns:
                rel65_chaves = set(self.df_relatorio_65['Chave NFe'].dropna())
            if 'Serie_Nro' in self.df_relatorio_65.columns:
                rel65_serie_nro = set(self.df_relatorio_65['Serie_Nro'])
        
        xml_chaves = set(self.df_xml['ChaveLimpa']) if not self.df_xml.empty else set()
        xml_serie_nro = set(self.df_xml['Serie_Nro']) if not self.df_xml.empty else set()
        
        # Adiciona colunas de análise
        df_analise['Pedido consta no 65?'] = df_analise['NumeroCupom'].isin(rel65_cupons).map({True: 'SIM', False: 'NÃO'})
        df_analise['Chave consta no 65?'] = df_analise['chave_nfe'].isin(rel65_chaves).map({True: 'SIM', False: 'NÃO'})
        df_analise['Tem XML?'] = df_analise['chave_nfe'].isin(xml_chaves).map({True: 'SIM', False: 'NÃO'})
        
        # Validações por Serie_Nro
        df_analise['Serie_Nro existe no 65?'] = df_analise['Serie_Nro'].isin(rel65_serie_nro).map({True: 'SIM', False: 'NÃO'})
        df_analise['Serie_Nro existe no XML?'] = df_analise['Serie_Nro'].isin(xml_serie_nro).map({True: 'SIM', False: 'NÃO'})
        
        # Coluna "NFCe Duplicada?"
        # Conta quantas vezes cada NFCe aparece
        nfce_counts = df_analise['Nro_NFCE'].value_counts()
        df_analise['NFCe Duplicada?'] = df_analise['Nro_NFCE'].map(
            lambda x: 'SIM' if nfce_counts.get(x, 0) > 1 else 'NÃO'
        )
        return df_analise

    def criar_analise_xml(self):
        """
        Cria análise do XML com comparações
        """
        if self.df_xml.empty:
            return pd.DataFrame()
        
        df_analise = self.df_xml.copy()
        
            # Converte campos de data para datetime
        df_analise['Data'] = pd.to_datetime(df_analise['Data'], errors='coerce').dt.tz_localize(None)
        df_analise['DtRecebimento'] = pd.to_datetime(df_analise['DtRecebimento'], errors='coerce').dt.tz_localize(None)

        # Preparar dados para comparação
        ecf_cupons = set(self.df_ecf_log['NumeroCupom']) if not self.df_ecf_log.empty else set()
        ecf_chaves = set(self.df_ecf_log['chave_nfe'].dropna()) if not self.df_ecf_log.empty else set()
        ecf_serie_nro = set(self.df_ecf_log['Serie_Nro']) if not self.df_ecf_log.empty else set()
        
        rel65_cupons = set()
        rel65_chaves = set()
        rel65_serie_nro = set()
        
        if not self.df_relatorio_65.empty:
            if 'Num Cupom' in self.df_relatorio_65.columns:
                rel65_cupons = set(self.df_relatorio_65['Num Cupom'].dropna())
            if 'Chave NFe' in self.df_relatorio_65.columns:
                rel65_chaves = set(self.df_relatorio_65['Chave NFe'].dropna())
            if 'Serie_Nro' in self.df_relatorio_65.columns:
                rel65_serie_nro = set(self.df_relatorio_65['Serie_Nro'])
        
        # Adiciona colunas de análise
        df_analise['Pedido consta na ECF Log?'] = df_analise['Pedido'].isin(ecf_cupons).map({True: 'SIM', False: 'NÃO'})
        df_analise['Chave consta na ECF Log?'] = df_analise['ChaveLimpa'].isin(ecf_chaves).map({True: 'SIM', False: 'NÃO'})
        df_analise['Pedido consta no 65?'] = df_analise['Pedido'].isin(rel65_cupons).map({True: 'SIM', False: 'NÃO'})
        df_analise['Chave consta no 65?'] = df_analise['ChaveLimpa'].isin(rel65_chaves).map({True: 'SIM', False: 'NÃO'})
        
        # Validações por Serie_Nro
        df_analise['Serie_Nro existe na ECF Log?'] = df_analise['Serie_Nro'].isin(ecf_serie_nro).map({True: 'SIM', False: 'NÃO'})
        df_analise['Serie_Nro existe no 65?'] = df_analise['Serie_Nro'].isin(rel65_serie_nro).map({True: 'SIM', False: 'NÃO'})
        
        #Coluna "Duplicação Cancelada?"
        def verificar_duplicacao_cancelada(row):
            pedido = row['Pedido']
            if pd.isna(pedido):
                return 'N/A'
            
            # Filtra todos os registros com o mesmo pedido
            registros_pedido = df_analise[df_analise['Pedido'] == pedido]
            
            if len(registros_pedido) <= 1:
                return 'N/A'  # Não é duplicado
            
            # Conta autorizados e cancelados
            qtd_autorizados = len(registros_pedido[registros_pedido['Status'] == 'Processada'])
            qtd_cancelados = len(registros_pedido[registros_pedido['Status'] == 'Cancelada'])
            
            # Aplica a regra: se (autorizados - cancelados) <= 0, então SIM
            if (qtd_autorizados - qtd_cancelados) <= 0:
                return 'SIM'
            else:
                return 'NÃO'
        
        df_analise['Duplicação Cancelada?'] = df_analise.apply(verificar_duplicacao_cancelada, axis=1)
        
        # Remove a coluna 'Chave' original e renomeia 'ChaveLimpa' para 'Chave'
        if 'Chave' in df_analise.columns:
            df_analise = df_analise.drop('Chave', axis=1)
        if 'ChaveLimpa' in df_analise.columns:
            df_analise = df_analise.rename(columns={'ChaveLimpa': 'Chave'})
        
        return df_analise
    
    def gerar_relatorio_inconsistencias(self):
        """
        Gera relatório detalhado das inconsistências encontradas
        """
        relatorio = {
            'total_xml': len(self.df_xml),
            'total_ecf_log': len(self.df_ecf_log),
            'total_relatorio_65': len(self.df_relatorio_65),
            'inconsistencias': {}
        }
        
        # Análise de chaves
        xml_chaves = set(self.df_xml['ChaveLimpa']) if not self.df_xml.empty else set()
        ecf_chaves = set(self.df_ecf_log['chave_nfe'].dropna()) if not self.df_ecf_log.empty else set()
        
        rel65_chaves = set()
        if not self.df_relatorio_65.empty and 'Chave NFe' in self.df_relatorio_65.columns:
            rel65_chaves = set(self.df_relatorio_65['Chave NFe'].dropna())
        
        # Inconsistências de chaves
        relatorio['inconsistencias']['chaves_xml_nao_ecf'] = len(xml_chaves - ecf_chaves)
        relatorio['inconsistencias']['chaves_ecf_nao_xml'] = len(ecf_chaves - xml_chaves)
        relatorio['inconsistencias']['chaves_xml_nao_65'] = len(xml_chaves - rel65_chaves)
        relatorio['inconsistencias']['chaves_65_nao_xml'] = len(rel65_chaves - xml_chaves)
        relatorio['inconsistencias']['chaves_ecf_nao_65'] = len(ecf_chaves - rel65_chaves)
        relatorio['inconsistencias']['chaves_65_nao_ecf'] = len(rel65_chaves - ecf_chaves)
        
        # Análise de Serie_Nro
        xml_serie_nro = set(self.df_xml['Serie_Nro']) if not self.df_xml.empty else set()
        ecf_serie_nro = set(self.df_ecf_log['Serie_Nro']) if not self.df_ecf_log.empty else set()
        
        rel65_serie_nro = set()
        if not self.df_relatorio_65.empty and 'Serie_Nro' in self.df_relatorio_65.columns:
            rel65_serie_nro = set(self.df_relatorio_65['Serie_Nro'])
        
        relatorio['inconsistencias']['serie_nro_xml_nao_ecf'] = len(xml_serie_nro - ecf_serie_nro)
        relatorio['inconsistencias']['serie_nro_ecf_nao_xml'] = len(ecf_serie_nro - xml_serie_nro)
        relatorio['inconsistencias']['serie_nro_xml_nao_65'] = len(xml_serie_nro - rel65_serie_nro)
        relatorio['inconsistencias']['serie_nro_65_nao_xml'] = len(rel65_serie_nro - xml_serie_nro)
        
        # Análise de cupons/pedidos
        xml_pedidos = set(self.df_xml['Pedido'].dropna()) if not self.df_xml.empty else set()
        ecf_cupons = set(self.df_ecf_log['NumeroCupom']) if not self.df_ecf_log.empty else set()
        
        rel65_cupons = set()
        if not self.df_relatorio_65.empty and 'Num Cupom' in self.df_relatorio_65.columns:
            rel65_cupons = set(self.df_relatorio_65['Num Cupom'].dropna())
        
        relatorio['inconsistencias']['pedidos_xml_nao_ecf'] = len(xml_pedidos - ecf_cupons)
        relatorio['inconsistencias']['pedidos_ecf_nao_xml'] = len(ecf_cupons - xml_pedidos)
        relatorio['inconsistencias']['pedidos_xml_nao_65'] = len(xml_pedidos - rel65_cupons)
        relatorio['inconsistencias']['pedidos_65_nao_xml'] = len(rel65_cupons - xml_pedidos)
        
        return relatorio
    
    def executar_analise_completa(self):
        """
        Executa toda a análise cruzada
        """
        print("=== INICIANDO ANÁLISE CRUZADA ===")
        
        # Lê dados
        self.ler_relatorio_65()
        self.consultar_ecf_log()
        
        # Cria análises
        df_analise_65 = self.criar_analise_relatorio_65()
        df_analise_ecf = self.criar_analise_ecf_log()
        df_analise_xml = self.criar_analise_xml()
        
        # Gera relatório de inconsistências
        relatorio_inconsistencias = self.gerar_relatorio_inconsistencias()
        
        # Exibe resumo
        print("\n=== RESUMO DA ANÁLISE ===")
        print(f"Total XML: {relatorio_inconsistencias['total_xml']}")
        print(f"Total ECF Log: {relatorio_inconsistencias['total_ecf_log']}")
        print(f"Total Relatório 65: {relatorio_inconsistencias['total_relatorio_65']}")
        
        print("\n=== INCONSISTÊNCIAS ENCONTRADAS ===")
        inc = relatorio_inconsistencias['inconsistencias']
        print(f"Chaves no XML que não estão na ECF Log: {inc['chaves_xml_nao_ecf']}")
        print(f"Chaves na ECF Log que não estão no XML: {inc['chaves_ecf_nao_xml']}")
        print(f"Serie_Nro no XML que não estão na ECF Log: {inc['serie_nro_xml_nao_ecf']}")
        print(f"Serie_Nro na ECF Log que não estão no XML: {inc['serie_nro_ecf_nao_xml']}")
        
        return {
            'analise_65': df_analise_65,
            'analise_ecf': df_analise_ecf,
            'analise_xml': df_analise_xml,
            'relatorio_inconsistencias': relatorio_inconsistencias
        }
    
    def _remover_timezone_dataframe(self, df):
        """
        Remove timezone de todas as colunas datetime do DataFrame
        """
        df_copy = df.copy()
        
        for col in df_copy.columns:
            if df_copy[col].dtype.name.startswith('datetime'):
                try:
                    # Se tem timezone, remove
                    if hasattr(df_copy[col].dtype, 'tz') and df_copy[col].dtype.tz is not None:
                        df_copy[col] = df_copy[col].dt.tz_localize(None)
                    # Se é object mas contém datetime, tenta converter
                    elif df_copy[col].dtype == 'object':
                        try:
                            df_copy[col] = pd.to_datetime(df_copy[col], errors='ignore').dt.tz_localize(None)
                        except:
                            pass
                except Exception as e:
                    print(f"Aviso: Não foi possível remover timezone da coluna {col}: {e}")
        
        return df_copy

    def salvar_analise_cruzada_mensal(self, resultados):
        """
        Salva análises cruzadas separadas por mês
        """
        print("Salvando análises cruzadas por mês...")
        
        if resultados['analise_xml'].empty:
            print("Nenhum dado XML para processar mensalmente")
            return []
        
        # Extrai meses dos dados XML
        df_xml_temp = resultados['analise_xml'].copy()

        # Remove timezone dos campos datetime antes de processar
        for col in df_xml_temp.columns:
            if df_xml_temp[col].dtype == 'datetime64[ns, UTC]' or 'datetime' in str(df_xml_temp[col].dtype):
                if hasattr(df_xml_temp[col].dtype, 'tz') and df_xml_temp[col].dtype.tz is not None:
                    df_xml_temp[col] = df_xml_temp[col].dt.tz_localize(None)
        
        # Converte para datetime de forma segura
        try:
            df_xml_temp['DataLimpa'] = pd.to_datetime(df_xml_temp['Data'], errors='coerce')
            
            # Remove timezone se existir
            if hasattr(df_xml_temp['DataLimpa'].dtype, 'tz') and df_xml_temp['DataLimpa'].dtype.tz is not None:
                df_xml_temp['DataLimpa'] = df_xml_temp['DataLimpa'].dt.tz_localize(None)
        except:
            df_xml_temp['DataLimpa'] = pd.to_datetime(df_xml_temp['Data'].astype(str).str[:10], errors='coerce')
        

        df_xml_temp['AnoMes'] = df_xml_temp['DataLimpa'].dt.to_period('M')
        
        meses_unicos = df_xml_temp['AnoMes'].dropna().unique()
        arquivos_mensais = []
        
        for mes in meses_unicos:
            try:
                # Filtra dados do mês
                df_xml_mes = df_xml_temp[df_xml_temp['AnoMes'] == mes].copy()
                df_xml_mes = df_xml_mes.drop(['DataLimpa', 'AnoMes'], axis=1)
                
                # Remove timezone de TODOS os campos datetime antes de salvar
                df_xml_mes = self._remover_timezone_dataframe(df_xml_mes)

                # Filtra outros DataFrames baseado nas chaves do XML do mês
                # Nota: 'ChaveLimpa' foi renomeada para 'Chave' no criar_analise_xml()
                chaves_mes = set(df_xml_mes['Chave'])
                serie_nro_mes = set(df_xml_mes['Serie_Nro'])
                
                # Filtra ECF Log
                df_ecf_mes = pd.DataFrame()
                if not resultados['analise_ecf'].empty:
                    df_ecf_mes = resultados['analise_ecf'][
                        (resultados['analise_ecf']['chave_nfe'].isin(chaves_mes)) |
                        (resultados['analise_ecf']['Serie_Nro'].isin(serie_nro_mes))
                    ].copy()
                    df_ecf_mes = self._remover_timezone_dataframe(df_ecf_mes)
                
                # Filtra Relatório 65
                df_65_mes = pd.DataFrame()
                if not resultados['analise_65'].empty and 'Chave NFe' in resultados['analise_65'].columns:
                    df_65_mes = resultados['analise_65'][
                        (resultados['analise_65']['Chave NFe'].isin(chaves_mes)) |
                        (resultados['analise_65']['Serie_Nro'].isin(serie_nro_mes))
                    ].copy()
                    df_65_mes = self._remover_timezone_dataframe(df_65_mes)
                
                # Nome do arquivo
                ano = mes.year
                mes_num = mes.month
                prefixo = self.validador._gerar_prefixo_arquivo()
                nome_arquivo = f"{prefixo}Analise_Cruzada_{mes_num:02d}_{ano}.xlsx"
                caminho_arquivo = os.path.join(config.PATH_ANALISES, nome_arquivo)
                
                # Salva arquivo Excel
                with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
                    if not df_xml_mes.empty:
                        df_xml_mes.to_excel(writer, sheet_name='XML_Analise', index=False)
                    
                    if not df_ecf_mes.empty:
                        df_ecf_mes.to_excel(writer, sheet_name='ECF_Log_Analise', index=False)
                    
                    if not df_65_mes.empty:
                        df_65_mes.to_excel(writer, sheet_name='Relatorio_65_Analise', index=False)
                    
                    # Resumo do mês
                    resumo_mes = pd.DataFrame([
                        ['Mês', str(mes)],
                        ['Registros XML', len(df_xml_mes)],
                        ['Registros ECF Log', len(df_ecf_mes)],
                        ['Registros Relatório 65', len(df_65_mes)],
                        ['', ''],
                        ['INCONSISTÊNCIAS DO MÊS', ''],
                        ['XML sem correspondência ECF', len(df_xml_mes[df_xml_mes['Chave consta na ECF Log?'] == 'NÃO'])],
                        ['XML sem correspondência 65', len(df_xml_mes[df_xml_mes['Chave consta no 65?'] == 'NÃO'])],
                    ], columns=['Métrica', 'Valor'])
                    
                    resumo_mes.to_excel(writer, sheet_name='Resumo_Mes', index=False)
                
                arquivos_mensais.append({
                    'mes': f"{mes_num:02d}/{ano}",
                    'arquivo': nome_arquivo,
                    'registros_xml': len(df_xml_mes),
                    'registros_ecf': len(df_ecf_mes),
                    'registros_65': len(df_65_mes)
                })
                
                print(f"Salvo: {nome_arquivo}")
                
            except Exception as e:
                print(f"Erro ao salvar análise do mês {mes}: {e}")
        
        return arquivos_mensais
    
    def salvar_analise_cruzada(self, resultados):
        """
        Salva os resultados da análise cruzada em Excel (consolidado e mensais)
        """
        # Salva análises mensais
        arquivos_mensais = self.salvar_analise_cruzada_mensal(resultados)
        
        # Salva consolidado
        nome_arquivo_consolidado = self._salvar_consolidado_cruzada(resultados)
        
        return {
            'arquivo_consolidado': nome_arquivo_consolidado,
            'arquivos_mensais': arquivos_mensais
        }
    
    def _salvar_consolidado_cruzada(self, resultados):
        """
        Salva arquivo consolidado da análise cruzada
        """
        # Nome do arquivo consolidado
        prefixo = self.validador._gerar_prefixo_arquivo()
        if self.validador.data_inicio and self.validador.data_fim:
            data_inicio_str = self.validador.data_inicio.strftime('%m-%Y')
            data_fim_str = self.validador.data_fim.strftime('%m-%Y')
            if data_inicio_str == data_fim_str:
                nome_arquivo = f"{prefixo}Analise_Cruzada_Consolidado_{data_inicio_str}.xlsx"
            else:
                nome_arquivo = f"{prefixo}Analise_Cruzada_Consolidado_{data_inicio_str}_a_{data_fim_str}.xlsx"
        else:
            nome_arquivo = f"{prefixo}Analise_Cruzada_Consolidado_Completo.xlsx"

        caminho_arquivo = os.path.join(config.PATH_ANALISES, nome_arquivo)
        
        try:
            with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
                # Remove timezone de todos os DataFrames antes de salvar
                if not resultados['analise_xml'].empty:
                    df_xml_clean = self._remover_timezone_dataframe(resultados['analise_xml'])
                    df_xml_clean.to_excel(writer, sheet_name='XML_Consolidado', index=False)
                
                if not resultados['analise_ecf'].empty:
                    df_ecf_clean = self._remover_timezone_dataframe(resultados['analise_ecf'])
                    df_ecf_clean.to_excel(writer, sheet_name='ECF_Log_Consolidado', index=False)
                
                if not resultados['analise_65'].empty:
                    df_65_clean = self._remover_timezone_dataframe(resultados['analise_65'])
                    df_65_clean.to_excel(writer, sheet_name='Relatorio_65_Consolidado', index=False)
                
                 
                # Resumo de inconsistências
                inc = resultados['relatorio_inconsistencias']['inconsistencias']
                df_resumo = pd.DataFrame([
                    ['Total XML', resultados['relatorio_inconsistencias']['total_xml']],
                    ['Total ECF Log', resultados['relatorio_inconsistencias']['total_ecf_log']],
                    ['Total Relatório 65', resultados['relatorio_inconsistencias']['total_relatorio_65']],
                    ['', ''],
                    ['INCONSISTÊNCIAS DE CHAVES', ''],
                    ['Chaves no XML que não estão na ECF Log', inc['chaves_xml_nao_ecf']],
                    ['Chaves na ECF Log que não estão no XML', inc['chaves_ecf_nao_xml']],
                    ['Chaves no XML que não estão no Rel. 65', inc['chaves_xml_nao_65']],
                    ['Chaves no Rel. 65 que não estão no XML', inc['chaves_65_nao_xml']],
                    ['', ''],
                    ['INCONSISTÊNCIAS DE SERIE_NRO', ''],
                    ['Serie_Nro no XML que não estão na ECF Log', inc['serie_nro_xml_nao_ecf']],
                    ['Serie_Nro na ECF Log que não estão no XML', inc['serie_nro_ecf_nao_xml']],
                    ['Serie_Nro no XML que não estão no Rel. 65', inc['serie_nro_xml_nao_65']],
                    ['Serie_Nro no Rel. 65 que não estão no XML', inc['serie_nro_65_nao_xml']],
                    ['', ''],
                    ['INCONSISTÊNCIAS DE PEDIDOS/CUPONS', ''],
                    ['Pedidos no XML que não estão na ECF Log', inc['pedidos_xml_nao_ecf']],
                    ['Pedidos na ECF Log que não estão no XML', inc['pedidos_ecf_nao_xml']],
                    ['Pedidos no XML que não estão no Rel. 65', inc['pedidos_xml_nao_65']],
                    ['Pedidos no Rel. 65 que não estão no XML', inc['pedidos_65_nao_xml']],
                ], columns=['Métrica', 'Valor'])
                
                df_resumo.to_excel(writer, sheet_name='Resumo_Inconsistencias', index=False)
            
            print(f"Análise cruzada consolidada salva em: {nome_arquivo}")
            return caminho_arquivo
            
        except Exception as e:
            print(f"Erro ao salvar análise cruzada consolidada: {e}")
            return None


# Função para testar busca do Relatório 65
def testar_busca_relatorio_65():
    """
    Função para testar isoladamente a busca dos relatórios 65
    """
    import config
    import os
    import glob
    
    print("=== TESTE DE BUSCA RELATÓRIO 65 ===")
    print(f"Pasta configurada: {config.PATH_RELATORIOS_65}")
    print(f"Pasta existe: {os.path.exists(config.PATH_RELATORIOS_65)}")
    
    if not os.path.exists(config.PATH_RELATORIOS_65):
        print("ERRO: Pasta não existe!")
        return
    
    # Lista todos os arquivos
    try:
        arquivos = [f for f in os.listdir(config.PATH_RELATORIOS_65) if f.lower().endswith(('.xlsx', '.xls'))]
        print(f"\nArquivos Excel encontrados ({len(arquivos)}):")
        for arquivo in arquivos:
            print(f"  - {arquivo}")
    except Exception as e:
        print(f"Erro ao listar arquivos: {e}")
        return
    
    # Testa padrões para agosto e setembro de 2025
    meses_teste = ['202508', '202509', '08-2025', '09-2025', '2025-08', '2025-09', '082025', '092025']
    
    print(f"\n=== TESTANDO PADRÕES DE BUSCA ===")
    for mes in meses_teste:
        padroes = [
            f"*{mes}*.xlsx",
            f"*{mes}*.xls",
        ]
        
        print(f"\nBuscando para '{mes}':")
        for padrao in padroes:
            caminho_completo = os.path.join(config.PATH_RELATORIOS_65, padrao)
            encontrados = glob.glob(caminho_completo)
            print(f"  {padrao}: {len(encontrados)} arquivo(s)")
            for arquivo in encontrados:
                print(f"    - {os.path.basename(arquivo)}")


# Atualização na função principal do ValidadorXMLNFe
def executar_analise_completa_com_cruzamento(self, salvar_automatico=True):
    """
    Executa processamento completo incluindo análise cruzada
    """
    # Processa XMLs primeiro SEM salvar automaticamente
    notas_faltantes, stats_duplicatas = self.processar_todos_xmls(salvar_automatico=False)
    
    # Salva resultados básicos se solicitado
    arquivos_salvos = None
    if salvar_automatico:
        arquivos_salvos = self.salvar_resultados()
    
    # Executa análise cruzada
    print("\n" + "="*50)
    print("INICIANDO ANÁLISE CRUZADA")
    print("="*50)
    
    try:
        analise_cruzada = AnaliseCruzada(self)
        resultados_cruzados = analise_cruzada.executar_analise_completa()
        
        if salvar_automatico:
            # Salva tanto consolidado quanto mensais
            arquivos_analise = analise_cruzada.salvar_analise_cruzada(resultados_cruzados)
            
            return {
                'notas_faltantes': notas_faltantes,
                'stats_duplicatas': stats_duplicatas,
                'arquivos_mensais': arquivos_salvos,
                'analise_cruzada': resultados_cruzados,
                'arquivo_analise_consolidado': arquivos_analise['arquivo_consolidado'],
                'arquivos_analise_mensais': arquivos_analise['arquivos_mensais']
            }
        else:
            return {
                'notas_faltantes': notas_faltantes,
                'stats_duplicatas': stats_duplicatas,
                'analise_cruzada': resultados_cruzados
            }
            
    except Exception as e:
        print(f"Erro na análise cruzada: {e}")
        import traceback
        traceback.print_exc()
        
        # Retorna resultado parcial em caso de erro
        return {
            'notas_faltantes': notas_faltantes,
            'stats_duplicatas': stats_duplicatas,
            'arquivos_mensais': arquivos_salvos,
            'analise_cruzada': None,
            'erro_analise_cruzada': str(e)
        }


# Exemplo de uso atualizado
def exemplo_analise_completa(data_inicio, data_fim):
    """
    Exemplo de uso da análise completa
    """
    try:
        # Configuração do período
        data_inicio = data_inicio
        data_fim = data_fim
        
        print("INICIANDO ANÁLISE COMPLETA DE NFCE")
        print(f"Período: {data_inicio} a {data_fim}")
        print("="*60)
        
        # Inicializa processador
        validador = ValidadorXMLNFe(data_inicio=data_inicio, data_fim=data_fim)
        
        # Executa análise completa
        resultados = validador.executar_analise_completa_com_cruzamento()
        
        # Relatório final
        print("\n" + "="*60)
        print("RELATÓRIO FINAL")
        print("="*60)
        
        print(f"✓ XMLs processados: {len(validador.df_principal)}")
        print(f"✓ Notas faltantes: {len(resultados['notas_faltantes'])}")
        print(f"✓ Duplicatas encontradas: {resultados['stats_duplicatas']['nfs_duplicadas']}")
        
        if resultados.get('analise_cruzada'):
            inc = resultados['analise_cruzada']['relatorio_inconsistencias']['inconsistencias']
            print(f"✓ Inconsistências XML vs ECF (chaves): {inc['chaves_xml_nao_ecf']}")
            print(f"✓ Inconsistências XML vs ECF (Serie_Nro): {inc['serie_nro_xml_nao_ecf']}")
            print(f"✓ Inconsistências XML vs Rel65 (chaves): {inc['chaves_xml_nao_65']}")
            print(f"✓ Inconsistências XML vs Rel65 (Serie_Nro): {inc['serie_nro_xml_nao_65']}")
        elif resultados.get('erro_analise_cruzada'):
            print(f"⚠ Erro na análise cruzada: {resultados['erro_analise_cruzada']}")
        
        if resultados.get('arquivos_mensais'):
            print(f"✓ Arquivos mensais XML gerados: {len(resultados['arquivos_mensais'])}")
        
        if resultados.get('arquivo_analise_consolidado'):
            print(f"✓ Análise cruzada consolidada: {os.path.basename(resultados['arquivo_analise_consolidado'])}")
        
        if resultados.get('arquivos_analise_mensais'):
            print(f"✓ Análises cruzadas mensais: {len(resultados['arquivos_analise_mensais'])} arquivo(s)")
            for arquivo in resultados['arquivos_analise_mensais']:
                print(f"   - {arquivo['arquivo']} (Mês: {arquivo['mes']})")
        
        print("\nAnálise concluída!")
        return resultados
        
    except Exception as e:
        print(f"Erro durante a análise: {e}")
        import traceback
        traceback.print_exc()
        return None


class ProcessadorXML:
    """
    Classe simplificada para integração com a interface gráfica
    Combina ValidadorXMLNFe e AnaliseCruzada em uma interface única
    """
    def __init__(self, diretorio_xml, diretorio_relatorios, diretorio_analises,
                 data_inicio=None, data_fim=None):
        """
        Inicializa o processador com os diretórios necessários

        Args:
            diretorio_xml: Pasta contendo os XMLs fiscais
            diretorio_relatorios: Pasta contendo os relatórios 65 (OPCIONAL - pode ser None)
            diretorio_analises: Pasta onde serão salvos os resultados
            data_inicio: Data inicial do período (date object)
            data_fim: Data final do período (date object)
        """
        # Atualiza as variáveis globais para os processadores internos
        import config
        import importlib

        # Recarrega o módulo config para pegar as variáveis de ambiente atualizadas
        importlib.reload(config)

        config.PATH_XML = diretorio_xml
        config.PATH_RELATORIOS_65 = diretorio_relatorios if diretorio_relatorios else ''
        config.PATH_ANALISES = diretorio_analises

        self.diretorio_xml = diretorio_xml
        self.diretorio_relatorios = diretorio_relatorios
        self.diretorio_analises = diretorio_analises
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.usar_relatorios = bool(diretorio_relatorios)  # Flag para saber se usa análise cruzada

        # Inicializa o validador
        self.validador = ValidadorXMLNFe(
            diretorio_xml=diretorio_xml,
            data_inicio=data_inicio,
            data_fim=data_fim
        )

    def carregar_xml(self):
        """Carrega e processa os arquivos XML"""
        print("\n📂 Carregando XMLs...")
        # processar_todos_xmls já faz tudo internamente, não precisa passar lista
        notas_faltantes, stats_duplicatas = self.validador.processar_todos_xmls(salvar_automatico=False)
        print(f"✓ {len(self.validador.df_principal)} XMLs processados")

    def carregar_relatorios_65(self):
        """Carrega os relatórios 65 para análise cruzada"""
        if not self.usar_relatorios:
            print("\n⚠️  Pasta de Relatórios 65 não fornecida. Análise cruzada será ignorada.")
            self.analise_cruzada = None
            return
            
        print("\n📊 Carregando Relatórios 65...")
        try:
            analise = AnaliseCruzada(self.validador)
            analise.ler_relatorio_65()
            self.analise_cruzada = analise
        except Exception as e:
            print(f"⚠️  Erro ao carregar relatórios: {e}")
            self.analise_cruzada = None

    def carregar_ecf_log(self):
        """Carrega dados do ECF Log (somente se BD estiver configurado)"""
        if not self.usar_relatorios:
            print("\n⚠️  Análise cruzada não será executada (Relatórios 65 não fornecidos)")
            return
            
        if not config.USE_DB or not config.DB_CONNECTION_STRING:
            print("\n⚠️  Banco de dados não configurado. Análise ECF Log será pulada.")
            return

        print("\n🗄️  Carregando dados do ECF Log...")
        try:
            if hasattr(self, 'analise_cruzada') and self.analise_cruzada:
                self.analise_cruzada.consultar_ecf_log()
            else:
                print("⚠️  Análise cruzada não inicializada")
        except Exception as e:
            print(f"⚠️  Erro ao carregar ECF Log: {e}")

    def gerar_analises(self):
        """Gera todas as análises e salva os resultados"""
        print("\n📋 Gerando análises...")

        try:
            # XMLs já foram processados em carregar_xml(), agora só salvamos os resultados
            # Salva resultados básicos (Analise_NFCe e Notas_Faltantes)
            arquivos_xml = self.validador.salvar_resultados()
            print(f"✓ Análises de XML salvas: {len(arquivos_xml) if arquivos_xml else 0} arquivo(s)")

            # Se há análise cruzada configurada E relatórios foram fornecidos, executa
            if self.usar_relatorios and hasattr(self, 'analise_cruzada') and self.analise_cruzada:
                try:
                    print("\n📊 Executando análise cruzada...")
                    resultados_cruzados = self.analise_cruzada.executar_analise_completa()
                    arquivos_analise = self.analise_cruzada.salvar_analise_cruzada(resultados_cruzados)
                    print(f"✓ Análise cruzada salva")
                except Exception as e:
                    print(f"⚠️  Erro na análise cruzada: {e}")
            elif not self.usar_relatorios:
                print("\n⚠️  Análise cruzada ignorada (pasta de Relatórios 65 não fornecida)")
                print("✓ Arquivos gerados: Analise_NFCe_*.xlsx e Notas_Faltantes_*.xlsx")

            print("\n✅ Processamento concluído!")
            print(f"📁 Resultados salvos em: {self.diretorio_analises}")

        except Exception as e:
            print(f"\n❌ Erro ao gerar análises: {e}")
            import traceback
            traceback.print_exc()
            raise


# Para executar
if __name__ == "__main__":
    data_inicio = '2025-01-01'
    data_fim = '2025-03-31'

    resultados = exemplo_analise_completa(data_inicio, data_fim )
