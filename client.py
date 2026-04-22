import socket
import threading
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime

BUFFER = 4096
PING_INTERVAL = 10  # secondes


class ChatClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5)
        self.server_addr = None
        self.pseudo = ""
        self.connected = False

        self._build_login_window()

    # ── Fenêtre de connexion ───────────────────────────────────────────────
    def _build_login_window(self):
        self.root = tk.Tk()
        self.root.title("UDP Chat — Connexion")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        frame = tk.Frame(self.root, bg="#1e1e2e", padx=30, pady=30)
        frame.pack()

        tk.Label(frame, text="UDP Chat", font=("Helvetica", 18, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").grid(row=0, column=0, columnspan=2, pady=(0, 20))

        for i, (label, attr) in enumerate([
            ("Adresse du serveur", "entry_host"),
            ("Port", "entry_port"),
            ("Pseudo", "entry_pseudo"),
        ]):
            tk.Label(frame, text=label, fg="#a6adc8", bg="#1e1e2e",
                     font=("Helvetica", 10)).grid(row=i+1, column=0, sticky="w", pady=4)
            e = tk.Entry(frame, width=22, bg="#313244", fg="#cdd6f4",
                         insertbackground="#cdd6f4", relief="flat", font=("Helvetica", 11))
            e.grid(row=i+1, column=1, padx=(10, 0), pady=4)
            setattr(self, attr, e)

        self.entry_host.insert(0, "192.168.1.100")
        self.entry_port.insert(0, "5555")
        self.entry_pseudo.insert(0, "Moi")

        tk.Button(frame, text="Se connecter", command=self._connect,
                  bg="#89b4fa", fg="#1e1e2e", font=("Helvetica", 11, "bold"),
                  relief="flat", padx=12, pady=6, cursor="hand2"
                  ).grid(row=4, column=0, columnspan=2, pady=(20, 0))

        self.root.bind("<Return>", lambda _: self._connect())
        self.root.mainloop()

    # ── Connexion au serveur ───────────────────────────────────────────────
    def _connect(self):
        host = self.entry_host.get().strip()
        port_str = self.entry_port.get().strip()
        pseudo = self.entry_pseudo.get().strip()

        if not host or not port_str or not pseudo:
            messagebox.showerror("Erreur", "Tous les champs sont requis.")
            return
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Erreur", "Port invalide.")
            return

        self.server_addr = (host, port)
        self.pseudo = pseudo

        try:
            self._send({"type": "join", "pseudo": pseudo})
            # Attend la confirmation du serveur
            self.sock.settimeout(5)
            data, _ = self.sock.recvfrom(BUFFER)
            msg = json.loads(data.decode())
            if msg.get("type") not in ("info", "message"):
                raise ConnectionError("Réponse inattendue.")
        except Exception as e:
            messagebox.showerror("Connexion échouée", str(e))
            return

        self.connected = True
        self.sock.settimeout(None)

        self.root.destroy()
        self._build_chat_window()

    # ── Fenêtre de chat ────────────────────────────────────────────────────
    def _build_chat_window(self):
        self.root = tk.Tk()
        self.root.title(f"UDP Chat — {self.pseudo}")
        self.root.configure(bg="#1e1e2e")
        self.root.geometry("620x480")
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

        # Zone de messages
        self.chat_area = scrolledtext.ScrolledText(
            self.root, state="disabled", wrap="word",
            bg="#181825", fg="#cdd6f4", font=("Helvetica", 11),
            relief="flat", padx=10, pady=8
        )
        self.chat_area.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # Config des tags couleur
        self.chat_area.tag_config("pseudo_me",     foreground="#89b4fa", font=("Helvetica", 11, "bold"))
        self.chat_area.tag_config("pseudo_other",  foreground="#a6e3a1", font=("Helvetica", 11, "bold"))
        self.chat_area.tag_config("pseudo_server", foreground="#f38ba8", font=("Helvetica", 11, "bold"))
        self.chat_area.tag_config("time",          foreground="#585b70", font=("Helvetica", 9))
        self.chat_area.tag_config("text",          foreground="#cdd6f4")

        # Barre d'envoi
        bottom = tk.Frame(self.root, bg="#1e1e2e")
        bottom.pack(fill="x", padx=10, pady=8)

        self.entry_msg = tk.Entry(bottom, bg="#313244", fg="#cdd6f4",
                                  insertbackground="#cdd6f4", font=("Helvetica", 12),
                                  relief="flat")
        self.entry_msg.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self.entry_msg.bind("<Return>", lambda _: self._send_message())

        tk.Button(bottom, text="Envoyer", command=self._send_message,
                  bg="#89b4fa", fg="#1e1e2e", font=("Helvetica", 10, "bold"),
                  relief="flat", padx=10, cursor="hand2").pack(side="left")

        # Lance la réception et le ping en arrière-plan
        threading.Thread(target=self._receive_loop, daemon=True).start()
        threading.Thread(target=self._ping_loop,    daemon=True).start()

        self._append_info("Connecté au serveur !")
        self.root.mainloop()

    # ── Envoi d'un message ─────────────────────────────────────────────────
    def _send_message(self):
        content = self.entry_msg.get().strip()
        if not content:
            return
        self.entry_msg.delete(0, "end")
        self._send({"type": "message", "content": content})

        # Affiche le message côté local
        now = datetime.now().strftime("%H:%M")
        self._append_message(self.pseudo, content, now, is_me=True)

    # ── Réception des paquets ──────────────────────────────────────────────
    def _receive_loop(self):
        while self.connected:
            try:
                data, _ = self.sock.recvfrom(BUFFER)
                msg = json.loads(data.decode())
                mtype = msg.get("type")

                if mtype == "message":
                    # Ne pas ré-afficher nos propres messages (déjà ajoutés localement)
                    if msg.get("pseudo") == self.pseudo:
                        continue
                    self._append_message(
                        msg.get("pseudo", "?"),
                        msg.get("content", ""),
                        msg.get("time", ""),
                        is_me=False
                    )
                elif mtype == "info":
                    self._append_info(msg.get("content", ""))

            except (json.JSONDecodeError, OSError):
                pass

    # ── Ping périodique ────────────────────────────────────────────────────
    def _ping_loop(self):
        import time
        while self.connected:
            time.sleep(PING_INTERVAL)
            self._send({"type": "ping"})

    # ── Helpers ────────────────────────────────────────────────────────────
    def _send(self, payload: dict):
        try:
            self.sock.sendto(json.dumps(payload).encode(), self.server_addr)
        except Exception as e:
            print(f"[ERREUR] Envoi : {e}")

    def _append_message(self, pseudo: str, content: str, time_str: str, is_me: bool):
        self.chat_area.config(state="normal")
        tag = "pseudo_me" if is_me else (
              "pseudo_server" if pseudo == "Serveur" else "pseudo_other")
        self.chat_area.insert("end", f"{pseudo} ", tag)
        self.chat_area.insert("end", f"[{time_str}]\n", "time")
        self.chat_area.insert("end", f"{content}\n\n", "text")
        self.chat_area.config(state="disabled")
        self.chat_area.see("end")

    def _append_info(self, text: str):
        self.chat_area.config(state="normal")
        self.chat_area.insert("end", f"── {text} ──\n\n", "pseudo_server")
        self.chat_area.config(state="disabled")
        self.chat_area.see("end")

    def _quit(self):
        self.connected = False
        self._send({"type": "leave"})
        self.sock.close()
        self.root.destroy()


if __name__ == "__main__":
    ChatClient()
