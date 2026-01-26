"""
Script para criar o executável Windows do Analisador de XMLs
Execute este script para gerar o arquivo .exe
"""

import PyInstaller.__main__
import os
import sys

# Configurações do build
app_version = "1.2.0"
app_name = f"Analisador_XMLs_Fiscais_v{app_version}"
main_script = "app_gui.py"
icon_file = None  # Você pode adicionar um ícone .ico aqui se desejar
version_file = "version_info.txt"  # Arquivo com informações de versão para o exe

# Argumentos para o PyInstaller
pyinstaller_args = [
    main_script,
    f'--name={app_name}',
    '--onefile',  # Cria um único executável
    '--windowed',  # Não mostra console (importante para GUI)
    '--clean',  # Limpa cache antes de construir

    # Inclui módulos necessários
    '--hidden-import=pandas',
    '--hidden-import=openpyxl',
    '--hidden-import=sqlalchemy',
    '--hidden-import=pyodbc',
    '--hidden-import=xml.etree.ElementTree',

    # Inclui os arquivos Python necessários
    '--add-data=config.py;.',
    '--add-data=processa_xml.py;.',
]

# Adiciona ícone se existir
if icon_file and os.path.exists(icon_file):
    pyinstaller_args.append(f'--icon={icon_file}')

# Adiciona arquivo de versão se existir
if version_file and os.path.exists(version_file):
    pyinstaller_args.append(f'--version-file={version_file}')

def main():
    """Executa o build do executável"""
    print("=" * 70)
    print("CONSTRUINDO EXECUTÁVEL DO ANALISADOR DE XMLs FISCAIS")
    print("=" * 70)
    print()

    # Verifica se o arquivo principal existe
    if not os.path.exists(main_script):
        print(f"[ERRO] Arquivo {main_script} nao encontrado!")
        sys.exit(1)

    print(f"[INFO] Arquivo principal: {main_script}")
    print(f"[INFO] Nome do executavel: {app_name}.exe")
    print(f"[INFO] Versao: {app_version}")
    print()
    print("[BUILD] Iniciando construcao...")
    print()

    try:
        # Executa o PyInstaller
        PyInstaller.__main__.run(pyinstaller_args)

        print()
        print("=" * 70)
        print("[OK] BUILD CONCLUIDO COM SUCESSO!")
        print("=" * 70)
        print()
        print(f"[INFO] O executavel foi criado em: dist/{app_name}.exe")
        print()
        print("INSTRUCOES DE USO:")
        print("1. Copie o arquivo .exe da pasta 'dist' para onde desejar")
        print("2. Execute o arquivo .exe")
        print("3. Configure as pastas e opcoes na interface grafica")
        print("4. Clique em 'Processar XMLs' para iniciar a analise")
        print()
        print("OBSERVACAO: O executavel NAO precisa de Python instalado para funcionar!")
        print()

    except Exception as e:
        print()
        print("=" * 70)
        print("[ERRO] ERRO DURANTE O BUILD")
        print("=" * 70)
        print(f"Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
