from dotenv import load_dotenv
import openai
from notion_client import Client
import re
import time
import os

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer les clés API depuis les variables d'environnement
openai_api_key = os.getenv('OPENAI_API_KEY')
notion_api_key = os.getenv('NOTION_API_KEY')

# Vérifier que les clés ont été chargées
if not openai_api_key:
    raise ValueError("La clé API OpenAI n'est pas définie. Vérifiez le fichier .env.")
if not notion_api_key:
    raise ValueError("La clé API Notion n'est pas définie. Vérifiez le fichier .env.")

# Initialiser les clients avec les clés API
openai.api_key = openai_api_key
notion = Client(auth=notion_api_key)

# ID de la page racine de Notion du référentiel
root_page_id = "13ff3a2d6882809bbaf4da8d6a7ae15a"

# Fonction pour supprimer les styles Markdown (gras, italique, barré, souligné)
def remove_markdown_styles(line):
    # Supprimer les délimiteurs Markdown pour gras, italique, barré, et souligné
    pattern = r'(\*\*\*\*|\*\*\*|\*\*|\*|~~|_)(.*?)\1'
    
    # Remplacer les délimiteurs trouvés par le texte brut (2e groupe du regex)
    clean_line = re.sub(pattern, r'\2', line)
    
    return clean_line

def split_text_into_blocks(text, max_length=2000):
    # Diviser le texte par lignes
    lines = text.splitlines(keepends=True)  # Conserver les sauts de ligne
    blocks = []
    current_block = ""

    for line in lines:
        # Si l'ajout de cette ligne dépasse la limite, on crée un nouveau bloc
        if len(current_block) + len(line) > max_length:
            blocks.append(current_block)  # Ajouter le bloc courant
            current_block = line  # Commencer un nouveau bloc avec la ligne courante
        else:
            current_block += line  # Ajouter la ligne au bloc courant
    
    # Ajouter le dernier bloc restant
    if current_block:
        blocks.append(current_block)
    
    return blocks

# Fonction pour convertir le Markdown en annotations Notion
def convert_markdown_to_notion_blocks(markdown_text, page_title):
    notion_blocks = []
    lines = markdown_text.splitlines()

    is_code_block = False
    code_buffer = []
    code_language = ""
    # Liste des langages supportés par Notion
    accepted_languages = [
        "abap", "agda", "arduino", "assembly", "bash", "basic", "bnf", "c", "c#", "c++", 
        "clojure", "coffeescript", "coq", "css", "dart", "dhall", "diff", "docker", "ebnf", 
        "elixir", "elm", "erlang", "f#", "flow", "fortran", "gherkin", "glsl", "go", "graphql", 
        "groovy", "haskell", "html", "idris", "java", "javascript", "json", "julia", "kotlin", 
        "latex", "less", "lisp", "livescript", "llvm ir", "lua", "makefile", "markdown", 
        "markup", "matlab", "mathematica", "mermaid", "nix", "notion formula", "objective-c", 
        "ocaml", "pascal", "perl", "php", "plain text", "powershell", "prolog", "protobuf", 
        "purescript", "python", "r", "racket", "reason", "ruby", "rust", "sass", "scala", 
        "scheme", "scss", "shell", "solidity", "sql", "swift", "toml", "typescript", "vb.net", 
        "verilog", "vhdl", "visual basic", "webassembly", "xml", "yaml", "java/c/c++/c#"
    ]

    for line in lines:
        line = line.rstrip()

        # Détecter le début d'un bloc de code multiligne
        if line.startswith('```') and not is_code_block:
            is_code_block = True
            code_language = line[3:].strip()  # Extraire le langage après ```
            code_buffer = []  # Réinitialiser le buffer de code
            continue

        # Détecter le début d'un bloc de code multiligne indenté pour une liste numérotée
        if line.startswith('   ```') and not is_code_block:
            is_code_block = True
            code_language = line[6:].strip()  # Extraire le langage après ```
            code_buffer = []  # Réinitialiser le buffer de code
            continue

        # Détecter le début d'un bloc de code multiligne indenté pour une liste à puce
        if line.startswith('  ```') and not is_code_block:
            is_code_block = True
            code_language = line[5:].strip()  # Extraire le langage après ```
            code_buffer = []  # Réinitialiser le buffer de code
            continue

        # Détecter la fin d'un bloc de code multiligne
        if line.startswith('```') and is_code_block:
            is_code_block = False
            # Découper le code en blocs de 2000 caractères
            code_blocks = split_text_into_blocks("\n".join(code_buffer))
            # Créer un bloc de code dans Notion en préservant les indentations
            for block in code_blocks:
                language_to_use = code_language if code_language in accepted_languages else "plain text"
                notion_blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": block}
                            }
                        ],
                        "language": language_to_use
                    }
                })
            code_buffer = []
            continue

        # Détecter la fin d'un bloc de code multiligne indenté  pour une liste numérotée
        if line.startswith('   ```') and is_code_block:
            is_code_block = False
            # Découper le code en blocs de 2000 caractères
            code_blocks = split_text_into_blocks("\n".join(code_buffer))
            # Créer un bloc de code dans Notion en préservant les indentations
            for block in code_blocks:
                language_to_use = code_language if code_language in accepted_languages else "plain text"
                notion_blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": block}
                            }
                        ],
                        "language": language_to_use
                    }
                })
            code_buffer = []
            continue

        # Détecter la fin d'un bloc de code multiligne indenté  pour une liste à puce
        if line.startswith('  ```') and is_code_block:
            is_code_block = False
            # Découper le code en blocs de 2000 caractères
            code_blocks = split_text_into_blocks("\n".join(code_buffer))
            # Créer un bloc de code dans Notion en préservant les indentations
            for block in code_blocks:
                language_to_use = code_language if code_language in accepted_languages else "plain text"
                notion_blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": block}
                            }
                        ],
                        "language": language_to_use
                    }
                })
            code_buffer = []
            continue
        
        # Si on est dans un bloc de code, accumuler les lignes de code (sans strip pour préserver l'indentation)
        if is_code_block:
            code_buffer.append(line)
            continue

        # Ignorer les lignes vides
        if len(line) == 0:
            continue
        
        # Si ce n'est pas un bloc de code, gérer normalement les autres types de lignes (titres, listes, etc.)
        # Nettoyage des styles Markdown avant traitement
        line = remove_markdown_styles(line)
        
        # 1. Gérer les séparateurs (--- ou ***)
        if line in ['---', '***']:
            notion_blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            continue

        # 2. Gérer les titres (#, ##, ###) avec formatage et code inline
        if line.startswith('#'):
            level = min(line.count('#'), 3)  # Limiter le niveau au maximum supporté par Notion (heading_3)

            plain_text = re.sub(r'^[#\s]+', '', line).strip()  # Supprimer tous les # et les espaces avant le texte

            # Ignorer le titre s'il correspond au titre de la page
            if plain_text.lower() == page_title.lower():
                continue

            rich_text = []
            # Diviser la ligne en parties par les backticks pour détecter le code inline
            parts = plain_text.split('`')
            
            for i, part in enumerate(parts):
                    if i % 2 == 0:
                        # Texte normal
                        rich_text.append({
                            "type": "text",
                            "text": {"content": part},
                            "annotations": {"bold": False, "italic": False}
                        })
                    else:
                        # Code inline
                        rich_text.append({
                            "type": "text",
                            "text": {"content": part},
                            "annotations": {"code": True}
                        })

            notion_blocks.append({
                "object": "block",
                f"heading_{level}": {"rich_text": rich_text}
            })
            continue
        
        # 3. Gérer les blocs de citation
        if line.startswith('> '):
            notion_blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": line[2:]},
                            "annotations": {"bold": False, "italic": False}
                        }
                    ]
                }
            })
            continue
        
        # 4. Gérer les listes à puces
        if line.startswith('- ') or line.startswith('* '):
            rich_text = []
            # Traiter les parties avec du code inline
            parts = line[2:].split('`')  # Enlever les puces (- ou *)
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    # Texte normal
                    rich_text.append({
                        "type": "text",
                        "text": {"content": part},
                        "annotations": {"bold": False, "italic": False}
                    })
                else:
                    # Code inline
                    rich_text.append({
                        "type": "text",
                        "text": {"content": part},
                        "annotations": {"code": True}
                    })
            
            notion_blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": rich_text
                }
            })
            continue
        
        # 7. Gérer le code inline `code`
        if '`' in line:
            parts = line.split('`')
            rich_text = []
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    # Texte normal
                    rich_text.append({
                        "type": "text",
                        "text": {"content": part},
                        "annotations": {"bold": False, "italic": False}
                    })
                else:
                    # Code inline
                    rich_text.append({
                        "type": "text",
                        "text": {"content": part},
                        "annotations": {"code": True}
                    })
            notion_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": rich_text}
            })
            continue

        # 8. Gérer le texte simple
        # Diviser le texte en blocs si nécessaire (limite de 2000 caractères)
        text_blocks = split_text_into_blocks(line)
        for block in text_blocks:
            notion_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": block},
                            "annotations": {"bold": False, "italic": False}
                        }
                    ]
                }
            })
    
    return notion_blocks


# Fonction pour formater le temps en minutes et secondes
def format_time(seconds):
    minutes, sec = divmod(seconds, 60)
    return f"{int(minutes)}mn et {int(sec)}s"

def count_total_items(chapter_structure):
    total = 0
    for subchapters_list in chapter_structure.values():
        for subchapter_dict in subchapters_list:
            if isinstance(subchapter_dict, dict):
                sub_subchapters = list(subchapter_dict.values())[0]
                if sub_subchapters:
                    for sub_subchapter in sub_subchapters:
                        if isinstance(sub_subchapter, dict):
                            sub_sub_subchapters = list(sub_subchapter.values())[0]
                            if sub_sub_subchapters:
                                total += len(sub_sub_subchapters)  # Compte les sous-sous-sous-chapitres
                            else:
                                total += 1  # Compte le sous-sous-chapitre
                        else:
                            total += 1  # Compte le sous-sous-chapitre
                else:
                    total += 1  # Compte le sous-chapitre
            else:
                total += 1  # Compte le sous-chapitre
    return total

# Fonction générale pour créer une page dans Notion
def create_page_in_notion(parent_id, title, content=None):
    # Création de la page sous un parent spécifié par page_id
    new_page = notion.pages.create(
        parent={"page_id": parent_id},
        properties={
            "title": {
                "title": [
                    {"type": "text", "text": {"content": title}}
                ]
            }
        }
    )
    # Ajout du contenu si disponible
    if content:
        notion_blocks = convert_markdown_to_notion_blocks(content, title)
        notion.blocks.children.append(block_id=new_page["id"], children=notion_blocks)
    return new_page

# Fonction pour générer le contenu d'un sous-sous-sous-chapitre avec la structure complète
def generate_content_for_sub_sub_subchapter_with_structure(chapter_title, subchapter_title, sub_subchapter_title, sub_sub_subchapter_title, chapter_structure):
    
    full_prompt = f"""
Tu es chargé de rédiger un référentiel complet sur JWT pour les développeurs.

Voici la structure :

{chapter_structure}

Maintenant, rédige un sous-sous-sous-chapitre détaillé sur : "{sub_sub_subchapter_title}", qui se trouve dans le sous-sous-chapitre "{sub_subchapter_title}" du sous-chapitre "{subchapter_title}" du chapitre "{chapter_title}".

Assure-toi d'éviter les redondances par rapport aux autres parties et vérifie qu'aucune information importante n'est omise.
    """

    # Appel à l'API GPT pour générer le contenu du sous-sous-sous-chapitre
    response = openai.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "user", "content": full_prompt}
        ],
        max_tokens=16384,
        temperature=0.1
    )
    return response.choices[0].message.content.strip()

# Fonction pour générer le contenu d'un sous-sous-chapitre avec la structure complète
def generate_content_for_sub_subchapter_with_structure(chapter_title, subchapter_title, sub_subchapter_title, chapter_structure):

    full_prompt = f"""
Tu es chargé de rédiger un référentiel complet sur JWT pour les développeurs.

Voici la structure :

{chapter_structure}

Maintenant, rédige un sous-sous-chapitre détaillé sur : "{sub_subchapter_title}", qui se trouve dans le sous-chapitre "{subchapter_title}" du chapitre "{chapter_title}".

Assure-toi d'éviter les redondances par rapport aux autres parties et vérifie qu'aucune information importante n'est omise.
    """

    # Appel à l'API GPT pour générer le contenu du sous-sous-chapitre
    response = openai.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "user", "content": full_prompt}
        ],
        max_tokens=16384,
        temperature=0.1
    )
    return response.choices[0].message.content.strip()

# Fonction pour générer le contenu d'un sous-chapitre avec la structure complète
def generate_content_for_subchapter_with_structure(chapter_title, subchapter_title, chapter_structure):
    # Générer une représentation textuelle de la structure

    full_prompt = f"""
Tu es chargé de rédiger un référentiel complet sur JWT pour les développeurs.

Voici la structure :

{chapter_structure}

Maintenant, rédige un sous-chapitre détaillé sur : "{subchapter_title}", qui se trouve dans le chapitre "{chapter_title}".

Assure-toi d'éviter les redondances par rapport aux autres parties et vérifie qu'aucune information importante n'est omise.
    """

    # Appel à l'API GPT pour générer le contenu du sous-chapitre
    response = openai.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "user", "content": full_prompt}
        ],
        max_tokens=16384,
        temperature=0.1
    )
    return response.choices[0].message.content.strip()

# Fonction pour générer tous les chapitres avec la structure donnée
def generate_all_chapters_one_by_one_with_structure(chapter_structure, root_page_id, start_item=1):
    total_items = count_total_items(chapter_structure)
    items_generated = 0
    items_processed = 0
    total_time_spent = 0
    total_chapters = len(chapter_structure)

    chapter_pages = {}
    subchapter_pages = {}
    sub_subchapter_pages = {}

    for chapter_idx, (chapter_title, subchapters_list) in enumerate(chapter_structure.items(), start=1):

        # Création ou récupération de la page du chapitre
        if chapter_title not in chapter_pages:
            print(f"\nGénération du chapitre : {chapter_title} ({chapter_idx}/{total_chapters})")
            chapter_page = create_page_in_notion(parent_id=root_page_id, title=chapter_title)
            chapter_page_id = chapter_page["id"]
            chapter_pages[chapter_title] = chapter_page_id
        else:
            chapter_page_id = chapter_pages[chapter_title]

        for subchapter_dict in subchapters_list:
            if isinstance(subchapter_dict, dict):
                subchapter_title = list(subchapter_dict.keys())[0]
                sub_subchapters = subchapter_dict[subchapter_title]
            else:
                subchapter_title = subchapter_dict
                sub_subchapters = []

            # Création ou récupération de la page du sous-chapitre
            if (chapter_title, subchapter_title) not in subchapter_pages:
                subchapter_page = create_page_in_notion(parent_id=chapter_page_id, title=subchapter_title)
                subchapter_page_id = subchapter_page["id"]
                subchapter_pages[(chapter_title, subchapter_title)] = subchapter_page_id
            else:
                subchapter_page_id = subchapter_pages[(chapter_title, subchapter_title)]

            if sub_subchapters:
                for sub_subchapter in sub_subchapters:
                    if isinstance(sub_subchapter, dict):
                        sub_subchapter_title = list(sub_subchapter.keys())[0]
                        sub_sub_subchapters = sub_subchapter[sub_subchapter_title]
                    else:
                        sub_subchapter_title = sub_subchapter
                        sub_sub_subchapters = []

                    # Création ou récupération de la page du sous-sous-chapitre
                    if (chapter_title, subchapter_title, sub_subchapter_title) not in sub_subchapter_pages:
                        sub_subchapter_page = create_page_in_notion(parent_id=subchapter_page_id, title=sub_subchapter_title)
                        sub_subchapter_page_id = sub_subchapter_page["id"]
                        sub_subchapter_pages[(chapter_title, subchapter_title, sub_subchapter_title)] = sub_subchapter_page_id
                    else:
                        sub_subchapter_page_id = sub_subchapter_pages[(chapter_title, subchapter_title, sub_subchapter_title)]

                    if sub_sub_subchapters:
                        for sub_sub_subchapter_title in sub_sub_subchapters:
                            items_generated += 1

                            if items_generated >= start_item:
                                print(f"Traitement de l'item {items_generated}: Sous-sous-sous-chapitre '{sub_sub_subchapter_title}'")
                                start_time = time.time()

                                # Générer le contenu
                                content = generate_content_for_sub_sub_subchapter_with_structure(
                                    chapter_title, subchapter_title, sub_subchapter_title, sub_sub_subchapter_title, chapter_structure
                                )

                                # Créer la page
                                create_page_in_notion(parent_id=sub_subchapter_page_id, title=sub_sub_subchapter_title, content=content)

                                # Attendre
                                time.sleep(60)

                                # Calculs de temps
                                elapsed_time = time.time() - start_time
                                total_time_spent += elapsed_time
                                items_processed += 1

                                items_remaining = total_items - items_generated
                                average_time_per_item = total_time_spent / items_processed
                                estimated_time_remaining = average_time_per_item * items_remaining

                                print(f"Sous-sous-sous-chapitre généré : {sub_sub_subchapter_title} - Temps restant estimé : {format_time(estimated_time_remaining)}")
                            else:
                                print(f"Sous-sous-sous-chapitre sauté : {sub_sub_subchapter_title}")
                    else:
                        items_generated += 1

                        if items_generated >= start_item:
                            print(f"Traitement de l'item {items_generated}: Sous-sous-chapitre '{sub_subchapter_title}'")
                            start_time = time.time()

                            # Générer le contenu
                            content = generate_content_for_sub_subchapter_with_structure(
                                chapter_title, subchapter_title, sub_subchapter_title, chapter_structure
                            )

                            # Ajouter le contenu
                            notion_blocks = convert_markdown_to_notion_blocks(content, sub_subchapter_title)
                            notion.blocks.children.append(block_id=sub_subchapter_page_id, children=notion_blocks)

                            # Attendre
                            time.sleep(60)

                            # Calculs de temps
                            elapsed_time = time.time() - start_time
                            total_time_spent += elapsed_time
                            items_processed += 1

                            items_remaining = total_items - items_generated
                            average_time_per_item = total_time_spent / items_processed
                            estimated_time_remaining = average_time_per_item * items_remaining

                            print(f"Sous-sous-chapitre généré : {sub_subchapter_title} - Temps restant estimé : {format_time(estimated_time_remaining)}")
                        else:
                            print(f"Sous-sous-chapitre sauté : {sub_subchapter_title}")
            else:
                items_generated += 1

                if items_generated >= start_item:
                    print(f"Traitement de l'item {items_generated}: Sous-chapitre '{subchapter_title}'")
                    start_time = time.time()

                    # Générer le contenu
                    content = generate_content_for_subchapter_with_structure(
                        chapter_title, subchapter_title, chapter_structure
                    )

                    # Ajouter le contenu
                    notion_blocks = convert_markdown_to_notion_blocks(content, subchapter_title)
                    notion.blocks.children.append(block_id=subchapter_page_id, children=notion_blocks)

                    # Attendre
                    time.sleep(60)

                    # Calculs de temps
                    elapsed_time = time.time() - start_time
                    total_time_spent += elapsed_time
                    items_processed += 1

                    items_remaining = total_items - items_generated
                    average_time_per_item = total_time_spent / items_processed
                    estimated_time_remaining = average_time_per_item * items_remaining

                    print(f"Sous-chapitre généré : {subchapter_title} - Temps restant estimé : {format_time(estimated_time_remaining)}")
                else:
                    print(f"Sous-chapitre sauté : {subchapter_title}")

# Structure des chapitres et sous-chapitres
chapter_structure = {
    "Introduction au JWT": [
        {"Qu'est-ce qu'un JWT ?": []},
        {"Historique et évolution du JWT": []},
        {"Avantages de l'utilisation des JWT": []},
        {"Cas d'utilisation typiques des JWT": []}
    ],
    "Concepts de base des JWT": [
        {"Structure d'un JWT": [
            {"En-tête (Header)": []},
            {"Charge utile (Payload)": []},
            {"Signature": []}
        ]},
        {"Encodage et décodage": [
            {"Encodage Base64Url": []},
            {"Sérialisation JSON": []}
        ]},
        {"Exemple détaillé d'un JWT": []},
        {"Claims dans les JWT": [
            {"Claims enregistrés (Registered Claims)": []},
            {"Claims publics": []},
            {"Claims privés": []},
            {"Claims personnalisés": []}
        ]}
    ],
    "Fonctionnement des JWT": [
        {"Création et signature des jetons": []},
        {"Vérification et validation des jetons": []},
        {"Mécanismes d'authentification avec les JWT": []},
        {"Algorithmes de signature": [
            {"Algorithmes symétriques": [
                "HS256",
                "HS384",
                "HS512"
            ]},
            {"Algorithmes asymétriques": [
                "RS256",
                "RS384",
                "RS512",
                "ES256",
                "ES384",
                "ES512"
            ]}
        ]},
        {"Gestion des expirations de jetons et jetons de rafraîchissement": []},
        {"Révocation et invalidation des JWT": []}
    ],
    "Les JWT avec Vapor (Serveur)": [
        {"Présentation de Vapor": []},
        {"Configuration de Vapor pour utiliser les JWT": []},
        {"Création de jetons JWT dans Vapor": []},
        {"Vérification et validation des JWT dans Vapor": []},
        {"Gestion de l'authentification et de l'autorisation": [
            {"Middleware d'authentification": []},
            {"Protection des routes": []},
            {"Gestion des rôles et des permissions": []}
        ]},
        {"Gestion des erreurs et des exceptions dans Vapor": []},
        {"Tests unitaires et d'intégration avec Vapor": []},
        {"Exemples pratiques avec Vapor": []}
    ],
    "Les JWT avec SwiftUI (Client)": [
        {"Présentation de SwiftUI": []},
        {"Intégration des JWT dans SwiftUI": [
            {"Stockage sécurisé des jetons JWT côté client": []},
            {"Envoi de requêtes HTTP authentifiées": []},
            {"Gestion des erreurs et des expirations de jetons": []}
        ]},
        {"Sécurité des applications SwiftUI utilisant les JWT": [
            {"Utilisation du Porte-clés iOS (Keychain)": []},
            {"Meilleures pratiques de sécurité": []}
        ]},
        {"Gestion des jetons de rafraîchissement dans SwiftUI": []},
        {"Gestion des erreurs et des exceptions dans SwiftUI": []},
        {"Tests unitaires et d'intégration avec SwiftUI": []},
        {"Exemples pratiques avec SwiftUI": []}
    ],
    "Communication sécurisée entre Vapor et SwiftUI": [
        {"Authentification de bout en bout": []},
        {"Sécurisation des communications avec HTTPS": []},
        {"Gestion des sessions et des jetons de rafraîchissement": []},
        {"Synchronisation des expirations de jetons entre client et serveur": []},
        {"Gestion des rôles et des permissions": []},
        {"Meilleures pratiques pour la sécurité des communications": []}
    ],
    "Considérations de sécurité": [
        {"Bonnes pratiques de sécurité avec les JWT": []},
        {"Vulnérabilités communes et prévention": [
            {"Fuites de jetons": []},
            {"Attaques par relecture (Replay Attacks)": []},
            {"Attaques de l'algorithme 'none'": []},
            {"Mauvaise gestion des clés": []},
            {"Attaques XSS et CSRF": []}
        ]},
        {"Gestion des clés et rotation des clés": []},
        {"Utilisation de HTTPS et SSL/TLS": []},
        {"Mise en place de politiques CORS appropriées": []},
        {"Stockage sécurisé des jetons côté client": []}
    ],
    "Concepts avancés": [
        {"JWT imbriqués (Nested JWT)": []},
        {"JWT chiffrés (JWE)": []},
        {"Introspection de jetons": []},
        {"Utilisation de JSON Web Key (JWK)": []},
        {"Gestion des multi-clients et multi-plateformes": []},
        {"Comparaison JWT vs OAuth2 vs SAML": []}
    ],
    "Tests, débogage et surveillance": [
        {"Outils pour déboguer les JWT": [
            "JWT.io",
            "Extensions de navigateur",
            "Outils en ligne de commande"
        ]},
        {"Tests unitaires et d'intégration avec Vapor": []},
        {"Tests unitaires et d'intégration avec SwiftUI": []},
        {"Gestion des logs et surveillance": []},
        {"Intégration continue et déploiement continu (CI/CD)": []}
    ],
    "Exemples pratiques et études de cas": [
        {"Création d'une API sécurisée avec Vapor": []},
        {"Développement d'une application SwiftUI consommant l'API": []},
        {"Implémentation de la gestion des jetons de rafraîchissement": []},
        {"Gestion des erreurs et des exceptions": []},
        {"Optimisation des performances": []},
        {"Étude de cas complète : Application de bout en bout": []}
    ],
    "Ressources supplémentaires": [
        {"Documentation officielle de JWT": []},
        {"Documentation de Vapor": []},
        {"Documentation de SwiftUI": []},
        {"Communautés et forums": []},
        {"Bibliothèques et outils utiles": []},
        {"Tutoriels et cours en ligne": []}
    ],
    "Conclusion": [
        {"Récapitulatif des points clés": []},
        {"Perspectives d'avenir pour les JWT": []},
        {"Prochaines étapes pour les développeurs": []},
        {"Ressources pour aller plus loin": []}
    ]
}

# Lancer la génération des chapitres un par un
generate_all_chapters_one_by_one_with_structure(chapter_structure, root_page_id, start_item=1)