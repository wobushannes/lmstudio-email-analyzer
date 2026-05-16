import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from pathlib import Path
import webbrowser
from modules.utils import setup_logging, ensure_directories
from modules.config_manager import ConfigManager
from modules.email_fetcher import EmailFetcher
from modules.lmstudio_client import LMStudioClient
from modules.email_analyzer import EmailAnalyzer
from modules.excel_reporter import ExcelReporter

logger = setup_logging()
ensure_directories()

class EmailAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📧 E-Mail Analyzer Pro")
        self.root.geometry("850x1000")
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=6, font=('Segoe UI', 10))
        style.configure('TLabel', font=('Segoe UI', 10))
        style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
        
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        
        self.lm_client = None
        self.analyzer = None
        self.last_excel = None
        self.last_json = None
        
        self._build_gui()
        self._load_config_to_gui()
        
    def _build_gui(self):
        # Hauptframe mit Scrollbar
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # ========== 1. E-Mail-Zugang ==========
        email_frame = ttk.LabelFrame(scrollable_frame, text="📨 E-Mail Zugang", padding=10)
        email_frame.pack(fill="x", padx=10, pady=5)
        
        self.use_imap = tk.BooleanVar(value=self.config.get('use_imap', True))
        ttk.Radiobutton(email_frame, text="IMAP", variable=self.use_imap, value=True).grid(row=0, column=0, padx=5)
        ttk.Radiobutton(email_frame, text="POP3", variable=self.use_imap, value=False).grid(row=0, column=1, padx=5)
        
        ttk.Label(email_frame, text="Server:").grid(row=1, column=0, sticky="w", pady=5)
        self.server_entry = ttk.Entry(email_frame, width=50)
        self.server_entry.grid(row=1, column=1, columnspan=2, pady=5)
        
        ttk.Label(email_frame, text="Port:").grid(row=2, column=0, sticky="w", pady=5)
        self.port_entry = ttk.Entry(email_frame, width=10)
        self.port_entry.grid(row=2, column=1, sticky="w", pady=5)
        
        ttk.Label(email_frame, text="Benutzername:").grid(row=3, column=0, sticky="w", pady=5)
        self.username_entry = ttk.Entry(email_frame, width=50)
        self.username_entry.grid(row=3, column=1, columnspan=2, pady=5)
        
        ttk.Label(email_frame, text="Passwort:").grid(row=4, column=0, sticky="w", pady=5)
        self.password_entry = ttk.Entry(email_frame, width=50, show="*")
        self.password_entry.grid(row=4, column=1, pady=5)
        
        self.show_password = tk.BooleanVar(value=False)
        ttk.Checkbutton(email_frame, text="👁 Zeigen", variable=self.show_password, 
                       command=self._toggle_password).grid(row=4, column=2, padx=5)
        
        # ========== 2. LM-Studio Einstellungen ==========
        lm_frame = ttk.LabelFrame(scrollable_frame, text="🧠 LM-Studio Verbindung", padding=10)
        lm_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(lm_frame, text="API URL:").grid(row=0, column=0, sticky="w", pady=5)
        self.lm_url_entry = ttk.Entry(lm_frame, width=50)
        self.lm_url_entry.grid(row=0, column=1, sticky="w", pady=5)
        ttk.Label(lm_frame, text="(z.B. http://localhost:1234/v1/chat/completions)").grid(row=0, column=2, padx=5)
        
        ttk.Label(lm_frame, text="Timeout (Sekunden):").grid(row=1, column=0, sticky="w", pady=5)
        self.lm_timeout_entry = ttk.Entry(lm_frame, width=10)
        self.lm_timeout_entry.grid(row=1, column=1, sticky="w", pady=5)
        
        ttk.Label(lm_frame, text="Max. Token pro Request:").grid(row=2, column=0, sticky="w", pady=5)
        self.lm_max_tokens_entry = ttk.Entry(lm_frame, width=10)
        self.lm_max_tokens_entry.grid(row=2, column=1, sticky="w", pady=5)
        
        ttk.Label(lm_frame, text="Temperatur (0-1):").grid(row=3, column=0, sticky="w", pady=5)
        self.lm_temperature_entry = ttk.Entry(lm_frame, width=10)
        self.lm_temperature_entry.grid(row=3, column=1, sticky="w", pady=5)
        
        # LM-Studio Status prüfen Button
        self.check_lm_btn = ttk.Button(lm_frame, text="🔌 LM-Studio Status prüfen", command=self._check_lm_status)
        self.check_lm_btn.grid(row=4, column=0, columnspan=2, pady=5)
        
        self.lm_status_label = ttk.Label(lm_frame, text="⚪ Nicht geprüft", foreground="gray")
        self.lm_status_label.grid(row=4, column=2, padx=5)
        
        # ========== 3. LM-Studio System-Prompt ==========
        prompt_frame = ttk.LabelFrame(scrollable_frame, text="📝 LM-Studio System-Prompt (für die KI)", padding=10)
        prompt_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, height=10, width=80, font=('Consolas', 9))
        self.prompt_text.pack(fill="both", expand=True)
        
        # ========== 4. Analyse-Einstellungen ==========
        settings_frame = ttk.LabelFrame(scrollable_frame, text="⚙️ Analyse-Einstellungen", padding=10)
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(settings_frame, text="Maximale E-Mails:").grid(row=0, column=0, sticky="w", pady=5)
        self.max_emails_entry = ttk.Entry(settings_frame, width=10)
        self.max_emails_entry.grid(row=0, column=1, sticky="w", pady=5)
        ttk.Label(settings_frame, text="(letzte X E-Mails)").grid(row=0, column=2, sticky="w", padx=5)
        
        ttk.Label(settings_frame, text="Themen-Cluster (kommagetrennt):").grid(row=1, column=0, sticky="w", pady=5)
        self.clusters_entry = ttk.Entry(settings_frame, width=60)
        self.clusters_entry.grid(row=1, column=1, columnspan=2, pady=5)
        
        self.allow_new_clusters = tk.BooleanVar(value=self.config.get('allow_new_clusters', True))
        ttk.Checkbutton(settings_frame, text="✅ LLM darf neue Cluster vorschlagen (lernt dazu)", 
                       variable=self.allow_new_clusters).grid(row=2, column=0, columnspan=3, sticky="w", pady=5)
        
        # ========== 5. Status und Buttons ==========
        status_frame = ttk.Frame(scrollable_frame)
        status_frame.pack(fill="x", padx=10, pady=10)
        
        self.analyze_btn = ttk.Button(status_frame, text="🔍 E-Mails laden & analysieren", 
                                     command=self.start_analysis, width=30)
        self.analyze_btn.pack(pady=5)
        
        self.progress = ttk.Progressbar(status_frame, mode='determinate')
        self.progress.pack(fill="x", pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Bereit", font=('Segoe UI', 9))
        self.status_label.pack(pady=5)
        
        # Ergebnis-Buttons
        result_frame = ttk.Frame(scrollable_frame)
        result_frame.pack(fill="x", padx=10, pady=5)
        
        self.open_excel_btn = ttk.Button(result_frame, text="📁 Excel öffnen", 
                                        command=self.open_excel, state='disabled')
        self.open_excel_btn.pack(side="left", padx=5)
        
        self.export_json_btn = ttk.Button(result_frame, text="💾 JSON export", 
                                         command=self.export_json, state='disabled')
        self.export_json_btn.pack(side="left", padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _toggle_password(self):
        if self.show_password.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")
    
    def _check_lm_status(self):
        """LM-Studio Verbindung testen"""
        url = self.lm_url_entry.get().strip()
        if not url:
            url = "http://localhost:1234/v1/chat/completions"
        
        base_url = url.replace("/v1/chat/completions", "/v1/models")
        
        try:
            import requests
            response = requests.get(base_url, timeout=5)
            if response.status_code == 200:
                self.lm_status_label.config(text="✅ Verbunden", foreground="green")
                messagebox.showinfo("LM-Studio", "LM-Studio ist erreichbar und läuft!")
            else:
                self.lm_status_label.config(text="⚠️ Nicht erreichbar", foreground="orange")
                messagebox.showwarning("LM-Studio", f"LM-Studio antwortet nicht richtig (HTTP {response.status_code})")
        except Exception as e:
            self.lm_status_label.config(text="❌ Keine Verbindung", foreground="red")
            messagebox.showerror("LM-Studio", 
                               f"LM-Studio ist nicht erreichbar!\n\n"
                               f"Fehler: {str(e)}\n\n"
                               f"Tipps:\n"
                               f"1. Ist LM-Studio gestartet?\n"
                               f"2. Ist ein Modell geladen?\n"
                               f"3. Läuft der Server auf {base_url}?")
    
    def _load_config_to_gui(self):
        """Alle gespeicherten Einstellungen laden"""
        # E-Mail
        self.server_entry.insert(0, self.config.get('server', 'imap.gmail.com'))
        self.port_entry.insert(0, str(self.config.get('port', 993)))
        self.username_entry.insert(0, self.config.get('username', ''))
        self.password_entry.insert(0, self.config.get('password', ''))
        
        # LM-Studio
        self.lm_url_entry.insert(0, self.config.get('lm_url', 'http://localhost:1234/v1/chat/completions'))
        self.lm_timeout_entry.insert(0, str(self.config.get('lm_timeout', 60)))
        self.lm_max_tokens_entry.insert(0, str(self.config.get('lm_max_tokens', 4096)))
        self.lm_temperature_entry.insert(0, str(self.config.get('lm_temperature', 0.3)))
        
        # Analyse
        self.max_emails_entry.insert(0, str(self.config.get('max_emails', 200)))
        self.clusters_entry.insert(0, ', '.join(self.config.get('clusters', ['Rechnung', 'Meeting', 'Newsletter', 'Support', 'Angebot', 'Privat'])))
        self.prompt_text.insert('1.0', self.config.get('system_prompt', self._default_prompt()))
    
    def _default_prompt(self):
        return """Du bist ein professioneller E-Mail-Analyst. Analysiere jede E-Mail und gib NUR EIN JSON-Objekt zurück, ohne zusätzlichen Text.

Das JSON MUSS diese Struktur haben:
{
    "cluster": "Hauptcluster aus der Liste oder NEU:NeuerClusterName",
    "clusters": ["Cluster1", "Cluster2", "bis zu 3 Cluster"],
    "summary": "Ein Satz Zusammenfassung auf Deutsch",
    "sentiment": "positiv|negativ|neutral",
    "actionable": ["Aktionspunkt 1", "Aktionspunkt 2"],
    "extracted_data": {"key": "value"},
    "importance": 1-10
}

Mögliche Cluster: {clusters}
Erkläre nichts, gib NUR das JSON zurück."""
    
    def _save_config(self):
        """Alle GUI-Einstellungen speichern"""
        clusters = [c.strip() for c in self.clusters_entry.get().split(',') if c.strip()]
        
        self.config = {
            # E-Mail
            'server': self.server_entry.get(),
            'port': int(self.port_entry.get() or 993),
            'username': self.username_entry.get(),
            'password': self.password_entry.get(),
            'use_imap': self.use_imap.get(),
            
            # LM-Studio
            'lm_url': self.lm_url_entry.get(),
            'lm_timeout': int(self.lm_timeout_entry.get() or 60),
            'lm_max_tokens': int(self.lm_max_tokens_entry.get() or 4096),
            'lm_temperature': float(self.lm_temperature_entry.get() or 0.3),
            
            # Analyse
            'max_emails': int(self.max_emails_entry.get() or 200),
            'clusters': clusters,
            'allow_new_clusters': self.allow_new_clusters.get(),
            'system_prompt': self.prompt_text.get('1.0', tk.END).strip()
        }
        self.config_manager.save_config(self.config)
    
    def start_analysis(self):
        self._save_config()
        
        # LM-Studio Client initialisieren
        self.lm_client = LMStudioClient(
            api_url=self.config['lm_url'],
            timeout=self.config['lm_timeout']
        )
        
        # Prüfe LM-Studio
        if not self.lm_client.check_connection():
            messagebox.showerror("Fehler", 
                               f"LM-Studio ist nicht erreichbar!\n\n"
                               f"URL: {self.config['lm_url']}\n\n"
                               f"Bitte starte LM-Studio, lade ein Modell und prüfe die URL.\n"
                               f"Klicke auf 'LM-Studio Status prüfen' für Details.")
            return
        
        # Deaktiviere Button während der Analyse
        self.analyze_btn.config(state='disabled', text='⏳ Analysiere...')
        self.progress['value'] = 0
        self.status_label.config(text="Verbinde mit E-Mail-Server...")
        
        # Starte in eigenem Thread
        thread = threading.Thread(target=self._run_analysis, daemon=True)
        thread.start()
    
    def _run_analysis(self):
        try:
            # 1. E-Mails laden
            fetcher = EmailFetcher(
                self.config['server'],
                self.config['port'],
                self.config['username'],
                self.config['password'],
                self.config['use_imap']
            )
            
            def update_progress(current, total):
                self.root.after(0, lambda: self._update_progress(current, total, "Lade E-Mails..."))
            
            connected, msg = fetcher.connect()
            if not connected:
                self.root.after(0, lambda: self._show_error(f"Verbindungsfehler: {msg}"))
                return
            
            self.root.after(0, lambda: self.status_label.config(text="Lade E-Mails..."))
            emails, error = fetcher.fetch_emails(self.config['max_emails'], update_progress)
            fetcher.disconnect()
            
            if error:
                self.root.after(0, lambda: self._show_error(f"Fehler beim Laden: {error}"))
                return
            
            if not emails:
                self.root.after(0, lambda: self._show_error("Keine E-Mails gefunden!"))
                return
            
            # 2. Analyse
            self.root.after(0, lambda: self.status_label.config(text=f"Analysiere {len(emails)} E-Mails mit LM-Studio..."))
            
            analyzer = EmailAnalyzer(
                self.lm_client,
                self.config['clusters'],
                self.config['allow_new_clusters']
            )
            
            def update_analysis_progress(current, total):
                self.root.after(0, lambda: self._update_progress(current, total, f"Analysiere {current}/{total}"))
            
            results, stats = analyzer.analyze_emails(
                emails,
                self.config['system_prompt'],
                self.config['lm_max_tokens'],
                update_analysis_progress
            )
            
            # 3. Excel erstellen
            self.root.after(0, lambda: self.status_label.config(text="Erstelle Excel-Report..."))
            reporter = ExcelReporter(results, stats)
            excel_file = reporter.create_report()
            
            # 4. Speichere JSON
            import json
            from datetime import datetime
            json_file = Path("exports") / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'results': results,
                    'stats': stats,
                    'config': self.config
                }, f, indent=2, default=str)
            
            self.last_excel = excel_file
            self.last_json = json_file
            
            self.root.after(0, lambda: self._analysis_finished(stats, excel_file))
            
        except Exception as e:
            logger.error(f"Fehler in Analyse: {str(e)}", exc_info=True)
            self.root.after(0, lambda: self._show_error(f"Unerwarteter Fehler: {str(e)}"))
    
    def _update_progress(self, current, total, status_text):
        self.progress['maximum'] = total
        self.progress['value'] = current
        self.status_label.config(text=f"{status_text} ({current}/{total})")
    
    def _analysis_finished(self, stats, excel_file):
        self.analyze_btn.config(state='normal', text="🔍 E-Mails laden & analysieren")
        self.open_excel_btn.config(state='normal')
        self.export_json_btn.config(state='normal')
        self.progress['value'] = self.progress['maximum']
        
        messagebox.showinfo("Fertig!", 
                           f"Analyse abgeschlossen!\n\n"
                           f"📊 {stats['total_emails']} E-Mails analysiert\n"
                           f"✅ Erfolgreich: {stats['successful_analyses']}\n"
                           f"❌ Fehler: {stats['failed_analyses']}\n"
                           f"📎 Mit Anhängen: {stats['emails_with_attachments']}\n\n"
                           f"📁 Excel wurde erstellt.")
        
        self.status_label.config(text=f"Fertig! {stats['total_emails']} E-Mails analysiert")
        
        # Excel automatisch öffnen?
        if messagebox.askyesno("Excel öffnen", "Möchten Sie den Excel-Report jetzt öffnen?"):
            webbrowser.open(str(excel_file))
    
    def open_excel(self):
        if hasattr(self, 'last_excel') and self.last_excel and self.last_excel.exists():
            webbrowser.open(str(self.last_excel))
        else:
            messagebox.showerror("Fehler", "Kein Excel-Report gefunden!")
    
    def export_json(self):
        if hasattr(self, 'last_json') and self.last_json and self.last_json.exists():
            webbrowser.open(str(self.last_json.parent))
            messagebox.showinfo("Info", f"JSON gespeichert unter:\n{self.last_json}")
        else:
            messagebox.showerror("Fehler", "Kein JSON gefunden!")
    
    def _show_error(self, error_msg):
        self.analyze_btn.config(state='normal', text="🔍 E-Mails laden & analysieren")
        messagebox.showerror("Fehler", error_msg)
        self.status_label.config(text="Fehler aufgetreten")

if __name__ == "__main__":
    root = tk.Tk()
    app = EmailAnalyzerGUI(root)
    root.mainloop()