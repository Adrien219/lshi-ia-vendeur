import os
import sys
import base64
import json
import time
import re
import requests
from io import BytesIO
from dotenv import load_dotenv
from PIL import Image

# --- CONFIGURATION DES CHEMINS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(BASE_DIR, ".."))
sys.path.append(ROOT_DIR)

from data.database import enregistrer_produit

load_dotenv(os.path.join(ROOT_DIR, ".env"))

# ========================================================
# CONFIGURATION API
# On utilise l'API Claude (Anthropic) à la place de Gemini.
# Pourquoi ? Quota Gemini Free Tier épuisé, et Claude supporte
# la vision (analyse d'image) avec un tarif très compétitif.
# Clé à mettre dans .env : ANTHROPIC_API_KEY=sk-ant-...
# ========================================================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"  # Rapide et économique, supporte la vision


def compresser_image_b64(chemin_image):
    """Réduit le poids de l'image pour optimiser les tokens API."""
    try:
        with Image.open(chemin_image) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((1024, 1024))
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=75)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"⚠️ Erreur compression: {e}")
        with open(chemin_image, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')


def publier_statut_whatsapp(chemin_image, nom, prix):
    """Envoi vers le pont Node.js WhatsApp Bridge."""
    try:
        with open(chemin_image, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')

        legende = f"🔥 NOUVEL ARRIVAGE !\n\n🛍️ {nom}\n💰 {prix}\n\n📍 Dispo à Lubumbashi ! 🚀"

        requests.post("http://127.0.0.1:3000/post-status", json={
            "imageBase64": img_b64,
            "caption": legende
        }, timeout=30)
        print("📢 Statut WhatsApp publié.")
    except Exception as e:
        print(f"❌ Erreur Statut : {e}")


def analyser_image_claude(image_data, message_patron):
    """
    Appelle l'API Claude Vision pour analyser un vêtement.
    Remplace l'ancien appel Gemini qui tombait en 429.
    """
    if not ANTHROPIC_API_KEY:
        return None, "❌ ANTHROPIC_API_KEY manquante dans le fichier .env"

    prompt = (
        f"Tu es un vendeur expert à Lubumbashi. Le patron dit : '{message_patron}'. "
        "Analyse l'image de ce vêtement et renvoie EXCLUSIVEMENT un JSON valide comme ceci : "
        '{"NOM": "Nom court du vêtement", "PRIX": "Prix en USD", "DESC": "Description courte et commerciale"} '
        "Exemple : {\"NOM\": \"Veste en cuir noire\", \"PRIX\": \"90$\", \"DESC\": \"Veste slim fit, taille M, cuir synthétique premium\"}"
    )

    payload = {
        "model": MODEL,
        "max_tokens": 256,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data
                    }
                },
                {"type": "text", "text": prompt}
            ]
        }]
    }

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    for tentative in range(3):
        try:
            response = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=30)

            if response.status_code == 429:
                attente = (tentative + 1) * 10
                print(f"⏳ Rate limit. Attente {attente}s...")
                time.sleep(attente)
                continue

            if response.status_code != 200:
                return None, f"❌ Erreur API Claude {response.status_code}: {response.text}"

            res_json = response.json()
            texte_raw = res_json['content'][0]['text']

            # Extraction JSON robuste par regex
            match = re.search(r'\{.*?\}', texte_raw, re.DOTALL)
            if not match:
                return None, f"❌ L'IA n'a pas renvoyé un JSON valide. Réponse: {texte_raw}"

            data = json.loads(match.group())
            return data, None

        except Exception as e:
            return None, f"❌ Erreur critique : {str(e)}"

    return None, "❌ Trop de tentatives échouées. Réessayez dans quelques minutes."


def traiter_nouvel_arrivage(chemin_image, message_patron):
    """Pipeline L4 : Compression → Vision IA → DB → Publication WhatsApp."""
    try:
        if not os.path.exists(chemin_image):
            return "❌ Image introuvable."

        print(f"🔍 Analyse en cours : {os.path.basename(chemin_image)}")

        # 1. Compression image
        image_data = compresser_image_b64(chemin_image)

        # 2. Analyse Claude Vision
        data, erreur = analyser_image_claude(image_data, message_patron)
        if erreur:
            return erreur

        nom = data.get('NOM', 'Article')
        prix = data.get('PRIX', 'À discuter')
        desc = data.get('DESC', 'Disponible.')

        print(f"📦 Produit détecté : {nom} — {prix}")

        # 3. Enregistrement DB
        if not enregistrer_produit(nom=nom, prix=prix, description=desc, image_path=chemin_image):
            return "❌ Erreur enregistrement en base de données."

        # 4. Publication statut WhatsApp
        publier_statut_whatsapp(chemin_image, nom, prix)

        return f"✅ *{nom}* ({prix}) ajouté au stock et publié sur WhatsApp !"

    except Exception as e:
        return f"❌ Erreur pipeline : {str(e)}"


if __name__ == "__main__":
    img_test = os.path.join(ROOT_DIR, "tests", "article.jpg")
    print(f"🚀 Test sur : {img_test}")
    print(traiter_nouvel_arrivage(img_test, "*1234* Belle veste noire 90$"))
