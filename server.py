import socket
import threading
import json
from datetime import datetime

HOST = "192.168.1.21" # A Changer selon votre adresse IP locale pour le serveur
PORT = 5555
BUFFER = 4096

# Dictionnaire des clients connectés : adresse -> pseudo
clients = {}
clients_lock = threading.Lock()


def broadcast(message: dict, exclude: tuple = None):
    """Envoie un message JSON à tous les clients connectés, sauf `exclude`."""
    data = json.dumps(message).encode()
    with clients_lock:
        for addr in list(clients):
            if addr != exclude:
                try:
                    sock.sendto(data, addr)
                except Exception as e:
                    print(f"[ERREUR] Envoi vers {addr} : {e}")


def handle_message(data: bytes, addr: tuple):
    """Traite un paquet reçu d'un client."""
    try:
        msg = json.loads(data.decode())
    except json.JSONDecodeError:
        return

    mtype = msg.get("type")

    # ── Connexion ──────────────────────────────────────────────────────────
    if mtype == "join":
        pseudo = msg.get("pseudo", "Anonyme")[:20]
        with clients_lock:
            clients[addr] = pseudo
        print(f"[+] {pseudo} connecté depuis {addr}")

        # Confirme la connexion au nouveau client (avec le compteur)
        sock.sendto(json.dumps({
            "type": "info",
            "content": f"Bienvenue {pseudo} ! {len(clients)} utilisateur(s) en ligne.",
            "count": len(clients)
        }).encode(), addr)

        # Annonce aux autres
        broadcast({
            "type": "message",
            "pseudo": "Serveur",
            "content": f"{pseudo} a rejoint le chat.",
            "time": datetime.now().strftime("%H:%M")
        }, exclude=addr)

    # ── Message normal ─────────────────────────────────────────────────────
    elif mtype == "message":
        with clients_lock:
            pseudo = clients.get(addr, "Inconnu")
        content = msg.get("content", "").strip()
        if not content:
            return
        now = datetime.now().strftime("%H:%M")
        print(f"[{now}] {pseudo}: {content}")
        broadcast({
            "type": "message",
            "pseudo": pseudo,
            "content": content,
            "time": now
        })

    # ── Déconnexion ────────────────────────────────────────────────────────
    elif mtype == "leave":
        with clients_lock:
            pseudo = clients.pop(addr, "Inconnu")
        print(f"[-] {pseudo} déconnecté")
        broadcast({
            "type": "message",
            "pseudo": "Serveur",
            "content": f"{pseudo} a quitté le chat.",
            "time": datetime.now().strftime("%H:%M")
        })

    # ── Heartbeat / ping ───────────────────────────────────────────────────
    elif mtype == "ping":
        sock.sendto(json.dumps({"type": "pong"}).encode(), addr)


def listen():
    """Boucle principale : écoute les paquets UDP entrants."""
    print(f"[SERVEUR] En écoute sur {HOST}:{PORT} …")
    while True:
        try:
            data, addr = sock.recvfrom(BUFFER)
            threading.Thread(target=handle_message, args=(data, addr), daemon=True).start()
        except Exception as e:
            print(f"[ERREUR] Réception : {e}")


if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    listen()
