/**
 * Lshi-IA-Vendeur — Pont WhatsApp (Node.js)
 * Tourne sur ton PC Windows en local.
 * Relaie les messages vers ton bot hébergé sur Railway.
 *
 * CONFIGURATION :
 * Créer un fichier .env dans ce dossier avec :
 * FLASK_URL=https://TON_APP.up.railway.app
 */

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode  = require('qrcode-terminal');
const axios   = require('axios');
const express = require('express');
require('dotenv').config();

// --- AJOUT : FONCTION DE DÉLAI ---
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// ─── URL DU BOT ───────────────────────────────────────────
const FLASK_URL = process.env.FLASK_URL || 'http://127.0.0.1:5000';
console.log(`🔗 Bot connecté sur : ${FLASK_URL}`);
// ──────────────────────────────────────────────────────────

const app = express();
app.use(express.json({ limit: '60mb' }));

const client = new Client({
    authStrategy: new LocalAuth(),
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
    },
    puppeteer: {
        handleSIGINT: false,
        protocolTimeout: 120000,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    }
});

// ─── ROUTE : Publier un statut WhatsApp ──────────────────
app.post('/post-status', async (req, res) => {
    try {
        let { imageBase64, caption } = req.body;
        if (imageBase64.includes('base64,')) {
            imageBase64 = imageBase64.split('base64,')[1];
        }
        imageBase64 = imageBase64.replace(/\s/g, '');
        const media = new MessageMedia('image/jpeg', imageBase64);
        await client.sendMessage('status@broadcast', media, { caption });
        console.log('📢 Statut WhatsApp publié !');
        res.json({ success: true });
    } catch (error) {
        console.error('❌ Erreur statut :', error.message);
        res.status(500).json({ error: error.message });
    }
});

// ─── ÉVÉNEMENTS WHATSAPP ─────────────────────────────────

client.on('qr', qr => {
    console.log('\n📱 Scanne ce QR code avec WhatsApp sur ton téléphone :\n');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('✅ WhatsApp CONNECTÉ !');
    app.listen(3000, () => console.log('🔌 Pont actif sur port 3000'));
});

client.on('disconnected', (reason) => {
    console.log('⚠️ WhatsApp déconnecté :', reason);
    console.log('♻️  Reconnexion dans 5s...');
    setTimeout(() => client.initialize(), 5000);
});

client.on('message', async (msg) => {
    // Ignorer les groupes et broadcasts
    if (msg.from.includes('@broadcast') || msg.from.includes('@g.us')) return;

    try {
        let mediaData = null;

        // --- MODIFICATION : ATTENTE DU TÉLÉCHARGEMENT ---
        if (msg.hasMedia && msg.type === 'image') {
            console.log("⏳ Image détectée, préparation du téléchargement...");
            await sleep(2000); // Laisse 2 secondes à WhatsApp pour charger le binaire
            const media = await msg.downloadMedia();
            if (media) {
                mediaData = media.data; // base64
                console.log("📸 Image prête !");
            }
        }

        // Envoyer au bot Railway (Timeout augmenté à 60s pour l'analyse IA)
        const response = await axios.post(`${FLASK_URL}/whatsapp`, {
            text:   msg.body || '',
            sender: msg.from,
            image:  mediaData   // null si pas d'image
        }, { timeout: 60000 });

        if (response.data && response.data.reply) {
            await client.sendMessage(msg.from, response.data.reply);
        }

    } catch (e) {
        console.log('⚠️ Erreur message :', e.message);
    }
});

// ─── PROTECTION ANTI-CRASH ───────────────────────────────
process.on('uncaughtException', (err) => {
    console.log('🛡️ Erreur interceptée (service maintenu) :', err.message);
});

client.initialize();