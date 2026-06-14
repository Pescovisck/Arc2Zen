import os
import sys
import json
import logging
import queue
import threading
from pathlib import Path
from typing import List, Dict, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

# Add src directory to path to load modules correctly
sys.path.append(str(Path(__file__).parent / "src"))

from arc_pinned_tab_extractor import ArcPinnedTabExtractor, ArcSpace
from zen_schema_analyzer import ZenSchemaAnalyzer
from zen_space_importer import ZenSpaceImporter, ZenProfile
from zen_sessions_importer import ZenSessionsImporter
from arc_history_migrator import ArcHistoryMigrator
from zen_sessionstore_manager import ZenSessionstoreManager
from zen_bookmark_importer import ZenBookmarkImporter

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")  # We'll customize widgets with premium violet accent


class GuiLogHandler(logging.Handler):
    """Safely redirects Python logger outputs to a CustomTkinter Textbox widget."""
    def __init__(self, textbox_widget: ctk.CTkTextbox):
        super().__init__()
        self.textbox = textbox_widget
        self.msg_queue = queue.Queue()
        self.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        # Start checking the queue
        self.textbox.after(50, self._process_queue)

    def emit(self, record):
        self.msg_queue.put(self.format(record) + "\n")

    def _process_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                self.textbox.configure(state="normal")
                self.textbox.insert("end", msg)
                self.textbox.see("end")
                self.textbox.configure(state="disabled")
                self.msg_queue.task_done()
        except queue.Empty:
            pass
        self.textbox.after(50, self._process_queue)


class Arc2ZenApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Arc to Zen Browser Migrator")
        self.geometry("850x680")
        self.minsize(800, 600)

        # Style colors
        self.accent_color = "#8a2be2"  # Violet
        self.accent_hover = "#6a1b9a"
        self.bg_card = "#2d2d2d"

        # Data states
        self.discovered_arc_spaces: List[ArcSpace] = []
        self.discovered_zen_profiles: List[Path] = []
        self.selected_zen_profile_path: Optional[Path] = None
        self.space_checkboxes: Dict[str, ctk.CTkCheckBox] = {}

        self._create_widgets()
        self._setup_logging()
        self._initialize_discovery()

    def _create_widgets(self):
        # Grid layout configuration (3 rows: Header, Main Content, Footer)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- HEADER ---
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, height=80, fg_color="#1e1e1e")
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="🔄 Arc to Zen Browser Migrator",
            font=ctk.CTkFont(family="Inter", size=22, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Transfer workspaces, pinned tabs, open tabs, and history automatically",
            font=ctk.CTkFont(family="Inter", size=13),
            text_color="gray"
        )
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        # --- MAIN CONTAINER ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=1, column=0, padx=20, pady=15, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=3) # Left: Configuration
        self.main_container.grid_columnconfigure(1, weight=2) # Right: Spaces List
        self.main_container.grid_rowconfigure(0, weight=1)

        # Left Column Frame
        self.left_column = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.left_column.grid_columnconfigure(0, weight=1)
        self.left_column.grid_rowconfigure(1, weight=1)  # Expand logging box

        # 1. Path Configuration Card
        self.path_frame = ctk.CTkFrame(self.left_column, fg_color=self.bg_card)
        self.path_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=2)
        self.path_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.path_frame,
            text="System Paths",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, columnspan=3, padx=15, pady=10, sticky="w")

        # Arc path
        ctk.CTkLabel(self.path_frame, text="Arc Sidebar:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.arc_path_entry = ctk.CTkEntry(self.path_frame)
        self.arc_path_entry.grid(row=1, column=1, padx=(5, 5), pady=5, sticky="ew")
        self.arc_browse_btn = ctk.CTkButton(
            self.path_frame, text="Browse", width=70, fg_color=self.accent_color, hover_color=self.accent_hover,
            command=self._browse_arc_path
        )
        self.arc_browse_btn.grid(row=1, column=2, padx=(0, 15), pady=5)

        # Zen profile path
        ctk.CTkLabel(self.path_frame, text="Zen Profile:").grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.zen_profile_combo = ctk.CTkComboBox(self.path_frame, command=self._on_zen_profile_changed)
        self.zen_profile_combo.grid(row=2, column=1, padx=(5, 5), pady=5, sticky="ew")
        self.zen_browse_btn = ctk.CTkButton(
            self.path_frame, text="Browse", width=70, fg_color=self.accent_color, hover_color=self.accent_hover,
            command=self._browse_zen_path
        )
        self.zen_browse_btn.grid(row=2, column=2, padx=(0, 15), pady=5)

        # 2. Console Logs Box
        self.log_frame = ctk.CTkFrame(self.left_column, fg_color=self.bg_card)
        self.log_frame.grid(row=1, column=0, sticky="nsew", pady=5, padx=2)
        self.log_frame.grid_rowconfigure(1, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.log_frame,
            text="Migration Output logs",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, padx=15, pady=10, sticky="w")

        self.console_textbox = ctk.CTkTextbox(self.log_frame, font=ctk.CTkFont(family="Consolas", size=11))
        self.console_textbox.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.console_textbox.configure(state="disabled")

        # Right Column Frame
        self.right_column = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.right_column.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.right_column.grid_columnconfigure(0, weight=1)
        self.right_column.grid_rowconfigure(0, weight=1)  # Expand list box
        self.right_column.grid_rowconfigure(1, weight=0)  # Options card

        # 3. Spaces Selection Card
        self.spaces_frame = ctk.CTkFrame(self.right_column, fg_color=self.bg_card)
        self.spaces_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10), padx=2)
        self.spaces_frame.grid_columnconfigure(0, weight=1)
        self.spaces_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.spaces_frame,
            text="Select Arc Spaces to Migrate",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, padx=15, pady=10, sticky="w")

        self.spaces_scroll_frame = ctk.CTkScrollableFrame(self.spaces_frame, fg_color="#222222")
        self.spaces_scroll_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

        # 4. Migration Preferences
        self.options_frame = ctk.CTkFrame(self.right_column, fg_color=self.bg_card)
        self.options_frame.grid(row=1, column=0, sticky="ew", pady=5, padx=2)
        self.options_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.options_frame,
            text="Migration Preferences",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")

        self.opt_pinned_tabs = ctk.CTkCheckBox(self.options_frame, text="Migrate Pinned Tabs & Folders", fg_color=self.accent_color, hover_color=self.accent_hover)
        self.opt_pinned_tabs.grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.opt_pinned_tabs.select()

        self.opt_open_tabs = ctk.CTkCheckBox(self.options_frame, text="Migrate Open Tabs (Sessionstore)", fg_color=self.accent_color, hover_color=self.accent_hover)
        self.opt_open_tabs.grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.opt_open_tabs.select()

        self.opt_history = ctk.CTkCheckBox(self.options_frame, text="Migrate Browsing History", fg_color=self.accent_color, hover_color=self.accent_hover)
        self.opt_history.grid(row=3, column=0, padx=15, pady=5, sticky="w")
        self.opt_history.select()

        self.opt_containers = ctk.CTkCheckBox(self.options_frame, text="Assign Cookie-Isolated Containers", fg_color=self.accent_color, hover_color=self.accent_hover)
        self.opt_containers.grid(row=4, column=0, padx=15, pady=(5, 15), sticky="w")
        self.opt_containers.select()

        # --- FOOTER ---
        self.footer_frame = ctk.CTkFrame(self, corner_radius=0, height=70, fg_color="#1e1e1e")
        self.footer_frame.grid(row=2, column=0, sticky="ew")
        self.footer_frame.grid_columnconfigure(0, weight=1)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.footer_frame, height=8, progress_color=self.accent_color)
        self.progress_bar.grid(row=0, column=0, columnspan=3, sticky="ew", padx=20, pady=(10, 5))
        self.progress_bar.set(0)

        # Buttons
        self.dry_run_btn = ctk.CTkButton(
            self.footer_frame,
            text="🧪 Dry Run (Test)",
            width=140,
            fg_color="#444444",
            hover_color="#555555",
            command=self._on_dry_run_clicked
        )
        self.dry_run_btn.grid(row=1, column=1, padx=(0, 10), pady=(5, 15), sticky="e")

        self.migrate_btn = ctk.CTkButton(
            self.footer_frame,
            text="🚀 Start Migration",
            width=160,
            fg_color=self.accent_color,
            hover_color=self.accent_hover,
            font=ctk.CTkFont(weight="bold"),
            command=self._on_migrate_clicked
        )
        self.migrate_btn.grid(row=1, column=2, padx=(0, 20), pady=(5, 15), sticky="e")

        self.status_label = ctk.CTkLabel(
            self.footer_frame,
            text="Idle - Ready to scan systems.",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=1, column=0, padx=20, pady=(5, 15), sticky="w")

    def _setup_logging(self):
        # Configure logging to write to console textbox
        self.log_handler = GuiLogHandler(self.console_textbox)
        
        # Get root logger and add handler
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(self.log_handler)

    def _initialize_discovery(self):
        # Scan system for Arc and Zen
        self.logger = logging.getLogger("Arc2ZenApp")
        self.logger.info("Initializing system scan...")

        # Setup Arc Extractor & file detection
        self.arc_extractor = ArcPinnedTabExtractor()
        if self.arc_extractor.arc_sidebar_file.exists():
            self.arc_path_entry.delete(0, "end")
            self.arc_path_entry.insert(0, str(self.arc_extractor.arc_sidebar_file))
            self.logger.info(f"Auto-detected Arc Sidebar: {self.arc_extractor.arc_sidebar_file.name}")
        else:
            self.logger.warning("Arc StorableSidebar.json not found in default location.")

        # Setup Zen schema analyzer & profile detection
        self.zen_analyzer = ZenSchemaAnalyzer()
        self.discovered_zen_profiles = self.zen_analyzer.find_zen_profiles()
        
        if self.discovered_zen_profiles:
            profile_names = [p.name for p in self.discovered_zen_profiles]
            self.zen_profile_combo.configure(values=profile_names)
            self.zen_profile_combo.set(profile_names[0])
            self.selected_zen_profile_path = self.discovered_zen_profiles[0]
            self.logger.info(f"Auto-detected {len(self.discovered_zen_profiles)} Zen Profile(s). Selected: {profile_names[0]}")
        else:
            self.logger.warning("No Zen profiles found. Please browse manually.")

        # Trigger initial scan of Arc Sidebar contents
        self._scan_arc_spaces()

    def _scan_arc_spaces(self):
        # Clear existing spaces list in GUI
        for widget in self.spaces_scroll_frame.winfo_children():
            widget.destroy()
        self.space_checkboxes.clear()

        path_str = self.arc_path_entry.get().strip()
        if not path_str:
            return

        arc_file = Path(path_str)
        if not arc_file.exists():
            self.logger.error("Specified Arc Sidebar file does not exist.")
            return

        # Override path in extractor
        self.arc_extractor.arc_sidebar_file = arc_file

        try:
            self.discovered_arc_spaces = self.arc_extractor.extract_pinned_tabs()
            if not self.discovered_arc_spaces:
                self.logger.warning("No spaces found in Arc Sidebar configuration.")
                return

            self.logger.info(f"Scan complete. Found {len(self.discovered_arc_spaces)} Arc Spaces.")

            # Populates UI spaces checkbox list
            for space in self.discovered_arc_spaces:
                tab_count = len(space.pinned_tabs)
                open_count = len(space.open_tabs)
                folder_count = len(space.folders)
                icon = space.icon if space.icon else "📁"

                text = f"{icon} {space.space_name}\n({tab_count} pinned, {open_count} open, {folder_count} folders)"
                cb = ctk.CTkCheckBox(
                    self.spaces_scroll_frame,
                    text=text,
                    font=ctk.CTkFont(size=12),
                    fg_color=self.accent_color,
                    hover_color=self.accent_hover
                )
                cb.pack(fill="x", padx=10, pady=6, anchor="w")
                cb.select()  # Checked by default
                self.space_checkboxes[space.space_name] = cb

        except Exception as e:
            self.logger.exception(f"Error parsing Arc Sidebar: {e}")

    def _browse_arc_path(self):
        file_path = filedialog.askopenfilename(
            title="Select Arc StorableSidebar.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            self.arc_path_entry.delete(0, "end")
            self.arc_path_entry.insert(0, file_path)
            self._scan_arc_spaces()

    def _browse_zen_path(self):
        dir_path = filedialog.askdirectory(title="Select Zen Profile Directory")
        if dir_path:
            profile_path = Path(dir_path)
            self.selected_zen_profile_path = profile_path
            self.zen_profile_combo.configure(values=[profile_path.name])
            self.zen_profile_combo.set(profile_path.name)
            self.logger.info(f"Manually set Zen Profile: {profile_path}")

    def _on_zen_profile_changed(self, value):
        for profile in self.discovered_zen_profiles:
            if profile.name == value:
                self.selected_zen_profile_path = profile
                self.logger.info(f"Switched to Zen profile: {value}")
                break

    def _get_active_migrators_and_data(self) -> Optional[dict]:
        # Perform validation checks
        arc_path = self.arc_path_entry.get().strip()
        if not arc_path or not Path(arc_path).exists():
            messagebox.showerror("Error", "Invalid Arc Sidebar path selected.")
            return None

        if not self.selected_zen_profile_path or not self.selected_zen_profile_path.exists():
            messagebox.showerror("Error", "No valid Zen profile directory selected.")
            return None

        # Gather checked spaces
        selected_space_names = [name for name, cb in self.space_checkboxes.items() if cb.get()]
        if not selected_space_names:
            messagebox.showerror("Error", "Please select at least one Arc Space to migrate.")
            return None

        # Filter discovered spaces based on user selection
        filtered_spaces = [space for space in self.discovered_arc_spaces if space.space_name in selected_space_names]
        
        # Determine options
        options = {
            "migrate_pinned": bool(self.opt_pinned_tabs.get()),
            "migrate_open": bool(self.opt_open_tabs.get()),
            "migrate_history": bool(self.opt_history.get()),
            "assign_containers": bool(self.opt_containers.get())
        }

        # Check if browser processes are running
        running_browsers = self._check_browsers_running()
        if running_browsers:
            running_str = " and ".join(running_browsers)
            msg = f"❌ ERROR: {running_str} browser(s) are currently running!\n\nPlease close them completely before migrating. Running browsers lock configuration databases, causing migration failures."
            self.logger.error(msg)
            messagebox.showwarning("Browsers Running", msg)
            return None

        return {
            "spaces": filtered_spaces,
            "profile_path": self.selected_zen_profile_path,
            "options": options
        }

    def _check_browsers_running(self) -> List[str]:
        running = []
        try:
            import subprocess
            # Simple tasks check on Windows
            if os.name == "nt":
                output = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq Arc.exe", "/FO", "CSV"],
                    capture_output=True, text=True
                ).stdout
                if "Arc.exe" in output:
                    running.append("Arc")

                output_zen = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq zen.exe", "/FO", "CSV"],
                    capture_output=True, text=True
                ).stdout
                if "zen.exe" in output_zen:
                    running.append("Zen")
        except Exception:
            pass
        return running

    def _on_dry_run_clicked(self):
        data = self._get_active_migrators_and_data()
        if not data:
            return

        self._lock_ui()
        self.progress_bar.set(0.2)
        self.status_label.configure(text="Running dry run test...", text_color=self.accent_color)
        
        threading.Thread(target=self._run_migration_thread, args=(data, True), daemon=True).start()

    def _on_migrate_clicked(self):
        data = self._get_active_migrators_and_data()
        if not data:
            return

        confirm = messagebox.askyesno(
            "Confirm Migration",
            "This will modify your Zen profile files.\nA backup of your Zen profile data will be created automatically.\n\nAre you sure you want to proceed?"
        )
        if not confirm:
            return

        self._lock_ui()
        self.progress_bar.set(0.2)
        self.status_label.configure(text="Migrating data...", text_color=self.accent_color)
        
        threading.Thread(target=self._run_migration_thread, args=(data, False), daemon=True).start()

    def _lock_ui(self):
        self.dry_run_btn.configure(state="disabled")
        self.migrate_btn.configure(state="disabled")
        self.arc_browse_btn.configure(state="disabled")
        self.zen_browse_btn.configure(state="disabled")
        self.zen_profile_combo.configure(state="disabled")
        for cb in self.space_checkboxes.values():
            cb.configure(state="disabled")

    def _unlock_ui(self):
        self.dry_run_btn.configure(state="normal")
        self.migrate_btn.configure(state="normal")
        self.arc_browse_btn.configure(state="normal")
        self.zen_browse_btn.configure(state="normal")
        self.zen_profile_combo.configure(state="normal")
        for cb in self.space_checkboxes.values():
            cb.configure(state="normal")

    def _run_migration_thread(self, data: dict, dry_run: bool):
        logger = logging.getLogger("MigratorWorker")
        spaces: List[ArcSpace] = data["spaces"]
        profile_path: Path = data["profile_path"]
        opts: dict = data["options"]

        mode_str = "DRY RUN" if dry_run else "MIGRATION"
        logger.info(f"--- STARTING {mode_str} ---")
        
        try:
            # Step 1: Prepare export data model (matching format required by importers)
            logger.info("Step 1: Structuring export data model...")
            
            # Serialize spaces to matches JSON structure
            export_data = {
                "spaces": []
            }
            
            for space in spaces:
                space_dict = {
                    "space_id": space.space_id,
                    "space_name": space.space_name,
                    "pinned_tabs": [t.to_dict() for t in space.pinned_tabs],
                    "folders": [
                        {
                            "folder_id": f.folder_id,
                            "title": f.title,
                            "parent_id": f.parent_id,
                            "space_id": f.space_id,
                            "children_ids": f.children_ids,
                            "index": f.index
                        } for f in space.folders
                    ],
                    "open_tabs": [t.to_dict() for t in space.open_tabs]
                }
                export_data["spaces"].append(space_dict)

            # Step 2: Handle Zen profiles setup
            zen_profile = ZenProfile(name=profile_path.name, path=profile_path)
            self.progress_bar.set(0.4)

            # Step 3: Create Zen containers/workspaces (cookie isolation)
            container_mappings = {}
            if opts["assign_containers"] and not opts["migrate_pinned"]:
                logger.warning("Containers mapping skipped since 'Migrate Pinned Tabs' is disabled.")
            
            if opts["assign_containers"] and opts["migrate_pinned"]:
                logger.info("Step 2: Configuring spaces as container workspaces...")
                space_importer = ZenSpaceImporter(zen_profile)
                container_mappings = space_importer.import_arc_spaces_as_containers(export_data, dry_run=dry_run)
            else:
                logger.info("Step 2: Assigning workspaces to standard default containers...")
                for space in export_data["spaces"]:
                    container_mappings[space["space_name"]] = 0 # default context

            self.progress_bar.set(0.6)

            # Step 4: Import pinned tabs to Zen modern sessions format (zen-sessions.jsonlz4)
            sessions_success = True
            if opts["migrate_pinned"]:
                logger.info("Step 3: Exporting pinned tabs into Zen session store...")
                sessions_importer = ZenSessionsImporter(profile_path)
                sessions_success = sessions_importer.import_arc_data(export_data, container_mappings, dry_run=dry_run)

                # Export backup bookmarks
                logger.info("Step 3b: Creating fallback bookmarks directory...")
                bookmark_importer = ZenBookmarkImporter(profile_path)
                bookmark_importer.import_arc_bookmarks(export_data, dry_run=dry_run)

            self.progress_bar.set(0.7)

            # Step 5: Import browsing history
            history_success = True
            if opts["migrate_history"]:
                logger.info("Step 4: Merging Chromium browsing history...")
                try:
                    history_migrator = ArcHistoryMigrator(profile_path)
                    history_stats = history_migrator.migrate(dry_run=dry_run)
                    if not dry_run:
                        logger.info(f"Successfully migrated {history_stats['inserted']} history items.")
                except Exception as ex:
                    logger.error(f"Browsing history migration failed: {ex}")
                    history_success = False

            self.progress_bar.set(0.8)

            # Step 6: Import open tabs
            session_success = True
            total_open = sum(len(s.open_tabs) for s in spaces)
            if opts["migrate_open"] and total_open > 0:
                logger.info("Step 5: Writing open tabs into browser sessionstore...")
                try:
                    session_manager = ZenSessionstoreManager(profile_path)
                    session_success = session_manager.create_workspaces_with_tabs(export_data, container_mappings, dry_run=dry_run)
                except Exception as ex:
                    logger.error(f"Open tabs migration failed: {ex}")
                    session_success = False

            self.progress_bar.set(1.0)
            
            # Final Status Report
            if dry_run:
                self.status_label.configure(text="Dry run complete. No modifications made.", text_color="green")
                messagebox.showinfo("Dry Run Complete", "The dry run finished successfully!\nAll configurations loaded and parsed. Check the logs for validation details.")
            else:
                self.status_label.configure(text="Migration successful! Restart Zen.", text_color="green")
                messagebox.showinfo(
                    "Migration Complete",
                    f"Success! Migrated your chosen Arc spaces.\n\n"
                    f"🎉 Pinned Tabs: {'Yes' if sessions_success else 'No'}\n"
                    f"🔄 Open Tabs: {'Yes' if session_success else 'No'}\n"
                    f"📜 History: {'Yes' if history_success else 'No'}\n\n"
                    f"⚠️ Please completely close and restart your Zen browser to load the new session."
                )

        except Exception as e:
            logger.exception(f"Migration thread crashed: {e}")
            self.status_label.configure(text="Failed - Error during execution.", text_color="red")
            messagebox.showerror("Migration Error", f"An unexpected error occurred: {e}\nCheck the logs widget for traceback details.")

        finally:
            self._unlock_ui()


def main():
    app = Arc2ZenApp()
    app.mainloop()


if __name__ == "__main__":
    main()
