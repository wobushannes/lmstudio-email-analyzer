import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

class EmailAnalyzer:
    """E-Mail-Analyse mit Clustering und allen Auswertungen"""
    
    def __init__(self, lm_client, base_clusters, temperature=0.3, allow_new_clusters=True):
        self.lm_client = lm_client
        self.base_clusters = base_clusters
        self.temperature = temperature
        self.allow_new_clusters = allow_new_clusters
        self.known_clusters = set(base_clusters)
        self.new_clusters_file = Path("custom_clusters.json")
        self._load_new_clusters()
    
    def _load_new_clusters(self):
        """Gelernte Cluster laden"""
        if self.new_clusters_file.exists():
            try:
                with open(self.new_clusters_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.known_clusters.update(data.get('clusters', []))
            except:
                pass
    
    def _save_new_clusters(self):
        """Neue Cluster speichern"""
        custom_clusters = list(self.known_clusters - set(self.base_clusters))
        if custom_clusters:
            with open(self.new_clusters_file, 'w', encoding='utf-8') as f:
                json.dump({'clusters': custom_clusters}, f, indent=2, ensure_ascii=False)
    
    def analyze_emails(self, emails, system_prompt, max_tokens=4096, progress_callback=None):
        """Alle E-Mails analysieren"""
        results = []
        new_clusters_found = Counter()
        
        for i, email in enumerate(emails):
            if progress_callback:
                progress_callback(i + 1, len(emails))
            
            # Analyse durch LM-Studio mit Temperatur
            analysis_result = self.lm_client.analyze_email(
                email_data=email,
                system_prompt=system_prompt,
                clusters=list(self.known_clusters),
                max_tokens=max_tokens,
                temperature=self.temperature
            )
            
            if analysis_result['success']:
                analysis = analysis_result['analysis']
                
                # Cluster-Handling
                clusters_assigned = []
                if 'clusters' in analysis and isinstance(analysis['clusters'], list):
                    clusters_assigned = analysis['clusters']
                elif 'cluster' in analysis:
                    clusters_assigned = [analysis['cluster']]
                else:
                    clusters_assigned = ['Sonstiges']
                
                # Neue Cluster erkennen und zählen
                for cluster in clusters_assigned[:]:  # Kopie für Iteration
                    if cluster.startswith('NEU:'):
                        new_cluster = cluster[4:]
                        if self.allow_new_clusters:
                            new_clusters_found[new_cluster] += 1
                            idx = clusters_assigned.index(cluster)
                            clusters_assigned[idx] = new_cluster
                            if new_cluster not in self.known_clusters:
                                self.known_clusters.add(new_cluster)
                    elif cluster not in self.known_clusters and self.allow_new_clusters:
                        new_clusters_found[cluster] += 1
                        self.known_clusters.add(cluster)
                
                # Ergebnis speichern
                result = {
                    'email_id': email['id'],
                    'subject': email['subject'],
                    'from': email['from'],
                    'date': email['date'],
                    'clusters': clusters_assigned,
                    'summary': analysis.get('summary', 'Keine Zusammenfassung'),
                    'sentiment': analysis.get('sentiment', 'neutral'),
                    'actionable': analysis.get('actionable', []),
                    'extracted_data': analysis.get('extracted_data', {}),
                    'importance': analysis.get('importance', 5),
                    'has_attachments': email['has_attachments'],
                    'analysis_success': True
                }
            else:
                # Fehlerfall
                result = {
                    'email_id': email['id'],
                    'subject': email['subject'],
                    'from': email['from'],
                    'date': email['date'],
                    'clusters': ['Fehler'],
                    'summary': f"Analyse fehlgeschlagen: {analysis_result.get('error', 'Unbekannter Fehler')}",
                    'sentiment': 'neutral',
                    'actionable': [],
                    'extracted_data': {},
                    'importance': 1,
                    'has_attachments': email['has_attachments'],
                    'analysis_success': False,
                    'error': analysis_result.get('error')
                }
            
            results.append(result)
        
        # Neue Cluster speichern (nur wenn sie mindestens 3x vorkamen)
        if self.allow_new_clusters:
            for cluster, count in new_clusters_found.items():
                if count >= 3:
                    self._save_new_clusters()
        
        # Zusätzliche Auswertungen
        stats = self._generate_statistics(results)
        
        return results, stats
    
    def _generate_statistics(self, results):
        """Statistiken aus den Analyseergebnissen generieren"""
        
        # Cluster-Statistik
        cluster_counts = Counter()
        for r in results:
            for cluster in r['clusters']:
                cluster_counts[cluster] += 1
        
        # Sentiment-Statistik
        sentiment_counts = Counter([r['sentiment'] for r in results])
        
        # Absender-Statistik
        sender_counts = Counter([r['from'] for r in results])
        top_senders = sender_counts.most_common(10)
        
        # Wichtigste Mails (nach Importance)
        important_mails = sorted([r for r in results if r['importance'] >= 7], 
                                key=lambda x: x['importance'], reverse=True)[:10]
        
        # Actionable Insights gesammelt
        all_actions = []
        for r in results:
            all_actions.extend(r.get('actionable', []))
        
        # Zeitliche Verteilung
        daily_counts = defaultdict(int)
        for r in results:
            if isinstance(r['date'], datetime):
                day = r['date'].strftime('%Y-%m-%d')
                daily_counts[day] += 1
        
        return {
            'total_emails': len(results),
            'successful_analyses': sum(1 for r in results if r['analysis_success']),
            'failed_analyses': sum(1 for r in results if not r['analysis_success']),
            'cluster_distribution': dict(cluster_counts),
            'sentiment_distribution': dict(sentiment_counts),
            'top_senders': top_senders,
            'important_emails': important_mails,
            'all_actions': all_actions[:20],
            'daily_distribution': dict(daily_counts),
            'emails_with_attachments': sum(1 for r in results if r['has_attachments'])
        }