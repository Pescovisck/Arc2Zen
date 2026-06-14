# Arc to Zen Browser Migrator (Desktop App)

A sleek, modern, and fully automated Windows desktop GUI application that migrates your workspaces, folder structures, pinned tabs, open tabs, and browsing history from the **Arc browser** to the **Zen browser**.

This tool wraps the core Python migration logic with a beautiful dark-mode interface built using CustomTkinter, allowing you to perform the entire migration process with a single click.

---

## 🤖 Developed using AI

This desktop application and build packaging setup were developed using **Antigravity**, an agentic AI coding assistant.

---

## 🌟 Credits & Acknowledgments

This GUI wrapper is built on top of the excellent work in the [rafcabezas/arc2zen](https://github.com/rafcabezas/arc2zen) repository. All props and credits for the core logic of Arc sidebar parsing and Zen sessions/sessionstore injection go to the original author, **Rafael Cabezas** (`@rafcabezas`).

---

## Features

- **Automated Scanning:** Automatically discovers your Arc sidebar file (`StorableSidebar.json`) and your active Zen browser profiles on Windows.
- **Space Filtering:** Select exactly which Arc Spaces you want to import into Zen.
- **Modern Tab Migration:** Imports Arc pinned tabs and nested folders directly into Zen's modern session store (`zen-sessions.jsonlz4`).
- **Open Tabs Migration:** Restores your open tabs into separate Zen workspaces.
- **Browsing History:** Merges your Arc browsing history directly into Zen's history database.
- **Isolated Containers:** Optionally maps each Arc Space to a cookie-isolated container in Zen.
- **Safe Execution:** Automatically creates timestamped backups of your Zen configuration before performing any changes. Includes a **Dry Run** mode to test settings before writing them.

---

## Getting Started

### 🚀 Direct Download
You can download the pre-compiled standalone executable **[Arc2Zen.exe](https://github.com/<your-username>/<your-repo>/releases/latest/download/Arc2Zen.exe)** (or find it in the `dist/` directory) and run it directly without any installation or python environment.

### 🛠️ Running from Source

#### Prerequisites
You need Python 3.10+ installed on your system.

#### Setup & Execution

1. Clone this repository:
   ```bash
   git clone <your-repo-url>
   cd Arc2Zen
   ```

2. Install dependencies:
   ```bash
   pip install customtkinter lz4 pyinstaller
   ```

3. Launch the application:
   ```bash
   python app.py
   ```

### Building the Standalone Executable (EXE)

To compile the script into a single standalone executable (`dist/Arc2Zen.exe`) that runs without requiring a python environment:

1. Run the build helper:
   ```bash
   python build_exe.py
   ```
2. Locate the compiled executable inside the `dist/` directory.

---

## How to Migrate

1. **Close your browsers:** Completely exit both Arc and Zen browsers to release configuration file locks.
2. **Launch the tool:** Double-click `Arc2Zen.exe` (or run `python app.py`).
3. **Verify paths:** Confirm that the auto-detected paths for Arc and Zen are correct.
4. **Choose spaces:** Tick the checkbox next to the Arc Spaces you want to migrate.
5. **Adjust settings:** Choose whether to migrate pinned tabs, open tabs, history, and container associations.
6. **Start migration:** Click **Start Migration**.
7. **Done:** Reopen Zen browser to enjoy your new workspace setup!
