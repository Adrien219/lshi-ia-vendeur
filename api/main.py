import os
import sys
import unicodedata
from flask import Flask, request, jsonify
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(BASE_DIR, ".."))
sys.path.append(ROOT_DIR)

from data.database import rechercher_produits, lister_tous_produits
from core.ai_engine import traiter_nouvel_arrivage

load_dotenv(os.path.join(ROOT_DIR, ".env"))

app = Flask(__name__)
# Augmentation de la taille max pour recevoir les images en Base64
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024 

BOUTIQUE_NOM      = os.getenv("BOUTIQUE_NOM", "Lshi-IA-Vendeur")
BOUTIQUE_ADRESSE  = os.getenv("BOUTIQUE_ADRESSE", "Centre-Ville de Lubumbashi, avenue de la Libération")
BOUTIQUE_HORAIRES = os.getenv("BOUTIQUE_HORAIRES", "Lundi-Samedi 8h30-17h30")

def normaliser(texte):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texte.lower())
        if unicodedata.category(c) != 'Mn'
    )

def est_code_patron(message):
    return message.strip().startswith('*1234*')

def filtrer_reponse_metier(msg_norm):
    if any(m in msg_norm for m in ["ou", "adresse", "situe", "emplacement", "quartier", "avenue", "localisation"]):
        return f"📍 Nous sommes situés au {BOUTIQUE_ADRESSE}. Passez nous voir ! 😊"
    if any(m in msg_norm for m in ["heure", "ouvert", "ferme", "quand", "dimanche", "weekend", "horaire"]):
        return f"🕒 Nos horaires : *{BOUTIQUE_HORAIRES}*. ✨"
    if any(m in msg_norm for m in ["livr", "expedition", "envoyer", "colis", "transport"]):
        return (
            "🚚 Oui, nous livrons partout à Lubumbashi ! 📦\n\n"
            "Pour Kolwezi, Likasi, Kinshasa : agences de transport sécurisées.\n"
            "⏱️ Délai : *24h à 48h* pour Lubumbashi."
        )
    if any(m in msg_norm for m in ["combien de temps", "delai", "duree", "rapidement"]):
        return "⏱️ *24h à 48h* pour Lubumbashi. 2 à 5 jours pour les autres villes. 🚀"
    if any(m in msg_norm for m in ["payer", "payement", "paiement", "monnaie", "mpesa", "airtel", "cash", "dollar", "franc"]):
        return (
            "💳 Modes de paiement acceptés :\n\n"
            "✅ Cash (USD ou CDF)\n"
            "✅ M-Pesa / Orange Money / Airtel Money\n"
            "✅ Virement bancaire\n\n"
            "Paiement avant ou à la livraison. 🔐"
        )
    if any(m in msg_norm for m in ["numero", "appeler", "contact", "telephone", "gerant"]):
        return "📞 Envoyez votre demande ici, je transmets au gérant directement ! 😊"
    return None

def generer_reponse_vendeur(message_client):
    msg_norm = normaliser(message_client)

    if msg_norm.strip() in ["salut", "bonjour", "bonsoir", "mambo", "habari", "yo", "hello", "coucou", "hi"]:
        return (
            f"Salut ! 👋 Bienvenue chez *{BOUTIQUE_NOM}*. Je suis votre assistant virtuel.\n\n"
            "Vous cherchez un article (veste, chemise, chaussure...) ?\n"
            "Tapez le nom ou posez votre question ! 😊"
        )

    reponse_auto = filtrer_reponse_metier(msg_norm)
    if reponse_auto:
        return reponse_auto

    if any(m in msg_norm for m in ["commande", "acheter", "achat", "je veux", "reserver"]):
        return (
            "🛒 Pour passer commande :\n\n"
            "1️⃣ Dites-moi le nom de l'article voulu.\n"
            "2️⃣ Je vérifie dispo et prix.\n"
            "3️⃣ On confirme la livraison ! 🚀"
        )

    if any(m in msg_norm for m in ["interesse", "ca me plait", "j'aime"]):
        return "Super ! 🎉 Précisez l'article et je vérifie la dispo. Ou tapez *CATALOGUE* ! 😊"

    if any(m in msg_norm for m in ["catalogue", "vous avez quoi", "vous vendez quoi",
                                    "votre stock", "liste", "disponible", "quel article", "quoi comme"]) \
            or msg_norm.strip() == "catalogue":
        tous = lister_tous_produits()
        if tous:
            rep = "🛍️ *Notre stock disponible :*\n\n"
            for p in tous:
                rep += f"• *{p[0]}* — {p[1]}\n"
            rep += "\nQuel article vous intéresse ? 😊"
            return rep
        return "Notre catalogue se met à jour ! 🔄 Restez branché sur nos statuts WhatsApp. ✨"

    if len(msg_norm) > 2:
        resultats = rechercher_produits(message_client)
        if resultats:
            rep = "🔥 *J'ai trouvé ça pour vous :*\n\n"
            for r in resultats:
                rep += f"🛍️ *{r[0]}*\n💰 Prix : {r[1]}\n📝 {r[2]}\n\n"
            rep += "Ça vous intéresse ? Tapez *COMMANDE* ! 😊"
            return rep

    return (
        "Désolé, je n'ai pas trouvé cet article. 😔\n\n"
        "💡 Essayez :\n"
        "• Taper *CATALOGUE* pour voir tous nos articles\n"
        "• Chercher par catégorie : veste, chemise, chaussure...\n"
        "• Ou posez une autre question ! ✨"
    )

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data"}), 400

        message_client = data.get('text', '').strip()
        sender         = data.get('sender', 'Client')
        # MODIFICATION : On récupère 'image' qui contient le Base64
        image_data     = data.get('image', None) 

        print(f"📩 {sender} : {message_client}")

        if est_code_patron(message_client):
            print(f"🔑 Code patron — {sender}")
            # MODIFICATION : On vérifie si image_data existe (plus besoin de os.path.exists)
            if image_data: 
                # Ton ai_engine doit être prêt à recevoir le Base64
                reponse = traiter_nouvel_arrivage(image_data, message_client)
            else:
                reponse = (
                    "✅ Code patron reçu !\n\n"
                    "⚠️ Envoyez l'IMAGE avec le code pour ajouter un article.\n"
                    "Format : *1234* [description] [prix]"
                )
            return jsonify({"status": "success", "reply": reponse})

        reponse = generer_reponse_vendeur(message_client)
        print(f"🤖 → {reponse[:80]}...")
        return jsonify({"status": "success", "reply": reponse})

    except Exception as e:
        print(f"❌ Erreur : {e}")
        return jsonify({"reply": "Petit souci technique, je reviens ! 🛠️"}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online", "service": BOUTIQUE_NOM}), 200


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": BOUTIQUE_NOM,
        "status": "running",
        "endpoints": ["/whatsapp (POST)", "/health (GET)"]
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"🌍 {BOUTIQUE_NOM} actif sur port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)