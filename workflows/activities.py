from asyncio import timeout
import os
import ast
from temporalio import activity
import json
import re
import yaml
import subprocess
import tempfile

from pathlib import Path
from services.anythingllm_client import AnythingLLMClient
from services.gemini_client import GeminiClient
from services.git_service1 import GitService

def clean_json_response(raw_response: str) -> str:
    """
    Nettoie une réponse JSON provenant du modèle.

    Le modèle peut retourner :
        ```json
        {...}
        ```

    ou directement :
        {...}

    Cette fonction retire les éventuelles balises Markdown.
    """

    if not raw_response:
        return ""

    cleaned = raw_response.strip()

    # Supprimer ```json au début
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()

    # Supprimer ``` au début si le modèle n'a pas précisé json
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()

    # Supprimer ``` à la fin
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return cleaned


def validate_playbook_name(playbook_name: str) -> bool:
    """
    Vérifie que le nom du playbook respecte notre convention.

    Exemple valide :
        create_vlan_120_serveurs

    Exemple invalide :
        Create VLAN 120 SERVEURS
        create-vlan-120
        create/vlan
        create_vlan_120.yml
    """

    if not playbook_name:
        return False

    pattern = r"^[a-z0-9]+(?:_[a-z0-9]+)*$"

    return bool(re.fullmatch(pattern, playbook_name))


@activity.defn
async def ask_anythingllm(prompt: str) -> str:

    client = AnythingLLMClient()

    response = client.ask(prompt)

    return response.get("textResponse", "")


@activity.defn
async def ask_gemini(prompt: str) -> str:

    client = GeminiClient()

    response = client.ask(prompt)

    return response.get("response", "")


@activity.defn
async def validate_ai_response(response: str) -> dict:

    try:
        # Nettoyer la réponse de Gemini avant json.loads()
        cleaned_response = clean_json_response(response)

        data = json.loads(cleaned_response)

        print("=== AI RESPONSE ===")
        print(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            )
        )

        print("=== DECISION ===")
        print(repr(data.get("decision")))

    except json.JSONDecodeError as e:
        print("=== RAW GEMINI RESPONSE ===")
        print(repr(response))

        raise ValueError(
            f"La réponse de Gemini n'est pas un JSON valide : {e}"
        )

    required_fields = [
        "analysis",
        "request",
        "decision",
        "commands",
        "ansible_required",
        "risks",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in data
    ]

    if missing_fields:
        raise ValueError(
            "Champs manquants dans la réponse Gemini : "
            f"{missing_fields}"
        )

    allowed_decisions = {
        "validation_required",
        "approved",
        "rejected",
    }

    if data["decision"] not in allowed_decisions:
        raise ValueError(
            f"Decision invalide : {data['decision']}"
        )

    if not isinstance(data["commands"], list):
        raise ValueError(
            "Le champ 'commands' doit être une liste."
        )

    if not isinstance(data["risks"], list):
        raise ValueError(
            "Le champ 'risks' doit être une liste."
        )

    if not isinstance(data["ansible_required"], bool):
        raise ValueError(
            "Le champ 'ansible_required' doit être booléen."
        )

    return data


@activity.defn
async def generate_ansible_playbook(
    proposal: dict,
) -> dict:

    client = GeminiClient()

    prompt = f"""
Tu es un ingénieur réseau spécialisé en Cisco IOS et Ansible.

Voici la proposition analysée :

{json.dumps(proposal, ensure_ascii=False, indent=2)}

Ta tâche est de préparer le playbook Ansible correspondant.

Retourne UNIQUEMENT un objet JSON valide.

IMPORTANT :
- Ne mets pas de texte avant le JSON.
- Ne mets pas de texte après le JSON.
- N'utilise pas de bloc Markdown ```json.
- Le résultat doit être directement compatible avec json.loads().

Structure obligatoire :

Structure obligatoire :

{{
  "playbook_available": true,
  "explanation": "Explication simple destinée à un ingénieur réseau qui ne maîtrise pas forcément Ansible.",
  "playbook_name": "create_vlan_100_rh",
  "playbook": "contenu YAML du playbook",
  "tasks_explanation": [
    {{
      "task": "Nom de la tâche",
      "explanation": "Explication simple de ce que fait la tâche"
    }}
  ],
  "verification": {{
    "device": "sw1",
    "command": "show vlan brief",
    "expected": {{
      "vlan_id": 100,
      "name": "RH"
    }}
  }}
}}

Règles :

1. Ne génère pas d'action qui n'est pas justifiée par la proposition.

2. Utilise les modules Cisco IOS appropriés.

3. Le résultat du champ "playbook" doit être un vrai playbook Ansible YAML.

4. Ne mets aucune commande fictive.

5. Si les informations sont insuffisantes pour générer un playbook sûr,
   mets "playbook_available": false.

6. Dans ce cas, explique précisément pourquoi.

7. L'explication doit être compréhensible par une personne
   qui ne maîtrise pas la syntaxe Ansible.

8. Le champ "playbook_name" doit être un nom de fichier lisible
   et descriptif.

9. Utilise uniquement des lettres minuscules, des chiffres
   et des underscores (_).

10. N'utilise pas d'espaces, d'accents, de caractères spéciaux
    ou de slash (/).

11. Ne mets pas l'extension ".yml" dans "playbook_name".

12. Le nom doit décrire l'action et la ressource concernée.

13. Exemples :

    create_vlan_100_rh
    update_vlan_100_rh
    delete_vlan_100_rh
    configure_switch_port
14. Le champ "verification" est obligatoire lorsque le playbook
    modifie la configuration d'un équipement réseau.

15. Le champ "verification" doit indiquer l'équipement cible,
    la commande permettant de vérifier la configuration et
    les valeurs attendues après exécution.

16. Pour une création ou modification de VLAN Cisco,
    utilise obligatoirement :

    "command": "show vlan brief"

17. Pour une création de VLAN, le champ "expected" doit contenir :

    "vlan_id": <identifiant du VLAN>,
    "name": "<nom du VLAN>"

18. La vérification doit permettre de déterminer automatiquement
    si la configuration demandée est effectivement présente
    sur l'équipement après l'exécution du playbook.
"""

    response = client.ask(prompt)

    raw_response = response.get("response", "")

    if not raw_response:
        raise ValueError(
            "Gemini n'a retourné aucune réponse pour le playbook."
        )

    try:
        # Nettoyer la réponse avant json.loads()
        cleaned_response = clean_json_response(raw_response)

        playbook_data = json.loads(cleaned_response)

    except json.JSONDecodeError as e:

        print("=== RAW GEMINI PLAYBOOK RESPONSE ===")
        print(repr(raw_response))

        raise ValueError(
            "La réponse de Gemini pour le playbook "
            f"n'est pas un JSON valide : {e}"
        )

    # Vérifier playbook_available
    if "playbook_available" not in playbook_data:
        raise ValueError(
            "Le champ 'playbook_available' est absent."
        )

    # Si aucun playbook n'est disponible,
    # on retourne la réponse pour permettre au workflow
    # de gérer ce cas.
    if not playbook_data["playbook_available"]:
        return playbook_data

    # Vérifier les champs obligatoires
    required_fields = [
        "explanation",
        "playbook_name",
        "playbook",
        "tasks_explanation",
        "verification",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in playbook_data
    ]

    if missing_fields:
        raise ValueError(
            "Champs manquants dans la réponse du playbook : "
            f"{missing_fields}"
        )

    # Vérifier le nom
    playbook_name = playbook_data["playbook_name"]

    if not isinstance(playbook_name, str):
        raise ValueError(
            "Le champ 'playbook_name' doit être une chaîne de caractères."
        )

    if not validate_playbook_name(playbook_name):
        raise ValueError(
            "Nom de playbook invalide : "
            f"'{playbook_name}'. "
            "Format attendu : create_vlan_100_rh"
        )

    # Vérifier le contenu du playbook
    if not isinstance(playbook_data["playbook"], str):
        raise ValueError(
            "Le champ 'playbook' doit être une chaîne de caractères."
        )

    # Vérifier tasks_explanation
    if not isinstance(
        playbook_data["tasks_explanation"],
        list
    ):
        raise ValueError(
            "Le champ 'tasks_explanation' doit être une liste."
        )
    if not isinstance(
        playbook_data["verification"],
        dict
    ):
        raise ValueError(
            "Le champ 'verification' doit être un objet."
        )

    verification = playbook_data["verification"]

    if "device" not in verification:
        raise ValueError(
            "L'équipement cible de la vérification est manquant."
        )

    if "command" not in verification:
        raise ValueError(
            "La commande de vérification est manquante."
        )

    if "expected" not in verification:
        raise ValueError(
            "Les valeurs attendues après exécution sont manquantes."
        )
    return playbook_data


@activity.defn
async def validate_playbook(
    playbook_data: dict,
) -> dict:

    if not playbook_data.get("playbook_available"):
        return {
            "valid": False,
            "reason": (
                "Aucun playbook exploitable n'a été généré."
            ),
        }

    playbook = playbook_data.get(
        "playbook",
        ""
    )

    if not playbook.strip():
        return {
            "valid": False,
            "reason": "Le playbook est vide.",
        }

    try:

        parsed = list(
            yaml.safe_load_all(playbook)
        )

    except yaml.YAMLError as e:

        return {
            "valid": False,
            "reason": f"YAML invalide : {e}",
        }

    if not parsed:

        return {
            "valid": False,
            "reason": (
                "Le playbook ne contient aucun document YAML."
            ),
        }

    return {
        "valid": True,
        "reason": (
            "Le YAML est syntaxiquement valide."
        ),
    }

@activity.defn
async def execute_ansible_playbook(
    playbook_data: dict,
) -> dict:

    if not playbook_data.get("playbook_available"):
        return {
            "success": False,
            "reason": "Aucun playbook disponible.",
        }

    playbook = playbook_data.get("playbook", "")

    if not playbook.strip():
        return {
            "success": False,
            "reason": "Le playbook est vide.",
        }

    temp_path = "/tmp/generated_playbook.yml"

    try:

        # Écrire temporairement le playbook sur la VM Temporal
        with open(temp_path, "w") as f:
            f.write(playbook)

        # Copier le playbook vers la VM Ansible
        scp_result = subprocess.run(
            [
                "scp",
                temp_path,
                "laila@192.168.106.132:/tmp/generated_playbook.yml",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if scp_result.returncode != 0:
            return {
                "success": False,
                "reason": "Impossible de copier le playbook vers ansiblee.",
                "stderr": scp_result.stderr,
            }

        # Exécuter Ansible sur ansiblee
        result = subprocess.run(
            [
                "ssh",
                "laila@192.168.106.132",
                "ansible-playbook -i ~/hosts.yml /tmp/generated_playbook.yml",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        return {
            
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            #"message": (
            #    "Playbook exécuté avec succès sur ansiblee."
            #   if result.returncode == 0
            #  else "Échec de l'exécution Ansible sur ansiblee."
            #),
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "reason": "Timeout pendant l'exécution Ansible.",
        }

    except Exception as e:
        return {
            "success": False,
            "reason": f"Erreur : {str(e)}",
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@activity.defn
async def verify_network_configuration(
    playbook_data: dict,
) -> dict:

    verification = playbook_data.get("verification")

    if not verification:
        return {
            "success": False,
            "reason": "Aucune information de vérification n'a été fournie.",
        }

    device = verification.get("device")
    command = verification.get("command")
    expected = verification.get("expected", {})

    if not device:
        return {
            "success": False,
            "reason": "L'équipement cible est manquant.",
        }

    if not command:
        return {
            "success": False,
            "reason": "La commande de vérification est manquante.",
        }

    vlan_id = expected.get("vlan_id")
    vlan_name = expected.get("name")

    try:

        result = subprocess.run(
            [
                "ssh",
                "laila@192.168.106.132",
                f"ansible {device} -i ~/hosts.yml "
                f"-m ansible.netcommon.cli_command "
                f"-a 'command=\"{command}\"'",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "device": device,
                "command": command,
                "reason": "Échec de l'exécution de la commande.",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }

        output = result.stdout

        # Vérification du VLAN
        if vlan_id is not None:

            vlan_found = False

            for line in output.splitlines():

                line = line.strip()

                # Exemple :
                # 200  RH  active

                match = re.match(
                    rf"^{vlan_id}\s+(\S+)\s+(active|act/unsup)\b",
                    line,
                    re.IGNORECASE,
                )

                if match:

                    detected_name = match.group(1).strip()
                    detected_status = match.group(2).strip().lower()

                    if vlan_name:
                        if (
                            detected_name.lower() == vlan_name.lower()
                            and detected_status == "active"
                        ):
                            vlan_found = True
                    else:
                        if detected_status == "active":
                            vlan_found = True

            if vlan_found:

                return {
                    "success": True,
                    "device": device,
                    "command": command,
                    "expected": expected,
                    "output": output,
                    "message": (
                        f"Le VLAN {vlan_id} "
                        f"({vlan_name}) est présent sur {device}."
                    ),
                }

            return {
                "success": False,
                "device": device,
                "command": command,
                "expected": expected,
                "output": output,
                "reason": (
                    f"Le VLAN {vlan_id} "
                    f"({vlan_name}) n'a pas été trouvé sur {device}."
                ),
            }

        return {
            "success": True,
            "device": device,
            "command": command,
            "output": output,
            "message": "La vérification a été exécutée avec succès.",
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "device": device,
            "command": command,
            "reason": "Timeout pendant la vérification.",
        }

    except Exception as e:

        return {
            "success": False,
            "device": device,
            "command": command,
            "reason": f"Erreur pendant la vérification : {str(e)}",
        }
@activity.defn
async def format_ansible_result(data: dict) -> dict:

    client = GeminiClient()

    prompt = f"""
Tu es chargé de transformer le résultat brut d'une exécution
Ansible en une réponse claire destinée à l'utilisateur.

Demande originale :
{data["prompt"]}

Playbook exécuté :
{data["playbook"]}

Résultat Ansible :
{data["ansible_result"]}

Résultat de la vérification réseau :
{data["verification_result"]}

Retourne UNIQUEMENT un JSON valide.

Structure :

{{
    "success": true,
    "title": "Titre court",
    "message": "Résumé clair du résultat",
    "data": [],
    "columns": []
}}

Règles :

1. Ne conserve que les informations utiles pour répondre
   à la demande originale.

2. Ne retourne jamais :
   - les warnings Ansible
   - les dépréciations
   - les informations internes d'exécution
   - les chemins de fichiers
   - les détails techniques inutiles
   - stdout complet

3. Si le résultat contient une liste d'éléments,
   utilise "data" comme liste.

4. Si les données peuvent être représentées sous forme de tableau,
   utilise "columns" pour les colonnes pertinentes.

5. Adapte automatiquement la réponse au type de demande.
   Ne suppose jamais qu'il s'agit de VLANs.

6. Ne supprime pas une information nécessaire pour répondre
   correctement à la demande.

7. Si l'exécution a échoué :
   "success": false
   et explique simplement l'erreur utile à l'utilisateur.

8. Retourne uniquement le JSON.

9. Si la vérification réseau confirme que la configuration
   demandée est présente sur l'équipement, indique clairement
   que la configuration a été appliquée et vérifiée avec succès.

10. Si la vérification réseau échoue, indique que la configuration
    n'a pas pu être confirmée.
"""

    response = client.ask(prompt)

    raw_response = response.get("response", "")

    cleaned_response = clean_json_response(raw_response)

    return json.loads(cleaned_response)
            
@activity.defn
async def push_to_gitea(
    playbook_data: dict,
) -> dict:

    if not playbook_data.get("playbook_available"):
        return {
            "success": False,
            "reason": "Aucun playbook disponible.",
        }

    playbook = playbook_data.get(
        "playbook",
        ""
    )

    playbook_name = playbook_data.get(
        "playbook_name",
        ""
    )

    if not playbook.strip():
        return {
            "success": False,
            "reason": "Le playbook est vide.",
        }

    if not playbook_name.strip():
        return {
            "success": False,
            "reason": "Le nom du playbook est manquant.",
        }

    if not validate_playbook_name(playbook_name):
        return {
            "success": False,
            "reason": (
                f"Nom de playbook invalide : "
                f"{playbook_name}"
            ),
        }

    try:

        # 1. Sauvegarder le playbook
        filepath = GitService.save_playbook(
            playbook,
            playbook_name
        )

        # 2. Commit + push vers Gitea
        GitService.git_push(filepath)

        return {
            "success": True,
            "filename": filepath.name,
            "filepath": str(filepath),
            "message": (
                "Playbook envoyé avec succès vers Gitea."
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "reason": (
                "Erreur lors du push vers Gitea : "
                f"{str(e)}"
            ),
        }