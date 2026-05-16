import asyncio
import threading
import time
import random
from faker import Faker
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

fake = Faker('de_DE')

# ====================== Zugangsdaten ======================
USERNAME = "test@local.test"
PASSWORD = "password123"

SMTP_PORT = 1025
IMAP_PORT = 1143

def start_localmail():
    """Startet localmail im Hintergrund"""
    import localmail
    print(f"🟢 Starte lokalen Mail-Server (SMTP:{SMTP_PORT} | IMAP:{IMAP_PORT})")
    
    def run_server():
        # Korrekte Aufrufweise: positionale Argumente
        localmail.run(SMTP_PORT, IMAP_PORT, 0, None)   # http_port=0 → deaktiviert
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(2.5)  # Etwas länger warten, bis Twisted hochgefahren ist


async def send_dummy_mails(anzahl=300):
    print(f"📨 Sende {anzahl} Dummy-Mails...")
    
    for attempt in range(5):  # Warte kurz, falls Server noch nicht ganz bereit
        try:
            with smtplib.SMTP('localhost', SMTP_PORT) as smtp:
                smtp.login(USERNAME, PASSWORD)   # Auth wird akzeptiert
                
                for i in range(anzahl):
                    msg = MIMEMultipart()
                    msg['From'] = fake.email()
                    msg['To'] = fake.email()
                    msg['Subject'] = fake.sentence(nb_words=random.randint(4, 10))
                    
                    body = f"""
                    <h3>{fake.sentence(nb_words=8)}</h3>
                    <p>{fake.paragraph(nb_sentences=6)}</p>
                    <p>{fake.paragraph(nb_sentences=5)}</p>
                    <br>
                    Mit freundlichen Grüßen<br>
                    {fake.name()}<br>
                    {fake.company()}
                    """
                    msg.attach(MIMEText(body, 'html'))
                    
                    smtp.send_message(msg)
                    
                    if (i + 1) % 50 == 0:
                        print(f"   → {i+1} Mails gesendet")
                    
                    await asyncio.sleep(random.uniform(0.05, 0.12))
                break
                
        except Exception as e:
            if attempt == 4:
                print(f"❌ Konnte keine Verbindung zum Server herstellen: {e}")
                return
            print(f"Warte auf Server... ({attempt+1}/5)")
            await asyncio.sleep(1.5)

    print("\n✅ Fertig! Alle Mails sind im Postfach.")


if __name__ == "__main__":
    start_localmail()
    
    print("\n=== Zugangsdaten ===")
    print(f"SMTP → localhost:{SMTP_PORT}")
    print(f"IMAP → localhost:{IMAP_PORT}")
    print(f"Benutzername: {USERNAME}")
    print(f"Passwort:    {PASSWORD}")
    print("(Auth wird akzeptiert, egal was du eingibst)")
    
    asyncio.run(send_dummy_mails(300))
    
    print("\nServer läuft weiter (Strg+C zum Beenden)")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nBeendet.")