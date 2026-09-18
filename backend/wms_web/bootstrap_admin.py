from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

from backend.wms_web.admin_config import AdminConfigStore
from backend.wms_web.passwords import hash_password


ADMIN_GROUP_ID = "amministratori-wms"


def bootstrap(data_dir: Path, username: str, display_name: str):
    data_dir.mkdir(parents=True, exist_ok=True)
    config = AdminConfigStore(data_dir / ".wms-config.json", seed_demo=False)

    username = username.strip()
    display_name = display_name.strip()

    if not username:
        raise ValueError("Il login è obbligatorio")
    if not display_name:
        raise ValueError("Il nome visualizzato è obbligatorio")

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Conferma password: ")

    if password != confirmation:
        raise ValueError("Le password non coincidono")

    password_hash = hash_password(password)

    existing = next(
        (u for u in config.list("users") if u.get("username") == username),
        None,
    )
    if existing:
        raise ValueError(f"L'utente {username!r} esiste già")

    groups = config.list("groups")
    if not any(g["id"] == ADMIN_GROUP_ID for g in groups):
        config.save("groups", {
            "id": ADMIN_GROUP_ID,
            "name": "Amministratori WMS",
            "role": "AMMINISTRATORE",
            "active": True,
        })

    user_id = username
    membership_id = f"{user_id}-amministratore"

    config.save("users", {
        "id": user_id,
        "username": username,
        "display_name": display_name,
        "default_membership_id": "",
        "active": True,
    })

    config.save("memberships", {
        "id": membership_id,
        "user_id": user_id,
        "group_id": ADMIN_GROUP_ID,
        "label": "Amministratore WMS",
        "active": True,
    })

    config.save("users", {
        "id": user_id,
        "default_membership_id": membership_id,
    })

    config.set_password_hash(user_id, password_hash)

    print(f"Amministratore creato: {username}")
    print(f"Directory dati: {data_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Crea il primo amministratore WMS"
    )
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("WMS_DATA_DIR", "."),
        help="Directory dati WMS",
    )
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args()

    bootstrap(
        Path(args.data_dir),
        args.username,
        args.display_name,
    )


if __name__ == "__main__":
    main()
