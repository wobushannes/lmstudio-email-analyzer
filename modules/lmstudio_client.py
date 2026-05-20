import requests
import json
import time

class LMStudioClient:
    """LM-Studio API Client mit professionellem Error-Handling"""
    
    def __init__(self, api_url="http://localhost:1234/v1/chat/completions", timeout=60):
        self.api_url = api_url
        self.timeout = timeout
        
    def check_connection(self):
        """Prüfen ob LM-Studio läuft"""
        try:
            base_url = self.api_url.replace("/v1/chat/completions", "/v1/models")
            response = requests.get(base_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def analyze_email(self, email_data, system_prompt, clusters, max_tokens=4096, temperature=0.3):
        """Eine einzelne E-Mail analysieren mit Retry-Logic"""
        
        # E-Mail für Prompt aufbereiten
        email_text = f"""
Betreff: {email_data['subject']}
Von: {email_data['from']}
Datum: {email_data['date']}
Inhalt:
{email_data['body']}

Anhänge: {len(email_data['attachments'])} Datei(en)
"""
        
        # System-Prompt mit Clustern füllen
        filled_prompt = system_prompt.replace("{clusters}", ", ".join(clusters))
        
        messages = [
            {"role": "system", "content": filled_prompt},
            {"role": "user", "content": f"Analysiere diese E-Mail:\n\n{email_text}"}
        ]
        
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        # Retry-Logic (3 Versuche)
        for attempt in range(3):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    llm_response = result['choices'][0]['message']['content']
                    
                    # JSON aus der Antwort extrahieren
                    try:
                        json_start = llm_response.find('{')
                        json_end = llm_response.rfind('}') + 1
                        if json_start != -1 and json_end > json_start:
                            json_str = llm_response[json_start:json_end]
                            analysis = json.loads(json_str)
                            return {
                                'success': True,
                                'analysis': analysis,
                                'raw_response': llm_response
                            }
                        else:
                            return {
                                'success': False,
                                'error': 'Kein JSON in LLM-Antwort gefunden',
                                'raw_response': llm_response
                            }
                    except json.JSONDecodeError as e:
                        return {
                            'success': False,
                            'error': f'JSON-Parse-Fehler: {str(e)}',
                            'raw_response': llm_response
                        }
                else:
                    if attempt == 2:
                        return {
                            'success': False,
                            'error': f'HTTP {response.status_code}: {response.text}'
                        }
                    time.sleep(2)
                    
            except requests.exceptions.Timeout:
                if attempt == 2:
                    return {'success': False, 'error': 'Zeitüberschreitung bei LM-Studio'}
                time.sleep(3)
            except Exception as e:
                if attempt == 2:
                    return {'success': False, 'error': str(e)}
                time.sleep(2)
        
        return {'success': False, 'error': 'Unbekannter Fehler'}