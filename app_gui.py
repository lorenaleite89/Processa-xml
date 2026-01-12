"""
Aplicativo Windows para análise de XMLs
Interface gráfica para processamento de XMLs fiscais
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
from pathlib import Path
import sys
import os

# Importar o processador depois de configurar as variáveis
from processa_xml import ProcessadorXML


class XMLAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Analisador de XMLs de NFCe - Versão 1.0")
        self.root.geometry("900x750")
        self.root.resizable(True, True)

        # Variáveis para armazenar configurações
        self.path_xml = tk.StringVar()
        self.path_relatorios = tk.StringVar()
        self.path_analises = tk.StringVar()
        self.data_inicio = tk.StringVar()
        self.data_fim = tk.StringVar()

        # Variáveis do banco de dados
        self.use_db = tk.BooleanVar(value=False)
        self.db_nome = tk.StringVar()
        self.db_user = tk.StringVar()
        self.db_password = tk.StringVar()

        self.create_widgets()

    def create_widgets(self):
        # Frame principal com scrollbar
        main_canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        # ===== SEÇÃO DE CAMINHOS =====
        paths_frame = ttk.LabelFrame(scrollable_frame, text="Configuração de Pastas", padding=10)
        paths_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Path XML
        ttk.Label(paths_frame, text="Pasta dos XMLs:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(paths_frame, textvariable=self.path_xml, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(paths_frame, text="Selecionar", command=lambda: self.select_folder(self.path_xml)).grid(row=0, column=2, pady=5)

        # Path Relatórios (OPCIONAL)
        ttk.Label(paths_frame, text="Pasta dos Relatórios 65 (Opcional):").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(paths_frame, textvariable=self.path_relatorios, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(paths_frame, text="Selecionar", command=lambda: self.select_folder(self.path_relatorios)).grid(row=1, column=2, pady=5)

        # Path Análises
        ttk.Label(paths_frame, text="Pasta para Análises (saída):").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(paths_frame, textvariable=self.path_analises, width=50).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(paths_frame, text="Selecionar", command=lambda: self.select_folder(self.path_analises)).grid(row=2, column=2, pady=5)

        # ===== SEÇÃO DE PERÍODO =====
        period_frame = ttk.LabelFrame(scrollable_frame, text="Período de Análise", padding=10)
        period_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(period_frame, text="Data Início (DD/MM/AAAA):").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(period_frame, textvariable=self.data_inicio, width=20).grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(period_frame, text="Data Fim (DD/MM/AAAA):").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(period_frame, textvariable=self.data_fim, width=20).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # ===== SEÇÃO DE BANCO DE DADOS (OPCIONAL) =====
        db_frame = ttk.LabelFrame(scrollable_frame, text="Configuração de Banco de Dados (Opcional)", padding=10)
        db_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        ttk.Checkbutton(db_frame, text="Usar conexão com banco de dados", variable=self.use_db,
                       command=self.toggle_db_fields).grid(row=0, column=0, columnspan=3, sticky="w", pady=5)

        ttk.Label(db_frame, text="Nome do Banco:").grid(row=1, column=0, sticky="w", pady=5)
        self.db_nome_entry = ttk.Entry(db_frame, textvariable=self.db_nome, width=30)
        self.db_nome_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.db_nome_entry.config(state="disabled")

        ttk.Label(db_frame, text="Usuário:").grid(row=2, column=0, sticky="w", pady=5)
        self.db_user_entry = ttk.Entry(db_frame, textvariable=self.db_user, width=30)
        self.db_user_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.db_user_entry.config(state="disabled")

        ttk.Label(db_frame, text="Senha:").grid(row=3, column=0, sticky="w", pady=5)
        self.db_password_entry = ttk.Entry(db_frame, textvariable=self.db_password, width=30)
        self.db_password_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.db_password_entry.config(state="disabled")

        # ===== BOTÃO DE PROCESSAR =====
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.grid(row=3, column=0, padx=10, pady=20)

        self.process_button = ttk.Button(button_frame, text="Processar XMLs", command=self.process_xmls, style="Accent.TButton")
        self.process_button.pack(pady=10)

        # ===== LOG DE SAÍDA =====
        log_frame = ttk.LabelFrame(scrollable_frame, text="Log de Processamento", padding=10)
        log_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=100, state="disabled")
        self.log_text.pack(fill="both", expand=True)

        # Configurar grid weights
        scrollable_frame.columnconfigure(0, weight=1)
        scrollable_frame.rowconfigure(4, weight=1)

        # Empacotar canvas e scrollbar
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def select_folder(self, var):
        """Abre diálogo para seleção de pasta"""
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)

    def toggle_db_fields(self):
        """Habilita/desabilita campos de banco de dados"""
        state = "normal" if self.use_db.get() else "disabled"
        self.db_nome_entry.config(state=state)
        self.db_user_entry.config(state=state)
        self.db_password_entry.config(state=state)

    def log(self, message):
        """Adiciona mensagem ao log"""
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.root.update()

    def validate_inputs(self):
        """Valida os inputs do usuário"""
        # Validar pastas
        if not self.path_xml.get():
            messagebox.showerror("Erro", "Selecione a pasta dos XMLs")
            return False

        # PATH_RELATORIOS agora é OPCIONAL
        # if not self.path_relatorios.get():
        #     messagebox.showerror("Erro", "Selecione a pasta dos Relatórios 65")
        #     return False

        if not self.path_analises.get():
            messagebox.showerror("Erro", "Selecione a pasta para salvar as Análises")
            return False

        # Validar que PATH_ANALISES é diferente de PATH_RELATORIOS_65 (somente se relatórios foi fornecido)
        if self.path_relatorios.get() and Path(self.path_analises.get()).resolve() == Path(self.path_relatorios.get()).resolve():
            messagebox.showerror("Erro", "A pasta de análises deve ser diferente da pasta de relatórios")
            return False

        # Validar datas
        if self.data_inicio.get():
            try:
                datetime.strptime(self.data_inicio.get(), "%d/%m/%Y")
            except ValueError:
                messagebox.showerror("Erro", "Data de início inválida. Use o formato DD/MM/AAAA")
                return False

        if self.data_fim.get():
            try:
                datetime.strptime(self.data_fim.get(), "%d/%m/%Y")
            except ValueError:
                messagebox.showerror("Erro", "Data de fim inválida. Use o formato DD/MM/AAAA")
                return False

        # Validar campos de banco se habilitado
        if self.use_db.get():
            if not self.db_nome.get() or not self.db_user.get() or not self.db_password.get():
                messagebox.showerror("Erro", "Preencha todos os campos do banco de dados ou desabilite a opção")
                return False

        return True

    def process_xmls(self):
        """Processa os XMLs com as configurações fornecidas"""
        if not self.validate_inputs():
            return

        # Desabilitar botão durante processamento
        self.process_button.config(state="disabled")
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")

        try:
            self.log("=" * 80)
            self.log("INICIANDO PROCESSAMENTO DE XMLs")
            self.log("=" * 80)

            # Configurar variáveis de ambiente para o processador
            os.environ['PATH_XML'] = self.path_xml.get()
            os.environ['PATH_RELATORIOS_65'] = self.path_relatorios.get() if self.path_relatorios.get() else ''
            os.environ['PATH_ANALISES'] = self.path_analises.get()

            # Configurar banco de dados se necessário
            if self.use_db.get():
                os.environ['USE_DB'] = 'True'
                os.environ['NOME_DB'] = self.db_nome.get()
                os.environ['USER_DB'] = self.db_user.get()
                os.environ['PASSWORD_DB'] = self.db_password.get()
            else:
                os.environ['USE_DB'] = 'False'

            # Converter datas
            data_inicio = None
            data_fim = None

            if self.data_inicio.get():
                data_inicio = datetime.strptime(self.data_inicio.get(), "%d/%m/%Y").date()
                self.log(f"📅 Data início: {data_inicio.strftime('%d/%m/%Y')}")

            if self.data_fim.get():
                data_fim = datetime.strptime(self.data_fim.get(), "%d/%m/%Y").date()
                self.log(f"📅 Data fim: {data_fim.strftime('%d/%m/%Y')}")

            self.log(f"\n📁 Pasta XMLs: {self.path_xml.get()}")
            if self.path_relatorios.get():
                self.log(f"📁 Pasta Relatórios: {self.path_relatorios.get()}")
            else:
                self.log(f"⚠️  Pasta Relatórios: NÃO FORNECIDA (análise cruzada será ignorada)")
            self.log(f"📁 Pasta Análises: {self.path_analises.get()}")

            if self.use_db.get():
                self.log(f"\n🗄️  Banco de dados: {self.db_nome.get()}")
            else:
                self.log("\n⚠️  Processamento sem banco de dados")

            self.log("\n" + "=" * 80)
            self.log("PROCESSANDO...")
            self.log("=" * 80 + "\n")

            # Criar processador e executar
            processador = ProcessadorXML(
                diretorio_xml=self.path_xml.get(),
                diretorio_relatorios=self.path_relatorios.get() if self.path_relatorios.get() else None,
                diretorio_analises=self.path_analises.get(),
                data_inicio=data_inicio,
                data_fim=data_fim
            )

            # Redirecionar print para o log
            original_stdout = sys.stdout

            class LogRedirector:
                def __init__(self, log_func):
                    self.log_func = log_func

                def write(self, message):
                    if message.strip():
                        self.log_func(message.rstrip())

                def flush(self):
                    pass

            sys.stdout = LogRedirector(self.log)

            try:
                # Carregar dados
                processador.carregar_xml()
                
                # Carregar relatórios somente se fornecido
                if self.path_relatorios.get():
                    processador.carregar_relatorios_65()

                    if self.use_db.get():
                        processador.carregar_ecf_log()

                # Gerar análises
                processador.gerar_analises()

                self.log("\n" + "=" * 80)
                self.log("✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
                self.log("=" * 80)

                messagebox.showinfo("Sucesso", "Processamento concluído com sucesso!\nVerifique os arquivos na pasta de análises.")

            finally:
                sys.stdout = original_stdout

        except Exception as e:
            self.log(f"\n❌ ERRO: {str(e)}")
            messagebox.showerror("Erro", f"Erro durante o processamento:\n{str(e)}")

        finally:
            # Reabilitar botão
            self.process_button.config(state="normal")


def main():
    root = tk.Tk()

    # Configurar estilo
    style = ttk.Style()
    style.theme_use('clam')

    app = XMLAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
