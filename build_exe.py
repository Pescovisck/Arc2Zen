import os
import sys
import subprocess
from pathlib import Path

def build():
    print("Starting Arc2Zen executable build process...")

    # Define paths
    workspace_dir = Path(__file__).parent.resolve()
    entry_point = workspace_dir / "app.py"
    src_dir = workspace_dir / "src"

    if not entry_point.exists():
        print(f"Error: Entry point not found at {entry_point}")
        sys.exit(1)

    if not src_dir.exists():
        print(f"Error: Sources directory not found at {src_dir}")
        sys.exit(1)

    # PyInstaller arguments
    # --onefile: build a single executable
    # --noconsole: do not open a console window
    # --name: output executable name
    # --add-data: bundle the src directory (in Windows syntax is: source;dest)
    # --clean: clean PyInstaller cache before build
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--paths=src",
        "--noconsole",
        "--name=Arc2Zen",
        f"--add-data={src_dir};src",
        "--clean",
        str(entry_point)
    ]

    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, cwd=str(workspace_dir))
        print("=" * 50)
        print("SUCCESS: Standalone executable created successfully!")
        print(f"Output location: {workspace_dir / 'dist' / 'Arc2Zen.exe'}")
        print("=" * 50)
    except subprocess.CalledProcessError as e:
        print(f"Error: PyInstaller build failed with exit code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    build()
