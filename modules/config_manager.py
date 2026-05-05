import json
from pathlib import Path

class ConfigManager:
    """Einfache Konfigurationsverwaltung (Passwort im Klartext)"""
    
    def __init__(self):
        self.config_file = Path("config.json")
        
    def save_config(self, config):
        """Konfiguration speichern"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def load_config(self):
        """Konfiguration laden"""
        if not self.config_file.exists():
            return self._default_config()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return self._default_config()
    
    def _default_config(self):
        """Standard-Konfiguration"""
        return {
            'server': 'imap.gmail.com',
            'port': 993,
            'username': '',
            'password': '',
            'use_imap': True,
            'max_emails': 200,
            'system_prompt': '''Du bist ein professioneller E-Mail-Analyst. Analysiere jede E-Mail und gib NUR EIN JSON-Objekt zurück, ohne zusätzlichen Text.

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
Erkläre nichts, gib NUR das JSON zurück.''',
            'clusters': ['Rechnung', 'Meeting', 'Newsletter', 'Support', 'Angebot', 'Privat'],
            'allow_new_clusters': True,
            'batch_size': 1
        }