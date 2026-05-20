import imaplib
import poplib
import email
from email.header import decode_header
from datetime import datetime
import hashlib
import socket
import time

class EmailFetcher:
    """E-Mails per IMAP oder POP3 laden mit Timeouts und Retry-Logic"""
    
    def __init__(self, server, port, username, password, use_imap=True, timeout=30, max_retries=3):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.use_imap = use_imap
        self.timeout = timeout
        self.max_retries = max_retries
        self.connection = None
        
    def connect(self):
        """Verbindung herstellen mit Retry-Logic"""
        for attempt in range(self.max_retries):
            try:
                if self.use_imap:
                    # IMAP mit Timeout
                    self.connection = imaplib.IMAP4_SSL(self.server, self.port, timeout=self.timeout)
                    self.connection.login(self.username, self.password)
                    self.connection.select('INBOX')
                    return True, f"Verbunden (Versuch {attempt + 1})"
                else:
                    # POP3 mit Timeout
                    socket.setdefaulttimeout(self.timeout)
                    self.connection = poplib.POP3_SSL(self.server, self.port)
                    self.connection.user(self.username)
                    self.connection.pass_(self.password)
                    return True, f"Verbunden (Versuch {attempt + 1})"
                    
            except socket.timeout:
                if attempt == self.max_retries - 1:
                    return False, f"Verbindungs-Timeout nach {self.timeout}s ({self.max_retries} Versuche)"
                time.sleep(2)
                
            except imaplib.IMAP4.error as e:
                if "authentication" in str(e).lower():
                    return False, f"Authentifizierungsfehler: {str(e)}"
                if attempt == self.max_retries - 1:
                    return False, f"IMAP-Fehler: {str(e)}"
                time.sleep(2)
                
            except poplib.error_proto as e:
                if "authentication" in str(e).lower():
                    return False, f"Authentifizierungsfehler: {str(e)}"
                if attempt == self.max_retries - 1:
                    return False, f"POP3-Fehler: {str(e)}"
                time.sleep(2)
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return False, str(e)
                time.sleep(2)
        
        return False, "Unbekannter Verbindungsfehler"
    
    def fetch_emails(self, max_emails=200, progress_callback=None):
        """E-Mails herunterladen mit Timeout und Abbruch bei zu langer Wartezeit"""
        emails = []
        
        try:
            if self.use_imap:
                # IMAP: Suche mit Timeout
                socket.setdefaulttimeout(self.timeout)
                
                try:
                    status, messages = self.connection.search(None, 'ALL')
                    if status != 'OK':
                        return [], "Keine Mails gefunden"
                except socket.timeout:
                    return [], f"Suchanfrage Timeout nach {self.timeout}s"
                
                mail_ids = messages[0].split()
                mail_ids = mail_ids[-max_emails:] if max_emails > 0 else mail_ids
                
                for i, mail_id in enumerate(mail_ids):
                    if progress_callback:
                        progress_callback(i + 1, len(mail_ids))
                    
                    # Einzelne Mail mit Timeout laden
                    try:
                        socket.setdefaulttimeout(self.timeout)
                        status, msg_data = self.connection.fetch(mail_id, '(RFC822)')
                        if status == 'OK':
                            raw_email = msg_data[0][1]
                            email_msg = self._parse_email(raw_email, mail_id.decode())
                            emails.append(email_msg)
                        else:
                            # Fehlerhafte Mail überspringen
                            continue
                    except socket.timeout:
                        # Timeout bei einer Mail – trotzdem weitermachen
                        continue
                    except Exception:
                        continue
                        
            else:
                # POP3
                try:
                    num_messages = len(self.connection.list()[1])
                except socket.timeout:
                    return [], f"LIST-Kommando Timeout nach {self.timeout}s"
                
                start = max(1, num_messages - max_emails + 1) if max_emails > 0 else 1
                
                for i in range(start, num_messages + 1):
                    if progress_callback:
                        progress_callback(i - start + 1, min(max_emails, num_messages) if max_emails > 0 else num_messages)
                    
                    try:
                        socket.setdefaulttimeout(self.timeout)
                        raw_email = self.connection.retr(i)[1]
                        raw_email = b'\r\n'.join(raw_email)
                        email_msg = self._parse_email(raw_email, str(i))
                        emails.append(email_msg)
                    except socket.timeout:
                        continue
                    except Exception:
                        continue
            
            return emails, None
            
        except socket.timeout:
            return [], f"Allgemeiner Timeout nach {self.timeout}s"
        except Exception as e:
            return [], str(e)
    
    def _parse_email(self, raw_email, mail_id):
        """E-Mail parsen und wichtige Infos extrahieren"""
        try:
            msg = email.message_from_bytes(raw_email)
        except:
            # Fallback für korrupte Mails
            return {
                'id': mail_id,
                'subject': 'Fehler: Konnte nicht geparst werden',
                'from': 'Unbekannt',
                'date': datetime.now(),
                'body': '',
                'attachments': [],
                'has_attachments': False
            }
        
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
            'subject': subject[:500],  # Begrenzung
            'from': from_addr[:200],
            'date': date,
            'body': body[:5000],
            'attachments': attachments,
            'has_attachments': len(attachments) > 0
        }
    
    def _decode_header(self, header):
        """E-Mail Header dekodieren"""
        if not header:
            return ""
        
        decoded_parts = []
        try:
            for part, encoding in decode_header(header):
                if isinstance(part, bytes):
                    try:
                        decoded = part.decode(encoding or 'utf-8', errors='ignore')
                    except:
                        decoded = part.decode('utf-8', errors='ignore')
                    decoded_parts.append(decoded)
                else:
                    decoded_parts.append(part)
        except:
            return str(header)
        
        return ' '.join(decoded_parts)
    
    def _extract_body(self, msg):
        """E-Mail Body extrahieren"""
        body = ""
        
        try:
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
        except:
            body = ""
        
        return body.strip()
    
    def disconnect(self):
        """Verbindung trennen (sicher)"""
        try:
            if self.connection:
                if self.use_imap:
                    try:
                        self.connection.close()
                    except:
                        pass
                    try:
                        self.connection.logout()
                    except:
                        pass
                else:
                    try:
                        self.connection.quit()
                    except:
                        pass
        except:
            pass
        finally:
            self.connection = None