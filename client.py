import socket
import threading
import json
import time
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime
from version import FULL_NAME

BUFFER        = 4096
PING_INTERVAL = 12

DEFAULT_SERVERS = [
    {"label": "Local VM",  "host": "192.168.1.100", "port": 5555},
    {"label": "Localhost", "host": "127.0.0.1",     "port": 5555},
]


class ChatClient:
    def __init__(self):
        self.sock        = None
        self.server_addr = None
        self.pseudo      = ""
        self.connected   = False
        self.user_count  = 0
        self.servers: list[dict] = list(DEFAULT_SERVERS)
        self.root        = None
        self._exit_app   = False

        self._run()

    # ══════════════════════════════════════════════════════════════════════
    # BOUCLE PRINCIPALE
    # ══════════════════════════════════════════════════════════════════════
    def _run(self):
        """Boucle principale : login → chat → login (si déconnexion volontaire)."""
        while True:
            ok = self._show_login()
            if not ok:
                break                      # Fermeture de la fenêtre login → quitte
            self._show_chat()
            if self._exit_app:
                break                      # Croix du chat → quitte
            # Sinon (bouton Déconnexion) → reboucle vers login

    # ══════════════════════════════════════════════════════════════════════
    # FENÊTRE DE LOGIN
    # ══════════════════════════════════════════════════════════════════════
    def _show_login(self) -> bool:
        """Affiche la fenêtre de login. Retourne True si connexion réussie."""
        self._login_success = False
        self.root = tk.Tk()
        self.root.title(f"{FULL_NAME} — Connexion")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")
        self.root.protocol("WM_DELETE_WINDOW", self._login_close)

        # En-tête
        header = tk.Frame(self.root, bg="#181825", pady=18)
        header.pack(fill="x")
        tk.Label(header, text="PyChat", font=("Helvetica", 22, "bold"),
                 fg="#cdd6f4", bg="#181825").pack()
        tk.Label(header, text=FULL_NAME, font=("Helvetica", 9),
                 fg="#585b70", bg="#181825").pack()

        # Formulaire
        form = tk.Frame(self.root, bg="#1e1e2e", padx=30, pady=24)
        form.pack()

        # Pseudo
        tk.Label(form, text="Pseudo", fg="#a6adc8", bg="#1e1e2e",
                 font=("Helvetica", 10)).grid(row=0, column=0, sticky="w", pady=6)
        self.entry_pseudo = self._mk_entry(form)
        self.entry_pseudo.insert(0, self.pseudo or "Moi")
        self.entry_pseudo.grid(row=0, column=1, padx=(12, 0), pady=6)

        # Séparateur
        tk.Frame(form, bg="#313244", height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=10)

        # Menu serveur
        tk.Label(form, text="Serveur", fg="#a6adc8", bg="#1e1e2e",
                 font=("Helvetica", 10)).grid(row=2, column=0, sticky="w", pady=6)

        self.server_var = tk.StringVar()
        self.server_var.trace_add("write", self._on_server_select)

        om_frame = tk.Frame(form, bg="#1e1e2e")
        om_frame.grid(row=2, column=1, padx=(12, 0), pady=6, sticky="w")
        self._rebuild_server_menu(om_frame)

        # IP / Port
        fields = tk.Frame(form, bg="#1e1e2e")
        fields.grid(row=3, column=0, columnspan=2, pady=(4, 0))

        tk.Label(fields, text="IP", fg="#585b70", bg="#1e1e2e",
                 font=("Helvetica", 9)).grid(row=0, column=0, sticky="w")
        self.entry_host = self._mk_entry(fields, width=18)
        self.entry_host.grid(row=0, column=1, padx=(8, 16))

        tk.Label(fields, text="Port", fg="#585b70", bg="#1e1e2e",
                 font=("Helvetica", 9)).grid(row=0, column=2, sticky="w")
        self.entry_port = self._mk_entry(fields, width=6)
        self.entry_port.grid(row=0, column=3, padx=(8, 0))

        # Pré-sélectionne le premier serveur
        self.server_var.set(self.servers[0]["label"])

        # Bouton connexion
        tk.Button(form, text="Se connecter", command=self._do_login,
                  bg="#89b4fa", fg="#1e1e2e", font=("Helvetica", 11, "bold"),
                  relief="flat", padx=14, pady=8, cursor="hand2"
                  ).grid(row=4, column=0, columnspan=2, pady=(20, 0))

        self.root.bind("<Return>", lambda _: self._do_login())
        self.root.mainloop()
        return self._login_success

    def _login_close(self):
        """Croix fenêtre login → quitte l'app."""
        self._exit_app = True
        self.root.destroy()

    def _do_login(self):
        """Tentative de connexion depuis l'écran login."""
        host   = self.entry_host.get().strip()
        port_s = self.entry_port.get().strip()
        pseudo = self.entry_pseudo.get().strip()

        if not host or not port_s or not pseudo:
            messagebox.showerror("Erreur", "Tous les champs sont requis.")
            return
        try:
            port = int(port_s)
        except ValueError:
            messagebox.showerror("Erreur", "Port invalide.")
            return

        err = self._connect_to(host, port, pseudo)
        if err:
            messagebox.showerror("Connexion échouée", err)
            return

        # Mémorise le serveur si nouveau
        label = self.server_var.get()
        if label == "Autre…":
            label = f"{host}:{port}"
        if not any(s["host"] == host and s["port"] == port for s in self.servers):
            self.servers.append({"label": label, "host": host, "port": port})

        self._login_success = True
        self.root.destroy()    # Ferme login → _run() continue vers _show_chat()

    # ══════════════════════════════════════════════════════════════════════
    # CONNEXION RÉSEAU
    # ══════════════════════════════════════════════════════════════════════
    def _connect_to(self, host: str, port: int, pseudo: str) -> "str | None":
        """
        Ouvre un socket UDP et envoie un join.
        Retourne None si succès, sinon un message d'erreur.
        """
        if self.sock:
            try: self.sock.close()
            except: pass

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        try:
            sock.sendto(json.dumps({"type": "join", "pseudo": pseudo}).encode(), (host, port))
            data, _ = sock.recvfrom(BUFFER)
            msg = json.loads(data.decode())
            if msg.get("type") not in ("info", "message"):
                raise ConnectionError("Réponse inattendue du serveur.")
            if "count" in msg:
                self.user_count = int(msg["count"])
        except Exception as e:
            sock.close()
            return str(e)

        sock.settimeout(None)
        self.sock        = sock
        self.server_addr = (host, port)
        self.pseudo      = pseudo
        self.connected   = True
        return None

    def _disconnect(self, send_leave: bool = True):
        """Envoie leave, ferme le socket, passe connected=False."""
        self.connected = False
        if send_leave and self.sock and self.server_addr:
            try:
                self.sock.sendto(
                    json.dumps({"type": "leave"}).encode(), self.server_addr)
            except: pass
        if self.sock:
            try: self.sock.close()
            except: pass
        self.sock = None

    # ══════════════════════════════════════════════════════════════════════
    # FENÊTRE DE CHAT
    # ══════════════════════════════════════════════════════════════════════
    def _show_chat(self):
        self._exit_app = False

        self.root = tk.Tk()
        self.root.title(f"PyChat — {self.pseudo}")
        self.root.configure(bg="#1e1e2e")
        self.root.geometry("700x540")
        self.root.minsize(520, 400)
        self.root.protocol("WM_DELETE_WINDOW", self._chat_close)

        self._build_topbar()
        self._build_chat_area()
        self._build_bottom_bar()
        self._start_threads()

        self._append_info(f"Connecté à {self.server_addr[0]}:{self.server_addr[1]}")
        self.root.mainloop()

    # ── Topbar ────────────────────────────────────────────────────────────
    def _build_topbar(self):
        bar = tk.Frame(self.root, bg="#181825", pady=8, padx=12)
        bar.pack(fill="x")

        # Gauche : point vert + adresse serveur
        left = tk.Frame(bar, bg="#181825")
        left.pack(side="left")

        dot = tk.Canvas(left, width=10, height=10, bg="#181825", highlightthickness=0)
        dot.pack(side="left", padx=(0, 7))
        dot.create_oval(1, 1, 9, 9, fill="#a6e3a1", outline="")

        self.lbl_server = tk.Label(
            left, text=f"{self.server_addr[0]}:{self.server_addr[1]}",
            fg="#cdd6f4", bg="#181825", font=("Helvetica", 10, "bold"))
        self.lbl_server.pack(side="left")

        # Droite : compteur + boutons
        right = tk.Frame(bar, bg="#181825")
        right.pack(side="right")

        self.lbl_users = tk.Label(
            right, text=f"👤 {self.user_count}",
            fg="#a6adc8", bg="#181825", font=("Helvetica", 10))
        self.lbl_users.pack(side="right", padx=(8, 0))

        tk.Button(right, text="Déconnexion",
                  command=self._do_disconnect,
                  bg="#f38ba8", fg="#1e1e2e", font=("Helvetica", 9, "bold"),
                  relief="flat", padx=10, pady=3, cursor="hand2"
                  ).pack(side="right", padx=(0, 6))

        tk.Button(right, text="Changer de serveur",
                  command=self._open_server_switcher,
                  bg="#313244", fg="#cdd6f4", font=("Helvetica", 9),
                  relief="flat", padx=10, pady=3, cursor="hand2"
                  ).pack(side="right", padx=(0, 6))

    # ── Zone de messages ──────────────────────────────────────────────────
    def _build_chat_area(self):
        self.chat_area = scrolledtext.ScrolledText(
            self.root, state="disabled", wrap="word",
            bg="#181825", fg="#cdd6f4", font=("Helvetica", 11),
            relief="flat", padx=12, pady=10, selectbackground="#45475a")
        self.chat_area.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        self.chat_area.tag_config("pseudo_me",     foreground="#89b4fa", font=("Helvetica", 11, "bold"))
        self.chat_area.tag_config("pseudo_other",  foreground="#a6e3a1", font=("Helvetica", 11, "bold"))
        self.chat_area.tag_config("pseudo_server", foreground="#f38ba8", font=("Helvetica", 10, "italic"))
        self.chat_area.tag_config("event_join",    foreground="#a6e3a1", font=("Helvetica", 10, "italic"))
        self.chat_area.tag_config("event_leave",   foreground="#fab387", font=("Helvetica", 10, "italic"))
        self.chat_area.tag_config("time",          foreground="#45475a", font=("Helvetica", 9))
        self.chat_area.tag_config("text",          foreground="#cdd6f4")
        self.chat_area.tag_config("divider",       foreground="#313244", font=("Helvetica", 9))

    # ── Barre d'envoi ─────────────────────────────────────────────────────
    def _build_bottom_bar(self):
        bottom = tk.Frame(self.root, bg="#181825", pady=10, padx=10)
        bottom.pack(fill="x")

        self.entry_msg = tk.Entry(
            bottom, bg="#313244", fg="#cdd6f4",
            insertbackground="#cdd6f4", font=("Helvetica", 12), relief="flat")
        self.entry_msg.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 10))
        self.entry_msg.bind("<Return>", lambda _: self._send_message())

        tk.Button(bottom, text="Envoyer", command=self._send_message,
                  bg="#89b4fa", fg="#1e1e2e", font=("Helvetica", 10, "bold"),
                  relief="flat", padx=14, pady=6, cursor="hand2"
                  ).pack(side="left")

    # ══════════════════════════════════════════════════════════════════════
    # ACTIONS TOPBAR
    # ══════════════════════════════════════════════════════════════════════
    def _do_disconnect(self):
        """Bouton Déconnexion → retour écran login."""
        if not messagebox.askyesno(
                "Déconnexion",
                "Se déconnecter et revenir à l'écran de connexion ?"):
            return
        self._disconnect(send_leave=True)
        self._exit_app = False          # On reboucle vers login, pas vers quitte
        self.root.destroy()

    def _chat_close(self):
        """Croix fenêtre chat → quitte complètement."""
        self._disconnect(send_leave=True)
        self._exit_app = True
        self.root.destroy()

    # ══════════════════════════════════════════════════════════════════════
    # PANNEAU CHANGER DE SERVEUR
    # ══════════════════════════════════════════════════════════════════════
    def _open_server_switcher(self):
        win = tk.Toplevel(self.root)
        win.title("Changer de serveur")
        win.configure(bg="#1e1e2e")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Changer de serveur", font=("Helvetica", 13, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(pady=(18, 2))
        tk.Label(win, text="Tu seras déconnecté du serveur actuel.",
                 font=("Helvetica", 9), fg="#585b70", bg="#1e1e2e").pack(pady=(0, 14))

        form = tk.Frame(win, bg="#1e1e2e", padx=24, pady=4)
        form.pack()

        sw_var = tk.StringVar(value=self.servers[0]["label"])
        e_host = self._mk_entry(form, width=20)
        e_port = self._mk_entry(form, width=8)

        def on_sw(*_):
            lbl = sw_var.get()
            srv = next((s for s in self.servers if s["label"] == lbl), None)
            if srv:
                e_host.delete(0, "end"); e_host.insert(0, srv["host"])
                e_port.delete(0, "end"); e_port.insert(0, str(srv["port"]))
            else:
                e_host.delete(0, "end"); e_port.delete(0, "end")

        sw_var.trace_add("write", on_sw)

        tk.Label(form, text="Serveur", fg="#a6adc8", bg="#1e1e2e",
                 font=("Helvetica", 10)).grid(row=0, column=0, sticky="w", pady=5)
        labels = [s["label"] for s in self.servers] + ["Autre…"]
        om = tk.OptionMenu(form, sw_var, *labels)
        om.config(bg="#313244", fg="#cdd6f4", activebackground="#45475a",
                  activeforeground="#cdd6f4", highlightthickness=0,
                  font=("Helvetica", 10), relief="flat", width=16)
        om["menu"].config(bg="#313244", fg="#cdd6f4",
                          activebackground="#45475a", activeforeground="#cdd6f4",
                          font=("Helvetica", 10))
        om.grid(row=0, column=1, padx=(10, 0), pady=5)

        tk.Label(form, text="IP",   fg="#585b70", bg="#1e1e2e",
                 font=("Helvetica", 9)).grid(row=1, column=0, sticky="w", pady=5)
        e_host.grid(row=1, column=1, padx=(10, 0))

        tk.Label(form, text="Port", fg="#585b70", bg="#1e1e2e",
                 font=("Helvetica", 9)).grid(row=2, column=0, sticky="w", pady=5)
        e_port.grid(row=2, column=1, padx=(10, 0), sticky="w")

        on_sw()

        def do_switch():
            host   = e_host.get().strip()
            port_s = e_port.get().strip()
            if not host or not port_s:
                messagebox.showerror("Erreur", "IP et port requis.", parent=win)
                return
            try:
                port = int(port_s)
            except ValueError:
                messagebox.showerror("Erreur", "Port invalide.", parent=win)
                return
            win.destroy()
            self._switch_server(host, port, sw_var.get())

        tk.Button(win, text="Se connecter", command=do_switch,
                  bg="#89b4fa", fg="#1e1e2e", font=("Helvetica", 10, "bold"),
                  relief="flat", padx=12, pady=7, cursor="hand2"
                  ).pack(pady=(18, 20))
        win.bind("<Return>", lambda _: do_switch())

    def _switch_server(self, host: str, port: int, label: str = ""):
        old_addr   = self.server_addr
        old_pseudo = self.pseudo

        # 1. Déconnexion propre de l'ancien serveur
        self._disconnect(send_leave=True)

        # 2. Connexion au nouveau
        err = self._connect_to(host, port, old_pseudo)
        if err:
            self._append_info(f"Échec connexion {host}:{port} — {err}")
            # Tentative de retour à l'ancien serveur
            self._connect_to(old_addr[0], old_addr[1], old_pseudo)
            self._start_threads()
            return

        # 3. Mémorise si nouveau
        if label == "Autre…":
            label = f"{host}:{port}"
        if not any(s["host"] == host and s["port"] == port for s in self.servers):
            self.servers.append({"label": label, "host": host, "port": port})

        # 4. Met à jour l'UI
        self.lbl_server.config(text=f"{host}:{port}")
        self._update_user_count(self.user_count)
        self._append_divider()
        self._append_info(f"Changement de serveur → {host}:{port}")

        # 5. Relance les threads
        self._start_threads()

    # ══════════════════════════════════════════════════════════════════════
    # THREADS
    # ══════════════════════════════════════════════════════════════════════
    def _start_threads(self):
        threading.Thread(target=self._receive_loop, daemon=True).start()
        threading.Thread(target=self._ping_loop,    daemon=True).start()

    def _receive_loop(self):
        while self.connected:
            try:
                data, _ = self.sock.recvfrom(BUFFER)
                msg     = json.loads(data.decode())
                mtype   = msg.get("type")

                if mtype == "message":
                    pseudo  = msg.get("pseudo", "?")
                    content = msg.get("content", "")
                    ts      = msg.get("time", "")

                    if pseudo == "Serveur":
                        if " a rejoint" in content:
                            name = content.split(" a rejoint")[0]
                            self.user_count += 1
                            self._update_user_count(self.user_count)
                            self._append_event(f"→ {name} a rejoint le chat", "event_join")
                        elif " a quitté" in content:
                            name = content.split(" a quitté")[0]
                            self.user_count = max(0, self.user_count - 1)
                            self._update_user_count(self.user_count)
                            self._append_event(f"← {name} a quitté le chat", "event_leave")
                        else:
                            self._append_event(content, "pseudo_server")
                    elif pseudo != self.pseudo:
                        self._append_message(pseudo, content, ts, is_me=False)

                elif mtype == "info":
                    content = msg.get("content", "")
                    if "count" in msg:
                        self.user_count = int(msg["count"])
                        self._update_user_count(self.user_count)
                    self._append_info(content)

                elif mtype == "pong":
                    pass

            except (json.JSONDecodeError, OSError):
                pass

    def _ping_loop(self):
        while self.connected:
            time.sleep(PING_INTERVAL)
            if self.connected and self.sock and self.server_addr:
                try:
                    self.sock.sendto(
                        json.dumps({"type": "ping"}).encode(), self.server_addr)
                except: pass

    # ══════════════════════════════════════════════════════════════════════
    # ENVOI
    # ══════════════════════════════════════════════════════════════════════
    def _send_message(self):
        content = self.entry_msg.get().strip()
        if not content:
            return
        self.entry_msg.delete(0, "end")
        if self.sock and self.server_addr:
            try:
                self.sock.sendto(
                    json.dumps({"type": "message", "content": content}).encode(),
                    self.server_addr)
            except Exception as e:
                print(f"[ERREUR] Envoi : {e}")
        now = datetime.now().strftime("%H:%M")
        self._append_message(self.pseudo, content, now, is_me=True)

    # ══════════════════════════════════════════════════════════════════════
    # AFFICHAGE
    # ══════════════════════════════════════════════════════════════════════
    def _update_user_count(self, n: int):
        try: self.lbl_users.config(text=f"👤 {n}")
        except: pass

    def _append_message(self, pseudo: str, content: str, ts: str, is_me: bool):
        try:
            self.chat_area.config(state="normal")
            tag    = "pseudo_me" if is_me else "pseudo_other"
            indent = "    " if is_me else ""
            self.chat_area.insert("end", f"{indent}{pseudo} ", tag)
            self.chat_area.insert("end", f"{ts}\n", "time")
            self.chat_area.insert("end", f"{indent}{content}\n\n", "text")
            self.chat_area.config(state="disabled")
            self.chat_area.see("end")
        except: pass

    def _append_event(self, text: str, tag: str = "pseudo_server"):
        try:
            self.chat_area.config(state="normal")
            self.chat_area.insert("end", f"  {text}\n\n", tag)
            self.chat_area.config(state="disabled")
            self.chat_area.see("end")
        except: pass

    def _append_info(self, text: str):
        try:
            self.chat_area.config(state="normal")
            self.chat_area.insert("end", f"  ── {text} ──\n\n", "pseudo_server")
            self.chat_area.config(state="disabled")
            self.chat_area.see("end")
        except: pass

    def _append_divider(self):
        try:
            self.chat_area.config(state="normal")
            self.chat_area.insert("end", "  " + "─" * 38 + "\n\n", "divider")
            self.chat_area.config(state="disabled")
            self.chat_area.see("end")
        except: pass

    # ══════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════
    def _mk_entry(self, parent, width: int = 20) -> tk.Entry:
        return tk.Entry(parent, width=width, bg="#313244", fg="#cdd6f4",
                        insertbackground="#cdd6f4", relief="flat",
                        font=("Helvetica", 11))

    def _rebuild_server_menu(self, parent: tk.Frame):
        for w in parent.winfo_children():
            w.destroy()
        labels = [s["label"] for s in self.servers] + ["Autre…"]
        om = tk.OptionMenu(parent, self.server_var, *labels)
        om.config(bg="#313244", fg="#cdd6f4", activebackground="#45475a",
                  activeforeground="#cdd6f4", highlightthickness=0,
                  font=("Helvetica", 10), relief="flat", width=14)
        om["menu"].config(bg="#313244", fg="#cdd6f4",
                          activebackground="#45475a", activeforeground="#cdd6f4",
                          font=("Helvetica", 10))
        om.pack(side="left")

    def _on_server_select(self, *_):
        label = self.server_var.get()
        srv   = next((s for s in self.servers if s["label"] == label), None)
        if srv:
            self.entry_host.delete(0, "end"); self.entry_host.insert(0, srv["host"])
            self.entry_port.delete(0, "end"); self.entry_port.insert(0, str(srv["port"]))
        elif label == "Autre…":
            self.entry_host.delete(0, "end"); self.entry_port.delete(0, "end")
            self.entry_host.focus()


if __name__ == "__main__":
    ChatClient()
