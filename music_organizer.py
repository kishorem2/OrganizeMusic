import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import hashlib
from pathlib import Path
import shutil
from collections import defaultdict

class MusicOrganizer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Music Organizer")
        self.root.geometry("800x600")

        # Music file extensions
        self.music_extensions = {'.mp3', '.mp4', '.m4a', '.wav', '.flac', '.aac', '.ogg'}

        # Progress tracking
        self.progress_file = "music_organizer_progress.json"
        self.source_folders = []
        self.all_songs = []
        self.processed_songs = set()
        self.current_index = 0
        self.organization_plan = {}  # song_path -> destination_folder
        self.duplicates = defaultdict(list)  # file_hash -> list of file_paths

        # Destination folder on desktop
        self.desktop_path = Path.home() / "Desktop"
        self.organized_music_path = self.desktop_path / "Organized_Music"

        self.setup_ui()
        self.load_progress()

    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Step 1: Select source folders
        ttk.Label(main_frame, text="Step 1: Select Source Folders", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=3, pady=10)

        ttk.Button(main_frame, text="Browse Folders", command=self.browse_folders).grid(row=1, column=0, padx=5)
        ttk.Button(main_frame, text="Scan for Music", command=self.scan_music).grid(row=1, column=1, padx=5)

        self.folders_label = ttk.Label(main_frame, text="No folders selected", wraplength=400)
        self.folders_label.grid(row=2, column=0, columnspan=3, pady=5)

        # Step 2: Song organization
        ttk.Separator(main_frame, orient='horizontal').grid(row=3, column=0, columnspan=3, sticky="ew", pady=20)
        ttk.Label(main_frame, text="Step 2: Organize Songs", font=("Arial", 12, "bold")).grid(row=4, column=0, columnspan=3, pady=10)

        # Progress info
        self.progress_label = ttk.Label(main_frame, text="")
        self.progress_label.grid(row=5, column=0, columnspan=3, pady=5)

        # Current song info
        self.song_frame = ttk.LabelFrame(main_frame, text="Current Song", padding="10")
        self.song_frame.grid(row=6, column=0, columnspan=3, pady=10, sticky="ew")

        self.song_name_label = ttk.Label(self.song_frame, text="", font=("Arial", 11), wraplength=600)
        self.song_name_label.grid(row=0, column=0, columnspan=3, pady=5)

        self.song_path_label = ttk.Label(self.song_frame, text="", font=("Arial", 9), foreground="gray", wraplength=600)
        self.song_path_label.grid(row=1, column=0, columnspan=3, pady=5)

        # Organization options
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=7, column=0, columnspan=3, pady=10)

        ttk.Button(options_frame, text="Add to Existing Folder", command=self.add_to_existing).grid(row=0, column=0, padx=5)
        ttk.Button(options_frame, text="Create New Folder", command=self.create_new_folder).grid(row=0, column=1, padx=5)
        ttk.Button(options_frame, text="Skip Song", command=self.skip_song).grid(row=0, column=2, padx=5)

        # Navigation
        nav_frame = ttk.Frame(main_frame)
        nav_frame.grid(row=8, column=0, columnspan=3, pady=10)

        ttk.Button(nav_frame, text="Previous", command=self.previous_song).grid(row=0, column=0, padx=5)
        ttk.Button(nav_frame, text="Next", command=self.next_song).grid(row=0, column=1, padx=5)

        # Final actions
        ttk.Separator(main_frame, orient='horizontal').grid(row=9, column=0, columnspan=3, sticky="ew", pady=20)

        final_frame = ttk.Frame(main_frame)
        final_frame.grid(row=10, column=0, columnspan=3, pady=10)

        ttk.Button(final_frame, text="Save Progress", command=self.save_progress).grid(row=0, column=0, padx=5)
        ttk.Button(final_frame, text="Execute Moves", command=self.execute_moves).grid(row=0, column=1, padx=5)
        ttk.Button(final_frame, text="View Plan", command=self.view_plan).grid(row=0, column=2, padx=5)

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

    def browse_folders(self):
        folder = filedialog.askdirectory(title="Select a folder containing music files")
        if folder:
            if folder not in self.source_folders:
                self.source_folders.append(folder)
                self.update_folders_display()

    def update_folders_display(self):
        if self.source_folders:
            folders_text = f"Selected {len(self.source_folders)} folder(s):\n" + "\n".join(self.source_folders)
            self.folders_label.config(text=folders_text)
        else:
            self.folders_label.config(text="No folders selected")

    def scan_music(self):
        if not self.source_folders:
            messagebox.showwarning("Warning", "Please select source folders first!")
            return

        self.all_songs = []
        self.duplicates.clear()
        file_hashes = {}

        progress_window = tk.Toplevel(self.root)
        progress_window.title("Scanning...")
        progress_window.geometry("400x100")
        progress_label = ttk.Label(progress_window, text="Scanning for music files...")
        progress_label.pack(pady=20)

        for folder in self.source_folders:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in self.music_extensions):
                        file_path = os.path.join(root, file)
                        self.all_songs.append(file_path)

                        # Check for duplicates
                        file_hash = self.get_file_hash(file_path)
                        if file_hash in file_hashes:
                            self.duplicates[file_hash].append(file_path)
                            if len(self.duplicates[file_hash]) == 1:
                                self.duplicates[file_hash].insert(0, file_hashes[file_hash])
                        else:
                            file_hashes[file_hash] = file_path

        progress_window.destroy()

        # Show scan results
        message = f"Found {len(self.all_songs)} music files"
        if self.duplicates:
            message += f"\nFound {len(self.duplicates)} sets of duplicate files"
            if messagebox.askyesno("Duplicates Found", f"{message}\n\nWould you like to see the duplicates?"):
                self.show_duplicates()

        messagebox.showinfo("Scan Complete", message)
        self.update_progress_display()
        self.show_current_song()

    def get_file_hash(self, file_path):
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        except Exception:
            return None
        return hash_md5.hexdigest()

    def show_duplicates(self):
        dup_window = tk.Toplevel(self.root)
        dup_window.title("Duplicate Files")
        dup_window.geometry("800x400")

        text_widget = tk.Text(dup_window, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(dup_window, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        for i, (file_hash, file_list) in enumerate(self.duplicates.items(), 1):
            text_widget.insert(tk.END, f"Duplicate Set {i}:\n")
            for file_path in file_list:
                text_widget.insert(tk.END, f"  {file_path}\n")
            text_widget.insert(tk.END, "\n")

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def update_progress_display(self):
        if self.all_songs:
            total = len(self.all_songs)
            processed = len(self.processed_songs)
            self.progress_label.config(text=f"Progress: {processed}/{total} songs processed ({self.current_index + 1} of {total})")
        else:
            self.progress_label.config(text="No songs loaded")

    def show_current_song(self):
        if not self.all_songs or self.current_index >= len(self.all_songs):
            self.song_name_label.config(text="No more songs")
            self.song_path_label.config(text="")
            return

        current_song = self.all_songs[self.current_index]
        song_name = os.path.basename(current_song)

        self.song_name_label.config(text=f"Song: {song_name}")
        self.song_path_label.config(text=f"Path: {current_song}")

    def add_to_existing(self):
        if not self.organized_music_path.exists():
            messagebox.showinfo("Info", "No organized folders exist yet. Use 'Create New Folder' first.")
            return

        existing_folders = [d.name for d in self.organized_music_path.iterdir() if d.is_dir()]
        if not existing_folders:
            messagebox.showinfo("Info", "No organized folders exist yet. Use 'Create New Folder' first.")
            return

        # Create selection dialog
        self.select_folder_dialog(existing_folders)

    def select_folder_dialog(self, folders):
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Folder")
        dialog.geometry("400x300")
        dialog.grab_set()

        ttk.Label(dialog, text="Select a folder:").pack(pady=10)

        listbox = tk.Listbox(dialog)
        for folder in folders:
            listbox.insert(tk.END, folder)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_folder = folders[selection[0]]
                self.assign_to_folder(selected_folder)
                dialog.destroy()

        ttk.Button(dialog, text="Select", command=on_select).pack(pady=10)

    def create_new_folder(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Folder")
        dialog.geometry("400x150")
        dialog.grab_set()

        ttk.Label(dialog, text="Enter folder name:").pack(pady=10)

        entry = ttk.Entry(dialog, width=40)
        entry.pack(pady=10)
        entry.focus()

        def on_create():
            folder_name = entry.get().strip()
            if folder_name:
                self.assign_to_folder(folder_name)
                dialog.destroy()
            else:
                messagebox.showwarning("Warning", "Please enter a folder name")

        ttk.Button(dialog, text="Create", command=on_create).pack(pady=10)
        entry.bind('<Return>', lambda e: on_create())

    def assign_to_folder(self, folder_name):
        if self.current_index < len(self.all_songs):
            current_song = self.all_songs[self.current_index]
            self.organization_plan[current_song] = folder_name
            self.processed_songs.add(current_song)
            self.next_song()

    def skip_song(self):
        if self.current_index < len(self.all_songs):
            current_song = self.all_songs[self.current_index]
            self.processed_songs.add(current_song)
            self.next_song()

    def next_song(self):
        if self.current_index < len(self.all_songs) - 1:
            self.current_index += 1
            while (self.current_index < len(self.all_songs) and
                   self.all_songs[self.current_index] in self.processed_songs):
                self.current_index += 1

        self.update_progress_display()
        self.show_current_song()

    def previous_song(self):
        if self.current_index > 0:
            self.current_index -= 1

        self.update_progress_display()
        self.show_current_song()

    def save_progress(self):
        progress_data = {
            'source_folders': self.source_folders,
            'all_songs': self.all_songs,
            'processed_songs': list(self.processed_songs),
            'current_index': self.current_index,
            'organization_plan': self.organization_plan,
            'duplicates': dict(self.duplicates)
        }

        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
            messagebox.showinfo("Success", "Progress saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save progress: {str(e)}")

    def load_progress(self):
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    progress_data = json.load(f)

                self.source_folders = progress_data.get('source_folders', [])
                self.all_songs = progress_data.get('all_songs', [])
                self.processed_songs = set(progress_data.get('processed_songs', []))
                self.current_index = progress_data.get('current_index', 0)
                self.organization_plan = progress_data.get('organization_plan', {})
                self.duplicates = defaultdict(list, progress_data.get('duplicates', {}))

                self.update_folders_display()
                self.update_progress_display()
                self.show_current_song()

                if self.all_songs:
                    messagebox.showinfo("Progress Loaded", f"Loaded progress: {len(self.processed_songs)}/{len(self.all_songs)} songs processed")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load progress: {str(e)}")

    def view_plan(self):
        if not self.organization_plan:
            messagebox.showinfo("Info", "No organization plan created yet")
            return

        plan_window = tk.Toplevel(self.root)
        plan_window.title("Organization Plan")
        plan_window.geometry("800x400")

        text_widget = tk.Text(plan_window, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(plan_window, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        folder_groups = defaultdict(list)
        for song_path, folder_name in self.organization_plan.items():
            folder_groups[folder_name].append(song_path)

        for folder_name, songs in folder_groups.items():
            text_widget.insert(tk.END, f"Folder: {folder_name} ({len(songs)} songs)\n")
            for song in songs:
                text_widget.insert(tk.END, f"  {os.path.basename(song)}\n")
            text_widget.insert(tk.END, "\n")

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def execute_moves(self):
        if not self.organization_plan:
            messagebox.showwarning("Warning", "No organization plan to execute")
            return

        if not messagebox.askyesno("Confirm", f"This will move {len(self.organization_plan)} files. Continue?"):
            return

        # Create organized music directory
        self.organized_music_path.mkdir(exist_ok=True)

        success_count = 0
        error_count = 0
        errors = []

        for song_path, folder_name in self.organization_plan.items():
            try:
                # Create destination folder
                dest_folder = self.organized_music_path / folder_name
                dest_folder.mkdir(exist_ok=True)

                # Move file
                song_name = os.path.basename(song_path)
                dest_path = dest_folder / song_name

                # Handle duplicate names
                counter = 1
                while dest_path.exists():
                    name, ext = os.path.splitext(song_name)
                    dest_path = dest_folder / f"{name}_{counter}{ext}"
                    counter += 1

                shutil.move(song_path, dest_path)
                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"{song_path}: {str(e)}")

        # Show results
        message = f"Move completed!\nSuccess: {success_count}\nErrors: {error_count}"
        if errors:
            message += f"\n\nFirst few errors:\n" + "\n".join(errors[:5])

        messagebox.showinfo("Move Complete", message)

        # Clear the plan after successful execution
        if error_count == 0:
            self.organization_plan.clear()
            self.save_progress()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MusicOrganizer()
    app.run()