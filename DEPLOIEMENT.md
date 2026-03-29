# 🚀 Guide de Déploiement — Lshi-IA-Vendeur sur Railway

## Architecture finale

```
Clients WhatsApp
       │  messages
       ▼
[Ton PC Windows]
whatsapp_bridge/index.js  ──── HTTP POST ────►  [Railway Cloud]
       │                                         api/main.py  (Flask)
       │  réponse                                data/inventaire.db
       ◄────────────────────────────────────────
```

Le bot tourne 24h/24 sur Railway (gratuit).
Le pont WhatsApp tourne sur ton PC quand il est allumé.
(Plus tard, on migre aussi le pont sur un VPS à 5$/mois.)

---

## ÉTAPE 1 — Créer un compte Railway (5 min)

1. Va sur https://railway.app
2. Clique **"Start a New Project"**
3. Connecte-toi avec **GitHub** (crée un compte GitHub si besoin)
4. Railway te donne **500h gratuites/mois** — c'est suffisant pour démarrer

---

## ÉTAPE 2 — Mettre le code sur GitHub (10 min)

### Sur ton PC, ouvre un terminal (PowerShell ou CMD) :

```bash
# Installe Git si pas déjà fait : https://git-scm.com/download/win

# Va dans ton dossier projet
cd D:\Lshi-IA-Vendeur

# Copie les nouveaux fichiers de déploiement dans ton projet
# (les fichiers de ce zip : Procfile, railway.json, requirements.txt, .gitignore, .env.example)

# Initialise Git
git init
git add .
git commit -m "Initial commit — Lshi-IA-Vendeur production ready"

# Crée un repo sur GitHub : https://github.com/new
# Nom : lshi-ia-vendeur  (privé !)
# Puis relie et pousse :
git remote add origin https://github.com/TON_USERNAME/lshi-ia-vendeur.git
git branch -M main
git push -u origin main
```

> ⚠️ Le repo doit être **PRIVÉ** — il contient la logique de ton produit.

---

## ÉTAPE 3 — Déployer sur Railway (5 min)

1. Sur railway.app, clique **"New Project"**
2. Choisis **"Deploy from GitHub repo"**
3. Sélectionne ton repo `lshi-ia-vendeur`
4. Railway détecte Python automatiquement et lance le build

### Ajouter les variables d'environnement :

Dans Railway → ton projet → **"Variables"** → ajoute :

| Variable | Valeur |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (ta clé sur console.anthropic.com) |
| `BOUTIQUE_NOM` | `Lshi-IA-Vendeur` (ou nom de la boutique cliente) |
| `BOUTIQUE_ADRESSE` | `Centre-Ville de Lubumbashi, avenue de la Libération` |
| `BOUTIQUE_HORAIRES` | `Lundi-Samedi 8h30-17h30` |

> ✅ Railway redémarre automatiquement après chaque changement de variable.

---

## ÉTAPE 4 — Obtenir ton URL publique

Dans Railway → ton projet → **"Settings"** → **"Domains"**
→ Clique **"Generate Domain"**
→ Tu obtiens quelque chose comme :
  `https://lshi-ia-vendeur-production.up.railway.app`

**Teste immédiatement :**
```
https://TON_APP.up.railway.app/health
```
Tu dois voir : `{"status": "online", "service": "Lshi-IA-Vendeur"}`

---

## ÉTAPE 5 — Connecter le pont WhatsApp (sur ton PC)

### Dans le dossier `whatsapp_bridge/` :

1. Copie `.env.example` en `.env`
2. Ouvre `.env` et remplace l'URL :
   ```
   FLASK_URL=https://lshi-ia-vendeur-production.up.railway.app
   ```

3. Installe les dépendances Node (une seule fois) :
   ```bash
   cd D:\Lshi-IA-Vendeur\whatsapp_bridge
   npm install
   ```

4. Lance le pont :
   ```bash
   node index.js
   ```

5. Un QR code apparaît dans le terminal.
   **Scanne-le avec WhatsApp** sur ton téléphone :
   - WhatsApp → Appareils liés → Lier un appareil → Scanner

6. Tu vois : `✅ WhatsApp CONNECTÉ !`

---

## ÉTAPE 6 — Tester end-to-end

Depuis un autre téléphone, envoie un message WhatsApp au numéro lié :
- `Salut` → doit répondre avec le message d'accueil
- `Vous avez quoi ?` → doit lister le catalogue (vide au début)
- `Votre adresse ?` → doit donner l'adresse de la boutique
- `Livraison ?` → doit expliquer la livraison

---

## ÉTAPE 7 — Ajouter le premier article (test patron)

1. Prends une photo d'un vêtement
2. Envoie-la sur WhatsApp avec le texte : `*1234* belle veste noire 45$`
3. Le bot analyse l'image, enregistre en base et publie le statut

---

## Commandes utiles

### Voir les logs Railway en temps réel :
Railway → ton projet → **"Logs"**

### Redémarrer le service Railway :
Railway → ton projet → **"..."** → **"Restart"**

### Mettre à jour le code :
```bash
git add .
git commit -m "mise à jour"
git push
# Railway redéploie automatiquement en ~1 minute
```

---

## Coûts

| Service | Plan | Coût |
|---|---|---|
| Railway (bot Flask) | Free tier | 0 $ / mois |
| Anthropic Claude Haiku | Pay-as-you-go | ~1-3 $ / mois (usage normal) |
| GitHub | Free | 0 $ |
| **TOTAL** | | **~1-3 $ / mois** |

Quand tu as des revenus (premier client payant), migre vers Railway Starter à 5$/mois pour enlever la limite des 500h.

---

## Prochaine étape après déploiement

→ Revenir sur Claude et demander : **"Génère le script de vente pour le premier gérant"**
