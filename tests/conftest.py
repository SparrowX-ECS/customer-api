import sys
import os
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5433")
os.environ.setdefault("DB_NAME", "customerdb")
os.environ.setdefault("DB_USERNAME", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
