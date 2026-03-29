import sqlite3
import os

# --- ARCHITECTURE DES CHEMINS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "inventaire.db")

if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

def get_connection():
    return sqlite3.connect(DB_PATH)

def initialiser_db():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                prix TEXT,
                description TEXT,
                categorie TEXT DEFAULT 'General',
                image_path TEXT,
                date_ajout TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print(f"✅ [DB] Schema initialise : {DB_PATH}")
    except Exception as e:
        print(f"❌ [DB] Erreur initialisation : {e}")

def enregistrer_produit(nom, prix, description, categorie="General", image_path=""):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO produits (nom, prix, description, categorie, image_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (nom, prix, description, categorie, image_path))
        conn.commit()
        conn.close()
        print(f"💾 [DB] Insertion : {nom} ({prix})")
        return True
    except Exception as e:
        print(f"❌ [DB] Echec insertion : {e}")
        return False

def rechercher_produits(recherche=""):
    """Recherche par mot-clé dans nom et description."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        param = f"%{recherche}%"
        cursor.execute(
            "SELECT nom, prix, description FROM produits WHERE nom LIKE ? OR description LIKE ?",
            (param, param)
        )
        resultats = cursor.fetchall()
        conn.close()
        return resultats
    except Exception as e:
        print(f"❌ [DB] Erreur requete : {e}")
        return []

def lister_tous_produits():
    """Retourne tout le catalogue disponible (pour répondre à 'vous avez quoi ?')."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nom, prix, description FROM produits ORDER BY date_ajout DESC")
        resultats = cursor.fetchall()
        conn.close()
        return resultats
    except Exception as e:
        print(f"❌ [DB] Erreur liste produits : {e}")
        return []

# Initialisation automatique au chargement du module
initialiser_db()
