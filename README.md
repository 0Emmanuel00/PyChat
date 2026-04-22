# 💬 PyChat

**PyChat** est une application de chat en réseau local basée sur UDP, développée en Python avec une interface graphique moderne utilisant Tkinter.

---

## 🚀 Fonctionnalités

* 💬 Chat en temps réel (multi-utilisateurs)
* 🖥️ Interface graphique intuitive (Tkinter)
* 🔌 Connexion à plusieurs serveurs
* 🔄 Changement de serveur à chaud
* 👥 Affichage du nombre d’utilisateurs connectés
* 🔔 Notifications (connexion / déconnexion)
* ❤️ Système de ping pour maintenir la connexion
* ⚡ Communication rapide via UDP

---

## 🏗️ Architecture

* **Client (`client.py`)**

  * Interface graphique
  * Gestion des messages
  * Connexion au serveur

* **Serveur (`server.py`)**

  * Gestion des clients
  * Diffusion des messages (broadcast)
  * Gestion des connexions/déconnexions

---

## 📡 Fonctionnement

1. Le client envoie une requête `join` au serveur
2. Le serveur enregistre l’utilisateur
3. Les messages sont envoyés en UDP
4. Le serveur redistribue à tous les clients connectés
5. Un système de `ping/pong` maintient la connexion active

---

## 🛠️ Installation

### 1. Cloner le projet

```bash
git clone https://github.com/ton-username/pychat.git
cd pychat
```

### 2. Lancer le serveur

```bash
python server.py
```

⚠️ Pense à modifier l’IP dans `server.py` :

```python
HOST = "192.168.X.X"
```

---

### 3. Lancer le client

```bash
python client.py
```

---

## ⚙️ Configuration

### Serveur

Dans `server.py` :

* `HOST` → adresse IP locale
* `PORT` → port utilisé (par défaut 5555)

### Client

Dans `client.py` :

* Liste des serveurs modifiable (`DEFAULT_SERVERS`)
* Ajout dynamique de serveurs possible depuis l’interface

---

## 📁 Structure du projet

```
pychat/
│── client.py
│── server.py
│── version.py
│── README.md
```

---

## 🧠 Technologies utilisées

* Python 3
* Socket (UDP)
* Threading
* Tkinter (GUI)
* JSON (échange de données)

---

## ⚠️ Limitations

* Communication en UDP (pas de garantie de livraison)
* Pas de chiffrement
* Pas de gestion avancée des erreurs réseau

---

## 🔮 Améliorations possibles

* 🔐 Chiffrement des messages
* 🌐 Support Internet (hors LAN)
* 📁 Envoi de fichiers
* 🧑‍💻 Authentification utilisateurs
* 💾 Historique des messages
* 🎨 Amélioration UI/UX

---

## 👨‍💻 Auteur

Projet développé par **Emmanuel Haron**

---

## 📄 Licence

Ce projet est open-source. Tu peux le modifier et l’améliorer librement.

---

## ⭐ Support

Si le projet te plaît, n’hésite pas à mettre une étoile ⭐ sur GitHub !
