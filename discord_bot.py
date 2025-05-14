import discord
import os
import random
import string
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
KEYAUTH_SELLER_KEY = os.getenv('KEYAUTH_SELLER_KEY')
AUTHORIZED_USER_IDS_STR = os.getenv('AUTHORIZED_USER_IDS')

if not DISCORD_TOKEN or not KEYAUTH_SELLER_KEY or not AUTHORIZED_USER_IDS_STR:
    print("Erreur : Assurez-vous que DISCORD_TOKEN, KEYAUTH_SELLER_KEY et AUTHORIZED_USER_IDS sont définis dans le fichier .env")
    exit()

try:
    AUTHORIZED_USER_IDS = [int(uid.strip()) for uid in AUTHORIZED_USER_IDS_STR.split(',')]
except ValueError:
    print("Erreur : AUTHORIZED_USER_IDS dans le fichier .env n'est pas une liste valide d'IDs numériques.")
    exit()

# Configuration des intents du bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True # Nécessaire pour lire le contenu des messages

client = discord.Client(intents=intents)

def generate_random_key():
    """Génère une clé aléatoire au format XXXX-XXXX-XXXX-XXXX."""
    chars = string.ascii_uppercase + string.digits
    segments = []
    for _ in range(4):
        segment = ''.join(random.choice(chars) for _ in range(4))
        segments.append(segment)
    return "-".join(segments)

def create_keyauth_license(seller_key, license_key, expiry_days=1, level=1):
    """
    Crée une licence via l'API KeyAuth.
    NOTE : Ceci est un exemple basique. Consultez la documentation de l'API KeyAuth
    pour les paramètres exacts (expiry, level, note, etc.) et la gestion des erreurs.
    """
    # L'URL de l'API KeyAuth pour ajouter une licence.
    # Assurez-vous que c'est le bon endpoint et que les paramètres correspondent à ce que KeyAuth attend.
    # Typiquement, les paramètres sont passés dans l'URL pour les requêtes GET.
    api_url = f"https://keyauth.win/api/seller/"
    params = {
        'sellerkey': seller_key,
        'type': 'add',        # ou 'addlicense', vérifiez la documentation KeyAuth
        'key': license_key,
        'expiry': str(expiry_days), # Nombre de jours avant expiration
        'level': str(level),        # Niveau de la licence
        'format': 'json'            # Pour obtenir une réponse en JSON
        # Vous pourriez avoir besoin d'autres paramètres comme 'amount', 'mask', 'note', etc.
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP (4xx ou 5xx)
        
        data = response.json()
        if data.get("success", False):
            # Essayer de récupérer la clé réellement créée par KeyAuth depuis la réponse
            actual_created_key = data.get("key")  # Nom de champ courant
            if not actual_created_key:
                actual_created_key = data.get("license") # Autre nom de champ possible
            # Vous pourriez avoir besoin d'ajouter d'autres tentatives ici si KeyAuth utilise un autre nom de champ.
            # Exemple:
            # if not actual_created_key:
            #     actual_created_key = data.get("generated_key") # Vérifiez la documentation KeyAuth

            if actual_created_key:
                # Utiliser la clé retournée par KeyAuth
                return True, actual_created_key
            else:
                # Si KeyAuth ne retourne pas la clé dans sa réponse (ce qui serait étonnant s'il la génère et que le succès est vrai)
                # on affiche un avertissement et on retourne la clé que le bot avait initialement générée.
                # Cela signifie que la clé affichée pourrait toujours être différente de celle dans KeyAuth.
                print(f"AVERTISSEMENT: KeyAuth a confirmé la création de la clé, mais la réponse JSON ne contenait pas de champ 'key' ou 'license' attendu (ou un autre champ spécifique à KeyAuth). " +
                      f"La clé affichée ({license_key}) sera celle générée par le bot et pourrait différer de celle dans KeyAuth si KeyAuth l'a modifiée ou générée différemment. " +
                      "Veuillez IMPÉRATIVEMENT vérifier la documentation de l'API KeyAuth (ou une réponse JSON brute) pour le nom exact du champ contenant la clé créée par KeyAuth.")
                return True, license_key # Retourne la clé générée par le bot comme fallback
        else:
            error_message = data.get("message", "Erreur inconnue de KeyAuth.")
            # KeyAuth peut retourner des messages d'erreur spécifiques, par exemple si la clé existe déjà.
            if "Key already exists" in error_message:
                 return False, f"❌ Erreur KeyAuth : La clé {license_key} (celle que le bot a tenté de créer) existe déjà."
            return False, f"❌ Erreur KeyAuth : {error_message}"

    except requests.exceptions.RequestException as e:
        return False, f"❌ Erreur de communication avec l'API KeyAuth : {e}"
    except ValueError: # Erreur de décodage JSON
        return False, "❌ Erreur : Réponse invalide de l'API KeyAuth."

def get_keyauth_license_info(seller_key, license_key):
    """
    Récupère les informations d'une licence via l'API KeyAuth.
    NOTE : Consultez la documentation de l'API KeyAuth pour les paramètres exacts
    (type d'action, par exemple 'info', 'fetch', 'databykey') et la structure de la réponse.
    """
    api_url = f"https://keyauth.win/api/seller/"
    params = {
        'sellerkey': seller_key,
        'type': 'info',  # IMPORTANT: Vérifiez ce type dans la documentation KeyAuth
        'key': license_key,
        'format': 'json'
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("success", False) and "key_data" in data: # Supposons que les infos sont dans "key_data"
            return True, data["key_data"]
        elif data.get("success", False) and "info" in data: # Autre structure possible
             return True, data["info"]
        elif "message" in data:
            return False, f"❌ Erreur KeyAuth : {data.get('message', 'Erreur inconnue de KeyAuth.')}"
        else:
            return False, "❌ Erreur KeyAuth : Réponse inattendue."

    except requests.exceptions.RequestException as e:
        return False, f"❌ Erreur de communication avec l'API KeyAuth : {e}"
    except ValueError:
        return False, "❌ Erreur : Réponse invalide de l'API KeyAuth."

@client.event
async def on_ready():
    print(f'Bot connecté en tant que {client.user.name}')
    print(f'ID du bot : {client.user.id}')
    print(f'Utilisateurs autorisés (IDs) : {AUTHORIZED_USER_IDS}')
    print('------')

@client.event
async def on_message(message):
    # Ignorer les messages du bot lui-même
    if message.author == client.user:
        return

    if message.content.startswith('!genkey'):
        # Vérifier si l'utilisateur est autorisé
        if message.author.id not in AUTHORIZED_USER_IDS:
            await message.channel.send("❌ Tu n'as pas la permission d'utiliser cette commande !")
            return

        args = message.content.split()
        expiry_days_to_set = 1 # Valeur par défaut pour les jours
        level_to_set = 1 # Valeur par défaut pour le niveau

        # Analyser les jours d'expiration (premier argument optionnel)
        if len(args) > 1:
            try:
                expiry_days_to_set = int(args[1])
                if expiry_days_to_set <= 0:
                    await message.channel.send("⚠️ La durée d'expiration doit être un nombre positif de jours. Utilisation de la valeur par défaut (1 jour).")
                    expiry_days_to_set = 1
            except ValueError:
                await message.channel.send("⚠️ La durée d'expiration fournie n'est pas un nombre valide. Utilisation de la valeur par défaut (1 jour).")
                expiry_days_to_set = 1
        
        # Analyser le niveau de la licence (deuxième argument optionnel)
        if len(args) > 2:
            try:
                level_to_set = int(args[2])
                if level_to_set <= 0: # Ou toute autre validation de niveau que vous souhaitez
                    await message.channel.send("⚠️ Le niveau de licence doit être un nombre positif. Utilisation de la valeur par défaut (niveau 1).")
                    level_to_set = 1
            except ValueError:
                await message.channel.send("⚠️ Le niveau de licence fourni n'est pas un nombre valide. Utilisation de la valeur par défaut (niveau 1).")
                level_to_set = 1
        
        await message.channel.send(f"🔑 Génération d'une nouvelle clé pour {expiry_days_to_set} jour(s) au niveau {level_to_set} en cours...")

        # 1. Générer une clé aléatoire
        new_key = generate_random_key()

        # 2. Créer la licence via l'API KeyAuth
        # new_key est la clé que le bot a générée et propose à KeyAuth
        success, result_data = create_keyauth_license(
            KEYAUTH_SELLER_KEY, 
            new_key, 
            expiry_days=expiry_days_to_set, 
            level=level_to_set
        )

        if success:
            # result_data est maintenant la clé qui doit être affichée
            # (soit celle de KeyAuth, soit new_key si KeyAuth n'a pas retourné la sienne et qu'un avertissement console a été émis)
            key_to_display_on_discord = result_data
            await message.channel.send(f"🎉 Licence générée pour {expiry_days_to_set} jour(s) au niveau {level_to_set} et ajoutée à KeyAuth : `{key_to_display_on_discord}`")
        else:
            # result_data est le message d'erreur complet
            error_message_to_display = result_data
            await message.channel.send(error_message_to_display)

    elif message.content.startswith('!checkkey'):
        if message.author.id not in AUTHORIZED_USER_IDS:
            await message.channel.send("❌ Tu n'as pas la permission d'utiliser cette commande !")
            return

        args = message.content.split()
        if len(args) < 2:
            await message.channel.send("⚠️ Veuillez fournir la clé à vérifier. Usage : `!checkkey XXXX-XXXX-XXXX-XXXX`")
            return
        
        key_to_check = args[1]
        await message.channel.send(f"🔎 Vérification de la clé `{key_to_check}` en cours...")

        success, info_or_error = get_keyauth_license_info(KEYAUTH_SELLER_KEY, key_to_check)

        if success:
            # Créer un Embed pour afficher les informations de la clé
            # La structure de 'info_or_error' dépendra de la réponse de l'API KeyAuth
            # Adaptez les champs ci-dessous en conséquence
            embed = discord.Embed(title=f"Informations pour la clé : {key_to_check}", color=discord.Color.blue())
            
            # Exemples de champs (à adapter selon la réponse réelle de KeyAuth)
            if isinstance(info_or_error, dict):
                embed.add_field(name="Statut", value=info_or_error.get("status", "N/A"), inline=True)
                embed.add_field(name="Niveau", value=info_or_error.get("level", "N/A"), inline=True)
                embed.add_field(name="Expire le", value=info_or_error.get("expires", "N/A"), inline=True) # KeyAuth peut retourner un timestamp ou une date
                embed.add_field(name="Note", value=info_or_error.get("note", "N/A"), inline=False)
                embed.add_field(name="HWID", value=info_or_error.get("hwid", "N/A"), inline=True)
                embed.add_field(name="Créée le", value=info_or_error.get("createdate", "N/A"), inline=True) # KeyAuth peut retourner un timestamp
                # Ajoutez d'autres champs si nécessaire (par exemple, 'usedby', 'usedon', etc.)
            else: # Si ce n'est pas un dict, c'est une chaîne d'erreur inattendue
                 embed.description = str(info_or_error)

            await message.channel.send(embed=embed)
        else:
            await message.channel.send(info_or_error) # Affiche le message d'erreur

# Démarrer le bot
if DISCORD_TOKEN:
    client.run(DISCORD_TOKEN)
else:
    print("Le token Discord n'est pas défini. Veuillez vérifier votre fichier .env.")
