import imaplib
import poplib
import email
from email.header import decode_header
from datetime import datetime
import hashlib

class EmailFetcher:
    """E-Mails per IMAP oder POP3 laden"""
    
    def __init__(self, server, port, username, password, use_imap=True):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.use_imap = use_imap
        self.connection = None
        
    def connect(self):
        """Verbindung herstellen"""
        try:
            if self.use_imap:
                # === WICHTIG: Lokaler Test-Server ohne SSL ===
                if self.server in ["localhost", "127.0.0.1"]:
                    self.connection = imaplib.IMAP4(self.server, self.port)   # KEIN SSL
                else:
                    self.connection = imaplib.IMAP4_SSL(self.server, self.port)  # Normal mit SSL
                
                self.connection.login(self.username, self.password)
                self.connection.select('INBOX')
            else:
                # POP3 (hier erstmal so lassen)
                self.connection = poplib.POP3_SSL(self.server, self.port)
                self.connection.user(self.username)
                self.connection.pass_(self.password)
                
            return True, "Verbunden"
            
        except Exception as e:
            return False, str(e)
    
    def fetch_emails(self, max_emails=200, progress_callback=None):
        """E-Mails herunterladen"""
        emails = []
        
        try:
            if self.use_imap:
                # IMAP: Suche nach allen Mails
                status, messages = self.connection.search(None, 'ALL')
                if status != 'OK':
                    return [], "Keine Mails gefunden"
                
                mail_ids = messages[0].split()
                mail_ids = mail_ids[-max_emails:]  # Letzte X Mails
                
                for i, mail_id in enumerate(mail_ids):
                    if progress_callback:
                        progress_callback(i + 1, len(mail_ids))
                    
                    status, msg_data = self.connection.fetch(mail_id, '(RFC822)')
                    if status == 'OK':
                        raw_email = msg_data[0][1]
                        email_msg = self._parse_email(raw_email, mail_id.decode())
                        emails.append(email_msg)
            else:
                # POP3
                num_messages = len(self.connection.list()[1])
                start = max(1, num_messages - max_emails + 1)
                
                for i in range(start, num_messages + 1):
                    if progress_callback:
                        progress_callback(i - start + 1, min(max_emails, num_messages))
                    
                    raw_email = self.connection.retr(i)[1]
                    raw_email = b'\r\n'.join(raw_email)
                    email_msg = self._parse_email(raw_email, str(i))
                    emails.append(email_msg)
            
            return emails, None
            
        except Exception as e:
            return [], str(e)
    
    def _parse_email(self, raw_email, mail_id):
        """E-Mail parsen und wichtige Infos extrahieren"""
        msg = email.message_from_bytes(raw_email)
        
        # Betreff dekodieren
        subject = self._decode_header(msg.get('Subject', 'Kein Betreff'))
        
        # Von dekodieren
        from_addr = self._decode_header(msg.get('From', 'Unbekannt'))
        
        # Datum parsen
        date_str = msg.get('Date', '')
        try:
            from email.utils import parsedate_to_datetime
            date = parsedate_to_datetime(date_str)
        except:
            date = datetime.now()
        
        # Body extrahieren
        body = self._extract_body(msg)
        
        # Anhänge erkennen (nur Metadaten)
        attachments = []
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') and 'attachment' in part.get('Content-Disposition'):
                filename = part.get_filename()
                if filename:
                    filename = self._decode_header(filename)
                    attachments.append({
                        'name': filename,
                        'size': len(part.get_payload(decode=True)) if part.get_payload(decode=True) else 0
                    })
        
        return {
            'id': mail_id,
            'subject': subject,
            'from': from_addr,
            'date': date,
            'body': body[:5000],  # Body auf 5000 Zeichen begrenzen
            'attachments': attachments,
            'has_attachments': len(attachments) > 0
        }
    
    def _decode_header(self, header):
        """E-Mail Header dekodieren"""
        if not header:
            return ""
        
        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    decoded = part.decode(encoding or 'utf-8', errors='ignore')
                except:
                    decoded = part.decode('utf-8', errors='ignore')
                decoded_parts.append(decoded)
            else:
                decoded_parts.append(part)
        return ' '.join(decoded_parts)
    
    def _extract_body(self, msg):
        """E-Mail Body extrahieren"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                
                if content_type == 'text/plain' and 'attachment' not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        try:
                            body += payload.decode('utf-8', errors='ignore')
                        except:
                            body += payload.decode('latin-1', errors='ignore')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                try:
                    body = payload.decode('utf-8', errors='ignore')
                except:
                    body = payload.decode('latin-1', errors='ignore')
        
        return body.strip()
    
    def disconnect(self):
        """Verbindung trennen"""
        if self.connection:
            if self.use_imap:
                self.connection.close()
                self.connection.logout()
            else:
                self.connection.quit()