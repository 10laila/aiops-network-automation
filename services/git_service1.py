from pathlib import Path
import subprocess
import re


REPO = Path.home() / "aiops-project"


class GitService:

    @staticmethod
    def save_playbook(playbook: str, playbook_name: str):
        folder = REPO / "playbooks"
        folder.mkdir(parents=True, exist_ok=True)

        # Nettoyer le nom pour qu'il soit compatible avec Linux/Git/Ansible
        filename = re.sub(r"[^a-zA-Z0-9_-]", "_", playbook_name.strip())

        # Éviter les doubles extensions
        if filename.endswith(".yml"):
            filename = filename[:-4]

        filepath = folder / f"{filename}.yml"

        filepath.write_text(playbook, encoding="utf-8")

        return filepath

    @staticmethod
    def git_push(filepath):
        subprocess.run(
            ["git", "add", str(filepath)],
            cwd=REPO,
            check=True,
        )

        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"Ajout automatique du playbook : {filepath.name}",
            ],
            cwd=REPO,
            check=True,
        )

        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=REPO,
            check=True,
        )