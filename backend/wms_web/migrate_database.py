"""Import legacy WMS files into SQL without changing the originals."""
import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from backend.wms_web.admin_config import AdminConfigStore
from backend.wms_web.database import Database, database_location
from backend.wms_web.organization_service import OrganizationalPracticeService


def migrate(data_dir, location):
    data_dir = Path(data_dir)
    backup = data_dir / 'backups' / ('pre-database-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    backup.mkdir(parents=True)
    for name in ('.wms-config.json', '.wms-demo-state.pkl'):
        source = data_dir / name
        if source.exists(): shutil.copy2(source, backup / name)
    database = Database(location)
    try:
        config = AdminConfigStore(data_dir / '.wms-config.json', seed_demo=False, database=database)
        service = OrganizationalPracticeService(state_path=data_dir / '.wms-demo-state.pkl', seed_demo=False, database=database)
        config.sync_clients(p.client_id for p in service._practices.values())
        counts = {k: len(config.list(k)) for k in ('users','groups','memberships','clients','practice_types')}
        return {'backup': str(backup), **counts, 'practices': len(service._practices)}
    finally:
        database.connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('WMS_DATA_DIR','.')))
    parser.add_argument('--database', default=os.environ.get('WMS_DATABASE_URL'))
    args = parser.parse_args()
    if not args.database or not args.database.startswith(('postgresql://','postgres://')):
        parser.error('Impostare WMS_DATABASE_URL o --database con il database PostgreSQL di destinazione')
    print(json.dumps(migrate(args.data_dir, args.database), indent=2))


if __name__ == '__main__': main()
