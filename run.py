import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from src.ui.app import run_app

if __name__ == "__main__":
    run_app()
