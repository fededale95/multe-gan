"""Ogni mattina: se oggi qualcuno compie gli anni, manda una notifica sul canale ntfy della squadra.

- Chiede a Supabase solo i nomi di chi festeggia oggi (funzione pubblica compleanni_oggi):
  le date di nascita restano private.
- PROVA=1 manda una notifica di prova anche se oggi non e' il compleanno di nessuno.
- DRY_RUN=1 stampa la notifica senza inviarla.
"""
import json
import os
import urllib.request

NTFY_URL = "https://ntfy.sh"
TOPIC = os.environ.get("NTFY_TOPIC", "ganopenc1")
APP_URL = "https://fededale95.github.io/multe-gan/"


def compleanni_oggi():
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/rpc/compleanni_oggi"
    key = os.environ["SUPABASE_ANON_KEY"]
    req = urllib.request.Request(url, data=b"{}", method="POST", headers={
        "apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        dati = json.loads(r.read().decode() or "[]")
    return [x if isinstance(x, str) else x.get("compleanni_oggi") for x in dati if x]


def elenco(nomi):
    return nomi[0] if len(nomi) == 1 else ", ".join(nomi[:-1]) + " e " + nomi[-1]


def invia(titolo, testo, tags):
    msg = {"topic": TOPIC, "title": titolo, "message": testo, "tags": tags, "click": APP_URL}
    if os.environ.get("DRY_RUN") == "1":
        print("DRY_RUN, non invio:", json.dumps(msg, ensure_ascii=False))
        return
    req = urllib.request.Request(NTFY_URL, data=json.dumps(msg).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        print("Notifica inviata su ntfy:", r.status)


def main():
    nomi = compleanni_oggi()
    print("Compleanni di oggi:", nomi or "nessuno")
    if nomi:
        verbo = "compiono" if len(nomi) > 1 else "compie"
        invia("Compleanno nel GAN Open C1!",
              "Oggi %s gli anni %s! 🎉 Tanti auguri da tutta la squadra 💚🧡" % (verbo, elenco(nomi)),
              ["birthday", "tada"])
    elif os.environ.get("PROVA") == "1":
        invia("Prova notifiche GAN Open C1",
              "Le notifiche dei compleanni funzionano: il giorno del compleanno arriva un messaggio qui. 💚🧡",
              ["white_check_mark"])


if __name__ == "__main__":
    main()
