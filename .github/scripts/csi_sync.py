"""Aggiorna classifica e risultati del GAN dal sito del CSI Milano.

- Classifica del girone -> scritta in classifica.json (letta dalla sezione Classifica dell'app).
- Risultati delle gare del GAN -> inviati a Supabase, che li salva solo nelle gare
  ancora senza risultato.
- Marcatori del GAN letti dalla pagina della partita -> salvati solo se il capitano
  non li ha gia' inseriti ("Giocatore non indicato" viene saltato; gli assist sul
  sito CSI non ci sono e restano da inserire a mano).

Usa solo la libreria standard di Python. Variabili d'ambiente:
  SUPABASE_URL, SUPABASE_ANON_KEY, CSI_BOT_TOKEN (segreto del repository).
"""
import datetime
import html
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

CSI_AJAX = "https://www.csi.milano.it/public/ajax/filtri.php"
CSI_PAGE = "https://www.csi.milano.it/albo/risultati-calendario-classifiche-squadre.html?campionato=116&q=cla"
CAMPIONATO = "116"   # Calcio Open C - A 7
GIRONE = "D"
SQUADRA_GAN = "1623"  # GAN OPEN C1
NOME_GAN = "GAN OPEN C1"
OUT = "classifica.json"
CSI_BASE = "https://www.csi.milano.it"


def csi_post(params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(CSI_AJAX, data=data, headers={
        "User-Agent": "GAN-Open-C1-app/1.0 (aggiornamento classifica squadra)",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.csi.milano.it/albo/risultati-calendario-classifiche-squadre.html",
    })
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def cell_text(td):
    return html.unescape(re.sub(r"<[^>]+>", "", td)).strip()


def parse_classifica(page):
    righe = []
    for tr in re.findall(r"<tr([^>]*)>(.*?)</tr>", page, flags=re.S):
        attrs, body = tr
        tds = re.findall(r"<td[^>]*>(.*?)</td>", body, flags=re.S)
        if len(tds) < 11:
            continue
        vals = [cell_text(t) for t in tds]
        # pos, logo, squadra, punti, giocate, vinte, perse, pareggiate, penalita, gf, gs
        try:
            nums = [int(v) for v in (vals[0], vals[3], vals[4], vals[5], vals[6], vals[7], vals[8], vals[9], vals[10])]
        except ValueError:
            continue
        zona = "promozione" if "cla_green" in attrs else "playoff" if "cla_blue" in attrs else ""
        righe.append({
            "pos": nums[0], "squadra": vals[2], "pt": nums[1], "g": nums[2], "v": nums[3],
            "p": nums[4], "n": nums[5], "pen": nums[6], "gf": nums[7], "gs": nums[8],
            "zona": zona, "ufficiosa": "ufficiosa" in attrs,
        })
    return righe


def parse_risultati_gan(page):
    out = []
    for attrs, body in re.findall(r"<tr([^>]*)>(.*?)</tr>", page, flags=re.S):
        cod = re.search(r'<td class="codice">\s*([^<\s]+)', body)
        squadre = re.findall(r'<td class="squadra">(.*?)</td>', body, flags=re.S)
        punt = re.search(r'<td class="punteggio"[^>]*>(.*?)</td>', body, flags=re.S)
        if not (cod and len(squadre) == 2 and punt):
            continue
        casa, ospite = cell_text(squadre[0]).upper(), cell_text(squadre[1]).upper()
        if NOME_GAN not in (casa, ospite):
            continue
        m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", cell_text(punt.group(1)))
        if not m:
            continue  # partita non ancora giocata, rinviata (REC.), ecc.
        link = re.search(r'href="(/albo/partite/[^"]+)"', body)
        out.append({"codice": cod.group(1), "gol_casa": int(m.group(1)), "gol_ospiti": int(m.group(2)),
                    "_casa": casa == NOME_GAN, "_link": link.group(1) if link else None})
    return out


def csi_get(path):
    req = urllib.request.Request(CSI_BASE + path, headers={"User-Agent": "GAN-Open-C1-app/1.0 (aggiornamento classifica squadra)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_marcatori_gan(page, gan_in_casa):
    """Nomi dei marcatori del GAN nell'ordine del sito; None = sezione assente."""
    blocco = re.search(r'<div class="%s">(.*?)</table>' % ("squadra_casa" if gan_in_casa else "squadra_ospite"), page, flags=re.S)
    if not blocco:
        return None
    nomi = []
    for tr in re.findall(r"<tr>(.*?)</tr>", blocco.group(1), flags=re.S):
        a = re.search(r'<a href="/albo/giocatori/[^"]*-%s-[^"]*">(.*?)</a>' % SQUADRA_GAN, tr, flags=re.S)
        if a:
            nomi.append(cell_text(a.group(1)))
    return nomi


def tokens(nome):
    t = unicodedata.normalize("NFKD", nome)
    t = "".join(c for c in t if not unicodedata.combining(c)).upper()
    return set(w for w in re.split(r"[^A-Z]+", t) if w)


def abbina(nome_csi, rosa):
    """'LUIGI COLANTUONI' -> 'Colantuoni Luigi' se c'e' un solo giocatore compatibile in rosa."""
    tc = tokens(nome_csi)
    cand = [n for n in rosa if tokens(n) and tokens(n) <= tc]
    if cand:
        best = max(len(tokens(n)) for n in cand)
        top = [n for n in cand if len(tokens(n)) == best]
        if len(top) == 1:
            return top[0]
    return nome_csi.title()  # non in rosa (o ambiguo): nome come sul sito CSI


def supabase_get(path):
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + path
    key = os.environ["SUPABASE_ANON_KEY"]
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode() or "[]")


def supabase_rpc(name, payload):
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/rpc/" + name
    key = os.environ["SUPABASE_ANON_KEY"]
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers={
        "apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode() or "null")


def main():
    errori = 0

    # --- classifica
    try:
        righe = parse_classifica(csi_post({"albo": "ok", "classifiche": "ok", "campionato": CAMPIONATO, "squadra": "", "girone": GIRONE}))
        if len(righe) < 2:
            raise RuntimeError("classifica vuota o formato cambiato")
        old = {}
        if os.path.exists(OUT):
            with open(OUT, encoding="utf-8") as f:
                old = json.load(f)
        if old.get("righe") != righe:
            now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
            data = {"girone": "Calcio Open C a 7 - Girone D", "fonte": CSI_PAGE, "aggiornata": now, "righe": righe}
            with open(OUT, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
                f.write("\n")
            print("Classifica aggiornata:", len(righe), "squadre")
        else:
            print("Classifica invariata")
    except Exception as e:  # noqa: BLE001
        errori += 1
        print("ERRORE classifica:", e, file=sys.stderr)

    # --- risultati del GAN
    try:
        ris = parse_risultati_gan(csi_post({"albo": "ok", "risultati": "ok", "campionato": CAMPIONATO, "squadra": SQUADRA_GAN, "girone": GIRONE}))
        print("Risultati GAN trovati sul sito CSI:", len(ris))
        token = os.environ.get("CSI_BOT_TOKEN", "")
        if not token:
            raise RuntimeError("manca il segreto CSI_BOT_TOKEN")
        # marcatori: leggo la pagina della partita solo se nell'app mancano ancora
        gare = {g["codice"]: g for g in supabase_get("gare?select=id,codice&codice=not.is.null")}
        gol = supabase_get("gol?select=gara_id,fonte")
        rosa = [c["nome"] for c in supabase_get("certificati?select=nome")]
        for r in ris:
            gan = r["gol_casa"] if r["_casa"] else r["gol_ospiti"]
            g = gare.get(r["codice"])
            if not g or gan == 0 or not r["_link"]:
                continue
            righe = [x for x in gol if x["gara_id"] == g["id"]]
            if any(x["fonte"] != "csi" for x in righe) or len(righe) >= gan:
                continue  # gia' inseriti dal capitano, o gia' completi
            nomi = parse_marcatori_gan(csi_get(r["_link"]), r["_casa"])
            if nomi:
                r["marcatori"] = [abbina(n, rosa) for n in nomi][:gan]
                print("Marcatori trovati per", r["codice"], ":", ", ".join(r["marcatori"]))
        payload = [{k: v for k, v in r.items() if not k.startswith("_")} for r in ris]
        esito = supabase_rpc("importa_risultati", {"p_token": token, "p_risultati": payload})
        print("Esito importazione:", esito)
    except Exception as e:  # noqa: BLE001
        errori += 1
        print("ERRORE risultati:", e, file=sys.stderr)

    sys.exit(1 if errori else 0)


if __name__ == "__main__":
    main()
