# E-Mail Analyzer Suite mit LM-Studio Integration

Eine komplette Desktop-Anwendung zur automatischen Analyse von E-Mails mit lokalen LLMs via LM-Studio. Entwickelt für normale Endanwender – keine Programmierkenntnisse nötig.

## 🎯 Was macht das Tool?

1. **E-Mails laden** von beliebigen IMAP/POP3-Konten
2. **KI-gestützte Analyse** jeder E-Mail:
   - Themen-Cluster (z.B. Rechnung, Meeting, Support)
   - Sentiment (positiv/negativ/neutral)
   - Kurze Zusammenfassung
   - Actionable Insights (was muss ich tun?)
   - Wichtigkeit (1-10)
   - Extrahierte Daten (Termine, Beträge, etc.)
3. **Excel-Report** mit Diagrammen und Tabellen
4. **Lernendes Clustering** – die KI erkennt neue Themen und merkt sie sich

## 🚀 Installation

```bash
git clone https://github.com/deinusername/email-analyzer-suite.git
cd email-analyzer-suite
pip install -r requirements.txt
python main.py

⚙️ Voraussetzungen
Python 3.8+

LM-Studio mit geladenem Modell (läuft lokal auf Port 1234)

E-Mail-Konto mit IMAP/POP3-Zugang

📊 Ausgabe
Der Excel-Report enthält:

Übersichtsblatt mit Kennzahlen

Alle E-Mails als Tabelle

Cluster-Verteilung als Balkendiagramm

Sentiment-Analyse als Tortendiagramm

Alle Actionable Insights

Wichtige E-Mails priorisiert

🛡️ Sicherheit
Passwörter werden verschlüsselt gespeichert

Keine externen Cloud-APIs – alles läuft lokal

E-Mails verlassen nie deinen Rechner

📝 Lizenz
MIT License
