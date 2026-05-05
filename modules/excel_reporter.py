import xlsxwriter
from datetime import datetime
from pathlib import Path

class ExcelReporter:
    """Excel-Report mit Diagrammen erstellen"""
    
    def __init__(self, results, stats):
        self.results = results
        self.stats = stats
        self.output_file = Path("exports") / f"email_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
    def create_report(self):
        """Kompletten Excel-Report erstellen"""
        workbook = xlsxwriter.Workbook(self.output_file)
        
        # Formate definieren
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'border': 1
        })
        
        cell_format = workbook.add_format({'border': 1})
        center_format = workbook.add_format({'border': 1, 'align': 'center'})
        
        # 1. Übersichtsblatt
        self._create_overview_sheet(workbook, header_format, cell_format)
        
        # 2. Alle E-Mails
        self._create_emails_sheet(workbook, header_format, cell_format)
        
        # 3. Cluster-Analyse mit Diagramm
        self._create_cluster_sheet(workbook)
        
        # 4. Sentiment-Analyse mit Diagramm
        self._create_sentiment_sheet(workbook)
        
        # 5. Actionable Insights
        self._create_actions_sheet(workbook, header_format, cell_format)
        
        # 6. Wichtige E-Mails
        self._create_important_sheet(workbook, header_format, center_format)
        
        workbook.close()
        return self.output_file
    
    def _create_overview_sheet(self, workbook, header_format, cell_format):
        """Übersichtsblatt mit Key Figures"""
        sheet = workbook.add_worksheet("📊 Übersicht")
        
        # Titel
        sheet.merge_range('A1:E1', 'E-Mail-Analyse Report', 
                         workbook.add_format({'bold': True, 'size': 16, 'align': 'center'}))
        sheet.merge_range('A2:E2', f"Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
                         workbook.add_format({'align': 'center'}))
        
        # Key Figures
        row = 4
        sheet.write(row, 0, "Kennzahl", header_format)
        sheet.write(row, 1, "Wert", header_format)
        
        row += 1
        sheet.write(row, 0, "E-Mails gesamt", cell_format)
        sheet.write(row, 1, self.stats['total_emails'], cell_format)
        
        row += 1
        sheet.write(row, 0, "Erfolgreich analysiert", cell_format)
        sheet.write(row, 1, self.stats['successful_analyses'], cell_format)
        
        row += 1
        sheet.write(row, 0, "Fehlgeschlagen", cell_format)
        sheet.write(row, 1, self.stats['failed_analyses'], cell_format)
        
        row += 1
        sheet.write(row, 0, "Mit Anhängen", cell_format)
        sheet.write(row, 1, self.stats['emails_with_attachments'], cell_format)
        
        row += 2
        sheet.write(row, 0, "Top 5 Absender", header_format)
        sheet.write(row, 1, "Anzahl", header_format)
        
        for i, (sender, count) in enumerate(self.stats['top_senders'][:5]):
            row += 1
            sheet.write(row, 0, sender[:50], cell_format)
            sheet.write(row, 1, count, cell_format)
        
        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 15)
    
    def _create_emails_sheet(self, workbook, header_format, cell_format):
        """Alle E-Mails als Tabelle"""
        sheet = workbook.add_worksheet("📧 Alle E-Mails")
        
        # Header
        headers = ['Datum', 'Absender', 'Betreff', 'Cluster', 'Sentiment', 'Zusammenfassung']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        
        # Daten
        for row, email in enumerate(self.results, start=1):
            sheet.write(row, 0, email['date'].strftime('%d.%m.%Y %H:%M') if isinstance(email['date'], datetime) else str(email['date']), cell_format)
            sheet.write(row, 1, email['from'][:50], cell_format)
            sheet.write(row, 2, email['subject'][:80], cell_format)
            sheet.write(row, 3, ', '.join(email['clusters']), cell_format)
            sheet.write(row, 4, email['sentiment'], cell_format)
            sheet.write(row, 5, email['summary'][:200], cell_format)
        
        sheet.set_column('A:A', 18)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 40)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 12)
        sheet.set_column('F:F', 50)
    
    def _create_cluster_sheet(self, workbook):
        """Cluster-Analyse mit Balkendiagramm"""
        sheet = workbook.add_worksheet("🏷️ Cluster-Verteilung")
        
        # Daten vorbereiten
        clusters = list(self.stats['cluster_distribution'].keys())
        counts = list(self.stats['cluster_distribution'].values())
        
        # Tabelle
        sheet.write(0, 0, "Cluster", workbook.add_format({'bold': True}))
        sheet.write(0, 1, "Anzahl", workbook.add_format({'bold': True}))
        
        for i, (cluster, count) in enumerate(self.stats['cluster_distribution'].items(), start=1):
            sheet.write(i, 0, cluster)
            sheet.write(i, 1, count)
        
        # Diagramm
        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'Anzahl E-Mails',
            'categories': ['🏷️ Cluster-Verteilung', 1, 0, len(clusters), 0],
            'values': ['🏷️ Cluster-Verteilung', 1, 1, len(clusters), 1],
            'fill': {'color': '#4CAF50'},
            'data_labels': {'value': True}
        })
        chart.set_title({'name': 'E-Mails pro Cluster'})
        chart.set_x_axis({'name': 'Cluster'})
        chart.set_y_axis({'name': 'Anzahl'})
        
        sheet.insert_chart('E2', chart, {'x_offset': 25, 'y_offset': 10})
        
        sheet.set_column('A:A', 20)
    
    def _create_sentiment_sheet(self, workbook):
        """Sentiment-Analyse mit Tortendiagramm"""
        sheet = workbook.add_worksheet("😊 Sentiment-Analyse")
        
        # Daten
        sentiments = list(self.stats['sentiment_distribution'].keys())
        counts = list(self.stats['sentiment_distribution'].values())
        
        # Tabelle
        sheet.write(0, 0, "Sentiment", workbook.add_format({'bold': True}))
        sheet.write(0, 1, "Anzahl", workbook.add_format({'bold': True}))
        
        colors = {'positiv': '#4CAF50', 'negativ': '#F44336', 'neutral': '#FFC107'}
        
        for i, (sentiment, count) in enumerate(self.stats['sentiment_distribution'].items(), start=1):
            sheet.write(i, 0, sentiment)
            sheet.write(i, 1, count)
        
        # Tortendiagramm
        chart = workbook.add_chart({'type': 'pie'})
        chart.add_series({
            'name': 'Sentiment',
            'categories': ['😊 Sentiment-Analyse', 1, 0, len(sentiments), 0],
            'values': ['😊 Sentiment-Analyse', 1, 1, len(sentiments), 1],
            'data_labels': {'percentage': True, 'category': True}
        })
        chart.set_title({'name': 'Sentiment-Verteilung'})
        
        sheet.insert_chart('E2', chart, {'x_offset': 25, 'y_offset': 10})
        
        sheet.set_column('A:A', 15)
    
    def _create_actions_sheet(self, workbook, header_format, cell_format):
        """Actionable Insights"""
        sheet = workbook.add_worksheet("✅ Actionable Insights")
        
        sheet.write(0, 0, "Aktion", header_format)
        sheet.write(0, 1, "Aus E-Mail", header_format)
        
        actions = self.stats['all_actions']
        
        for i, action in enumerate(actions[:50], start=1):
            sheet.write(i, 0, action, cell_format)
            # Hier könnte man die zugehörige Mail verlinken
            sheet.write(i, 1, "-", cell_format)
        
        sheet.set_column('A:A', 60)
        sheet.set_column('B:B', 40)
    
    def _create_important_sheet(self, workbook, header_format, center_format):
        """Wichtige E-Mails"""
        sheet = workbook.add_worksheet("⭐ Wichtige E-Mails")
        
        headers = ['Wichtigkeit', 'Datum', 'Absender', 'Betreff', 'Cluster']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        
        for row, email in enumerate(self.stats['important_emails'], start=1):
            sheet.write(row, 0, f"{email['importance']}/10", center_format)
            sheet.write(row, 1, email['date'].strftime('%d.%m.%Y') if isinstance(email['date'], datetime) else str(email['date']), center_format)
            sheet.write(row, 2, email['from'][:40])
            sheet.write(row, 3, email['subject'][:60])
            sheet.write(row, 4, ', '.join(email['clusters']))
        
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 40)
        sheet.set_column('E:E', 20)