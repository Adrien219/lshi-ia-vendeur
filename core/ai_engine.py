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
import google.generativeai as genai

# --- CONFIGURATION DES CHEMINS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(BASE_DIR, ".."))
sys.path.append(ROOT_DIR)

from data.database import enregistrer_produit

load_dotenv(os.path.join(ROOT_DIR, ".env"))

# ========================================================
# CONFIGURATION GEMINI
# ========================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
# Utilisation de Flash pour la rapidité et les quotas généreux
model = genai.GenerativeModel('gemini-1.5-flash')

def preparer_image_pour_gemini(image_input):
    """Compresse et convertit l'entrée (chemin ou b64) pour Gemini."""
    try:
        if isinstance(image_input, str) and os.path.exists(image_input):
            img = Image.open(image_input)
        else:
            img_data = base64.b64decode(image_input)
            img = Image.open(BytesIO(img_data))

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        img.thumbnail((1024, 1024))
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=70) # Qualité 70 pour alléger le payload
        return buffer.getvalue()
    except Exception as e:
        print(f"⚠️ Erreur image: {e}")
        return None

def analyser_image_gemini(img_bytes, message_patron):
    """Appel à l'API Gemini avec gestion du Rate Limit."""
    if not GEMINI_API_KEY:
        return None, "❌ Clé API Gemini manquante."

    prompt = (
        f"Tu es un vendeur expert à Lubumbashi. Le patron envoie cette photo avec le message : '{message_patron}'. "
        "Analyse le vêtement et réponds UNIQUEMENT avec ce JSON : "
        '{"NOM": "Nom court", "PRIX": "Prix", "DESC": "Description commerciale courte"}'
    )

    # Préparation du contenu pour Gemini
    image_part = {"mime_type": "image/jpeg", "data": img_bytes}

    for tentative in range(3):
        try:
            response = model.generate_content([prompt, image_part])
            
            # Extraction du JSON dans la réponse
            match = re.search(r'\{.*?\}', response.text, re.DOTALL)
            if match:
                return json.loads(match.group()), None
            return None, "❌ Format JSON non trouvé dans la réponse IA."

        except Exception as e:
            if "429" in str(e):
                attente = (tentative + 1) * 5
                print(f"⏳ Rate limit Gemini. Attente {attente}s...")
                time.sleep(attente)
                continue
            return None, f"❌ Erreur Gemini : {str(e)}"
    
    return None, "❌ Trop de tentatives (Quota dépassé)."

def traiter_nouvel_arrivage(image_source, message_patron):
    """Pipeline : Réception -> Gemini -> DB."""
    try:
        # 1. Préparation Image
        img_bytes = preparer_image_pour_gemini(image_source)
        if not img_bytes:
            return "❌ Erreur de traitement de l'image."

        # 2. Analyse Gemini
        data, erreur = analyser_image_gemini(img_bytes, message_patron)
        if erreur:
            return erreur

        nom = data.get('NOM', 'Article')
        prix = data.get('PRIX', 'À discuter')
        desc = data.get('DESC', 'Disponible.')

        # 3. Sauvegarde DB
        # On utilise une constante pour le chemin sur Railway
        success = enregistrer_produit(nom=nom, prix=prix, description=desc, image_path="RAILWAY_STORAGE")
        
        if success:
            return f"✅ *{nom}* ({prix}) ajouté à l'inventaire Lshi-IA ! 🧥"
        return "❌ Erreur lors de l'enregistrement en base de données."

    except Exception as e:
        return f"❌ Erreur pipeline : {str(e)}"