"""
vendeur.py — Réponses clients enrichies via Claude API
Utilisé uniquement si on veut des réponses IA génératives (stock trouvé).
Pour les réponses FAQ (adresse, livraison, paiement), c'est main.py qui gère.
"""
import os
import sys
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(BASE_DIR, ".."))
sys.path.append(ROOT_DIR)

from data.database import rechercher_produits

load_dotenv(os.path.join(ROOT_DIR, ".env"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"


def repondre_au_client_ia(message_client, produits):
    """
    Génère une réponse commerciale avec l'IA Claude à partir des produits trouvés.
    Appelé uniquement quand des produits sont en stock.
    """
    if not ANTHROPIC_API_KEY:
        # Fallback sans IA si pas de clé
        reponse = "🔥 J'ai trouvé ça pour vous :\n\n"
        for p in produits:
            reponse += f"🛍️ *{p[0]}* — {p[1]}\n📝 {p[2]}\n\n"
        return reponse + "Ça vous intéresse ? 😊"

    stock_info = "\n".join([f"- {p[0]} à {p[1]} : {p[2]}" for p in produits])

    prompt = f"""Tu es un vendeur chaleureux dans une boutique de mode à Lubumbashi, en RDC.
Voici les articles disponibles en stock :
{stock_info}

Le client demande : '{message_client}'

Réponds en français, style WhatsApp : chaleureux, émojis, donne les prix, invite à passer commande.
Réponse courte (max 5 lignes)."""

    try:
        response = requests.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": MODEL,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=15
        )
        if response.status_code == 200:
            return response.json()['content'][0]['text']
    except Exception as e:
        print(f"⚠️ Erreur IA vendeur : {e}")

    # Fallback si l'IA échoue
    reponse = "🔥 J'ai trouvé :\n\n"
    for p in produits:
        reponse += f"🛍️ *{p[0]}* — {p[1]}\n"
    return reponse + "\nÇa vous intéresse ? Tapez COMMANDE ! 😊"


if __name__ == "__main__":
    produits = rechercher_produits("veste")
    if produits:
        print(repondre_au_client_ia("Vous avez des vestes ?", produits))
    else:
        print("Aucun produit en stock pour le test.")
