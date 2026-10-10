from datetime import timedelta
from temporalio import workflow


with workflow.unsafe.imports_passed_through():
    from workflows.activities import (
        ask_anythingllm,
        ask_gemini,
        validate_ai_response,
        generate_ansible_playbook,
        validate_playbook,
        execute_ansible_playbook,
        verify_network_configuration,
        format_ansible_result,
        push_to_gitea,
    )


@workflow.defn
class AIOpsWorkflow:
    
    def __init__(self):
        self.approval_decision = None

    @workflow.signal
    async def approve(self, decision: str):
        self.approval_decision = decision

    @workflow.run
    async def run(self, prompt: str) -> dict:

        knowledge_response = await workflow.execute_activity(
            ask_anythingllm,
            prompt,
            start_to_close_timeout=timedelta(minutes=3),
        )


        gemini_prompt = f"""
Tu es un ingénieur réseau chargé d'analyser une demande
d'automatisation réseau.

Demande utilisateur :
{prompt}

Informations provenant de la base de connaissances :
{knowledge_response}

Tu dois produire UNIQUEMENT un objet JSON valide.

Structure obligatoire :

{{
  "request": "demande utilisateur",
  "decision": "approved | validation_required | rejected",
  "analysis": "analyse technique",
  "commands": [],
  "ansible_required": true,
  "risks": []
}}

Règles :

- Ne crée pas de règles internes absentes de la base.
- Si une validation humaine est nécessaire :
  "validation_required".
- Si la demande viole une règle :
  "rejected".
- Si la demande est conforme :
  "approved".
  
  Règles techniques Ansible :

- Le playbook doit utiliser la collection cisco.ios.
- Pour créer ou modifier un VLAN avec cisco.ios.ios_vlans :
  utiliser state: merged.
- Pour supprimer un VLAN avec cisco.ios.ios_vlans :
  utiliser state: deleted.
- Ne jamais utiliser state: absent avec cisco.ios.ios_vlans.
- Pour une suppression complète d'un VLAN Cisco, l'opération attendue
  correspond à la commande Cisco "no vlan <vlan_id>".
- Le playbook généré doit être compatible avec le module utilisé.
- Retourne uniquement le JSON.
"""

        gemini_response = await workflow.execute_activity(
            ask_gemini,
            gemini_prompt,
            start_to_close_timeout=timedelta(minutes=2),
        )

        # =====================================================
        # 3. Validation de la réponse de Gemini
        # =====================================================

        validated_response = await workflow.execute_activity(
            validate_ai_response,
            gemini_response,
            start_to_close_timeout=timedelta(minutes=3),
        )

        # =====================================================
        # 4. Vérification du rejet automatique
        # =====================================================

        if validated_response["decision"] == "rejected":
            return {
                "status": "rejected",
                "proposal": validated_response,
            }

        # =====================================================
        # 5. Génération du playbook Ansible
        # =====================================================

        playbook_data = await workflow.execute_activity(
            generate_ansible_playbook,
            validated_response,
            start_to_close_timeout=timedelta(minutes=3),
        )

        # =====================================================
        # 6. Validation du playbook
        # =====================================================

        playbook_validation = await workflow.execute_activity(
            validate_playbook,
            playbook_data,
            start_to_close_timeout=timedelta(minutes=3),
        )

        if not playbook_validation["valid"]:
            return {
                "status": "clarification_required",
                "proposal": validated_response,
                "playbook": playbook_data,
                "validation": playbook_validation,
            }

        # =====================================================
        # 7. ATTENTE DE LA VALIDATION HUMAINE
        # =====================================================

        await workflow.wait_condition(
            lambda: self.approval_decision is not None
        )

        if self.approval_decision == "rejected":
            return {
                "status": "rejected_by_human",
                "proposal": validated_response,
                "playbook": playbook_data,
                "playbook_validation": playbook_validation,
            }

        if self.approval_decision != "approved":
            return {
                "status": "invalid_approval",
                "proposal": validated_response,
                "playbook": playbook_data,
                "playbook_validation": playbook_validation,
            }

        # =====================================================
        # 8. Exécution du playbook sur la machine Ansible
        # =====================================================

        ansible_result = await workflow.execute_activity(
            execute_ansible_playbook,
            playbook_data,
            start_to_close_timeout=timedelta(minutes=5),
        )
        # -----------------------------------------------------
        # Échec Ansible
        # -----------------------------------------------------

        if not ansible_result["success"]:
            return {
                "status": "ansible_execution_failed",
                "proposal": validated_response,
                "playbook": playbook_data,
                "playbook_validation": playbook_validation,
                "ansible": ansible_result,
            }


        # =====================================================
        # 9. Vérification de la configuration dans PNETLab
        # =====================================================

        verification_result = await workflow.execute_activity(
            verify_network_configuration,
            playbook_data,
            start_to_close_timeout=timedelta(minutes=3),
        )

        if not verification_result["success"]:
            return {
                "status": "network_verification_failed",
                "proposal": validated_response,
                "playbook": playbook_data,
                "playbook_validation": playbook_validation,
                "ansible": ansible_result,
                "verification": verification_result,
            }


        # =====================================================
        # 9. Transformation du résultat Ansible
        # =====================================================

        formatted_result = await workflow.execute_activity(
            format_ansible_result,
            {
                "prompt": prompt,
                "playbook": playbook_data["playbook"],
                "ansible_result": ansible_result,
                "verification_result": verification_result,
            },
            start_to_close_timeout=timedelta(minutes=2),
        )

        # =====================================================
        # 10. Push du playbook vers Gitea
        # =====================================================

        gitea_result = await workflow.execute_activity(
            push_to_gitea,
            playbook_data,
            start_to_close_timeout=timedelta(minutes=3),
        )

        # -----------------------------------------------------
        # Échec Gitea
        # -----------------------------------------------------

        if not gitea_result["success"]:
            return {
                "status": "gitea_push_failed",
                "proposal": validated_response,
                "playbook": playbook_data,
                "playbook_validation": playbook_validation,
                "result": formatted_result,
                "gitea": gitea_result,
            }

        # =====================================================
        # 11. Résultat final propre pour l'utilisateur
        # =====================================================

        return {
            "status": "completed",
            "result": formatted_result,
        }