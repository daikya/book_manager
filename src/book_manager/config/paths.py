from pathlib import Path

# リポジトリルート
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# ディレクトリ
DATA_DIR = PROJECT_ROOT / "data"
BACKUP_DIR = PROJECT_ROOT / "backups"
CACHE_DIR = PROJECT_ROOT / "cache"

# データベース
DATABASE_PATH = DATA_DIR / "book_manager.db"