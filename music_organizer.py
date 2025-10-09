import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import hashlib
from pathlib import Path
import shutil
from collections import defaultdict
import pygame
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen import File as MutagenFile

class MusicOrganizer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Music Organizer")
        self.root.geometry("900x800")

        # Music file extensions
        self.music_extensions = {'.mp3', '.mp4', '.m4a', '.wav', '.flac', '.aac', '.ogg'}

        # Progress tracking
        self.progress_file = "music_organizer_progress.json"
        self.source_folders = []
        self.all_songs = []
        self.processed_songs = set()
        self.current_index = 0
        self.organization_plan = {}  # song_path -> destination_folder
        self.created_folders = set()  # Track folders created during organization
        self.duplicates = defaultdict(list)  # file_hash -> list of file_paths

        # Multi-selection tracking
        self.selected_songs = set()  # Track selected songs
        self.song_checkboxes = {}  # song_path -> checkbox_var
        self.last_selected_index = None  # For shift+click range selection

        # Destination folder (initially on desktop, but user can change)
        self.desktop_path = Path.home() / "Desktop"
        self.destination_base_path = self.desktop_path  # Default to desktop
        self.organized_music_path = self.destination_base_path / "Organized_Music"

        # Audio playback
        pygame.mixer.init()
        self.currently_playing = None
        self.is_paused = False
        self.song_length = 0
        self.seek_update_job = None
        self._play_start_time = 0
        self.seeking = False

        # Metadata cache
        self.song_metadata = {}  # song_path -> {artist, album, genre, title}

        # Grouping/sorting options
        self.sort_mode = "filename"  # filename, artist, album

        self.setup_ui()
        self.load_progress()

    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Step 1: Select source folders and destination
        ttk.Label(main_frame, text="Step 1: Select Source Folders and Destination", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=3, pady=10)

        ttk.Button(main_frame, text="Browse Folders", command=self.browse_folders).grid(row=1, column=0, padx=5)
        ttk.Button(main_frame, text="Choose Destination", command=self.choose_destination).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Scan for Music", command=self.scan_music).grid(row=1, column=2, padx=5)

        # Folder management buttons
        folder_mgmt_frame = ttk.Frame(main_frame)
        folder_mgmt_frame.grid(row=1, column=3, columnspan=2, padx=5)
        ttk.Button(folder_mgmt_frame, text="Remove Folder", command=self.remove_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(folder_mgmt_frame, text="Clear All Folders", command=self.clear_all_folders).pack(side=tk.LEFT, padx=2)

        self.folders_label = ttk.Label(main_frame, text="No folders selected", wraplength=400)
        self.folders_label.grid(row=2, column=0, columnspan=3, pady=5)

        self.destination_label = ttk.Label(main_frame, text=f"Destination: {self.organized_music_path}", wraplength=600, foreground="blue")
        self.destination_label.grid(row=3, column=0, columnspan=3, pady=5)

        # Step 2: Song organization
        ttk.Separator(main_frame, orient='horizontal').grid(row=4, column=0, columnspan=3, sticky="ew", pady=20)
        ttk.Label(main_frame, text="Step 2: Organize Songs", font=("Arial", 12, "bold")).grid(row=5, column=0, columnspan=3, pady=10)

        # Progress info
        self.progress_label = ttk.Label(main_frame, text="")
        self.progress_label.grid(row=6, column=0, columnspan=3, pady=5)

        # Selection controls
        selection_controls_frame = ttk.Frame(main_frame)
        selection_controls_frame.grid(row=7, column=0, columnspan=3, pady=5)

        ttk.Button(selection_controls_frame, text="Select All", command=self.select_all_songs).grid(row=0, column=0, padx=5)
        ttk.Button(selection_controls_frame, text="Deselect All", command=self.deselect_all_songs).grid(row=0, column=1, padx=5)
        self.selection_count_label = ttk.Label(selection_controls_frame, text="0 songs selected")
        self.selection_count_label.grid(row=0, column=2, padx=10)

        # Audio playback controls
        playback_frame = ttk.LabelFrame(main_frame, text="Audio Preview", padding="10")
        playback_frame.grid(row=7, column=3, columnspan=2, pady=5, padx=10, sticky="ew")

        self.now_playing_label = ttk.Label(playback_frame, text="No song playing", foreground="gray")
        self.now_playing_label.grid(row=0, column=0, columnspan=3, pady=(0, 5))

        # Playback buttons
        button_frame = ttk.Frame(playback_frame)
        button_frame.grid(row=1, column=0, columnspan=3, pady=(0, 5))
        ttk.Button(button_frame, text="▶ Play", command=self.play_selected, width=8).grid(row=0, column=0, padx=2)
        ttk.Button(button_frame, text="⏸ Pause", command=self.pause_audio, width=8).grid(row=0, column=1, padx=2)
        ttk.Button(button_frame, text="⏹ Stop", command=self.stop_audio, width=8).grid(row=0, column=2, padx=2)

        # Seek bar and time display
        seek_frame = ttk.Frame(playback_frame)
        seek_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(5, 0))

        self.time_label = ttk.Label(seek_frame, text="0:00", width=6)
        self.time_label.grid(row=0, column=0, padx=(0, 5))

        self.seek_bar = ttk.Scale(seek_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_seek)
        self.seek_bar.grid(row=0, column=1, sticky="ew", padx=5)
        self.seek_bar.bind("<ButtonPress-1>", self.on_seek_start)
        self.seek_bar.bind("<ButtonRelease-1>", self.on_seek_end)

        self.duration_label = ttk.Label(seek_frame, text="0:00", width=6)
        self.duration_label.grid(row=0, column=2, padx=(5, 0))

        seek_frame.columnconfigure(1, weight=1)
        playback_frame.columnconfigure(0, weight=1)

        # Sorting controls
        sorting_frame = ttk.Frame(main_frame)
        sorting_frame.grid(row=7, column=5, columnspan=2, pady=5, padx=10)

        ttk.Label(sorting_frame, text="Sort by:").grid(row=0, column=0, padx=5)
        self.sort_var = tk.StringVar(value="filename")
        sort_dropdown = ttk.Combobox(sorting_frame, textvariable=self.sort_var, values=["filename", "artist", "album"], state="readonly", width=12)
        sort_dropdown.grid(row=0, column=1, padx=5)
        sort_dropdown.bind("<<ComboboxSelected>>", lambda e: self.populate_song_list())

        # Song list frame
        self.song_list_frame = ttk.LabelFrame(main_frame, text="Songs to Organize", padding="10")
        self.song_list_frame.grid(row=8, column=0, columnspan=3, pady=10, sticky="ew")

        # Create scrollable frame for song list
        self.setup_song_list_widget()

        # Organization options
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=9, column=0, columnspan=3, pady=10)

        ttk.Button(options_frame, text="Add Selected to Existing Folder", command=self.add_selected_to_existing).grid(row=0, column=0, padx=5)
        ttk.Button(options_frame, text="Add Selected to New Folder", command=self.create_new_folder_for_selected).grid(row=0, column=1, padx=5)
        ttk.Button(options_frame, text="Skip Selected", command=self.skip_selected_songs).grid(row=0, column=2, padx=5)

        # Final actions
        ttk.Separator(main_frame, orient='horizontal').grid(row=10, column=0, columnspan=3, sticky="ew", pady=20)

        final_frame = ttk.Frame(main_frame)
        final_frame.grid(row=11, column=0, columnspan=3, pady=10)

        ttk.Button(final_frame, text="Save Progress", command=self.save_progress).grid(row=0, column=0, padx=5)
        ttk.Button(final_frame, text="Execute Moves", command=self.execute_moves).grid(row=0, column=1, padx=5)
        ttk.Button(final_frame, text="View Plan", command=self.view_plan).grid(row=0, column=2, padx=5)

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(8, weight=1)  # Make song list frame expandable

    def setup_song_list_widget(self):
        # Create canvas and scrollbar for scrollable song list
        canvas = tk.Canvas(self.song_list_frame, height=200)
        scrollbar = ttk.Scrollbar(self.song_list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas = canvas
        self.song_list_scrollbar = scrollbar

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

    def remove_folder(self):
        if not self.source_folders:
            messagebox.showwarning("Warning", "No folders to remove!")
            return

        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Remove Folder")
        dialog.geometry("600x300")
        dialog.grab_set()

        ttk.Label(dialog, text="Select a folder to remove:").pack(pady=10)

        listbox = tk.Listbox(dialog, width=80)
        for folder in self.source_folders:
            listbox.insert(tk.END, folder)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def on_remove():
            selection = listbox.curselection()
            if selection:
                selected_folder = self.source_folders[selection[0]]
                self.source_folders.remove(selected_folder)

                # Remove songs from this folder from all_songs, processed_songs, and organization_plan
                songs_to_remove = [song for song in self.all_songs if song.startswith(selected_folder)]

                for song in songs_to_remove:
                    self.all_songs.remove(song)
                    self.processed_songs.discard(song)
                    self.selected_songs.discard(song)
                    if song in self.organization_plan:
                        del self.organization_plan[song]

                self.update_folders_display()
                self.update_progress_display()
                self.populate_song_list()

                messagebox.showinfo("Success", f"Removed folder and {len(songs_to_remove)} songs:\n{selected_folder}")
                dialog.destroy()

        ttk.Button(dialog, text="Remove", command=on_remove).pack(pady=10)

    def clear_all_folders(self):
        if not self.source_folders:
            messagebox.showwarning("Warning", "No folders to clear!")
            return

        # Warn if there's an active organization plan
        warning_msg = f"Clear all {len(self.source_folders)} selected folder(s)?\n\n"
        if self.organization_plan:
            warning_msg += f"WARNING: You have {len(self.organization_plan)} songs in your organization plan that haven't been moved yet!\n\n"
        warning_msg += "This will:\n- Clear all source folders\n- Clear all songs from the list\n- Clear the organization plan\n\nYour already organized music files will NOT be affected.\n\nContinue?"

        if messagebox.askyesno("Confirm", warning_msg):
            # Clear all songs and related data
            total_songs = len(self.all_songs)
            self.source_folders.clear()
            self.all_songs.clear()
            self.processed_songs.clear()
            self.selected_songs.clear()
            self.organization_plan.clear()
            self.current_index = 0

            self.update_folders_display()
            self.update_progress_display()
            self.populate_song_list()

            messagebox.showinfo("Success", f"Cleared all folders and {total_songs} songs!\n\nRemember to save progress if you want to keep this cleared state.")

    def choose_destination(self):
        destination = filedialog.askdirectory(title="Choose destination for organized music")
        if destination:
            self.destination_base_path = Path(destination)
            self.organized_music_path = self.destination_base_path / "Organized_Music"
            self.destination_label.config(text=f"Destination: {self.organized_music_path}")
            messagebox.showinfo("Destination Set", f"Music will be organized to:\n{self.organized_music_path}")

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
        self.populate_song_list()

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
            remaining = total - processed
            self.progress_label.config(text=f"Progress: {processed}/{total} songs processed, {remaining} remaining")
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

    def populate_song_list(self):
        # Clear existing checkboxes
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.song_checkboxes.clear()
        self.selected_songs.clear()

        # Get unprocessed songs
        unprocessed_songs = [song for song in self.all_songs if song not in self.processed_songs]

        # Sort songs based on selected mode
        sort_mode = self.sort_var.get() if hasattr(self, 'sort_var') else "filename"
        unprocessed_songs = self.sort_songs(unprocessed_songs, sort_mode)

        # Create checkbox for each unprocessed song
        for i, song_path in enumerate(unprocessed_songs):
            song_name = os.path.basename(song_path)

            # Get metadata for this song
            metadata = self.get_song_metadata(song_path)

            # Create frame for this song
            song_frame = ttk.Frame(self.scrollable_frame)
            song_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=2)

            # Create checkbox variable
            var = tk.BooleanVar()
            self.song_checkboxes[song_path] = var

            # Create checkbox
            checkbox = ttk.Checkbutton(
                song_frame,
                variable=var,
                command=lambda sp=song_path: self.on_checkbox_change(sp)
            )
            checkbox.grid(row=0, column=0, sticky="w")

            # Create clickable label for song name with metadata
            display_text = song_name
            if metadata['artist'] or metadata['title']:
                title = metadata['title'] or song_name
                artist = metadata['artist'] or 'Unknown'
                display_text = f"{artist} - {title}"

            song_label = ttk.Label(song_frame, text=display_text, width=50, anchor="w")
            song_label.grid(row=0, column=1, sticky="ew", padx=(5, 0))

            # Display genre if available
            if metadata['genre']:
                genre_label = ttk.Label(song_frame, text=f"[{metadata['genre']}]", foreground="blue", width=15, anchor="w")
                genre_label.grid(row=0, column=2, sticky="w", padx=(5, 0))

            # Display album if available and not in artist mode
            if metadata['album'] and sort_mode != "album":
                album_label = ttk.Label(song_frame, text=f"({metadata['album']})", foreground="gray", width=20, anchor="w")
                album_label.grid(row=0, column=3, sticky="w", padx=(5, 0))

            # Bind click events for Ctrl/Shift selection
            song_label.bind("<Button-1>", lambda e, idx=i, sp=song_path: self.on_song_click(e, idx, sp))
            song_label.bind("<Double-Button-1>", lambda e, sp=song_path: self.play_song(sp))
            song_frame.bind("<Button-1>", lambda e, idx=i, sp=song_path: self.on_song_click(e, idx, sp))

            # Configure column weight
            song_frame.columnconfigure(1, weight=1)

        # Configure scrollable frame
        self.scrollable_frame.columnconfigure(0, weight=1)
        self.update_selection_count()

    def on_checkbox_change(self, song_path):
        var = self.song_checkboxes[song_path]
        if var.get():
            self.selected_songs.add(song_path)
        else:
            self.selected_songs.discard(song_path)
        self.update_selection_count()

    def on_song_click(self, event, index, song_path):
        # Handle Ctrl+click and Shift+click
        var = self.song_checkboxes[song_path]

        if event.state & 0x4:  # Ctrl key
            # Toggle selection
            var.set(not var.get())
            self.on_checkbox_change(song_path)
            self.last_selected_index = index

        elif event.state & 0x1:  # Shift key
            # Range selection
            if self.last_selected_index is not None:
                start_idx = min(self.last_selected_index, index)
                end_idx = max(self.last_selected_index, index)

                unprocessed_songs = [song for song in self.all_songs if song not in self.processed_songs]

                for i in range(start_idx, end_idx + 1):
                    if i < len(unprocessed_songs):
                        range_song = unprocessed_songs[i]
                        if range_song in self.song_checkboxes:
                            self.song_checkboxes[range_song].set(True)
                            self.selected_songs.add(range_song)

                self.update_selection_count()
            else:
                # First selection
                var.set(True)
                self.on_checkbox_change(song_path)
                self.last_selected_index = index
        else:
            # Regular click - toggle selection
            var.set(not var.get())
            self.on_checkbox_change(song_path)
            self.last_selected_index = index

    def select_all_songs(self):
        for song_path, var in self.song_checkboxes.items():
            var.set(True)
            self.selected_songs.add(song_path)
        self.update_selection_count()

    def deselect_all_songs(self):
        for song_path, var in self.song_checkboxes.items():
            var.set(False)
        self.selected_songs.clear()
        self.update_selection_count()

    def update_selection_count(self):
        count = len(self.selected_songs)
        if count == 0:
            self.selection_count_label.config(text="No songs selected")
        elif count == 1:
            self.selection_count_label.config(text="1 song selected")
        else:
            self.selection_count_label.config(text=f"{count} songs selected")

    def add_selected_to_existing(self):
        if not self.selected_songs:
            messagebox.showwarning("Warning", "Please select songs first!")
            return

        # Get physically existing folders with song counts
        folder_counts = self.get_folder_song_counts()

        if not folder_counts:
            messagebox.showinfo("Info", "No folders available yet. Use 'Add Selected to New Folder' first.")
            return

        # Create selection dialog with all available folders and counts
        self.select_folder_dialog_with_counts(folder_counts)

    def get_folder_song_counts(self):
        """Get song counts for all existing folders"""
        folder_counts = {}

        # Get physically existing folders
        if self.organized_music_path.exists():
            for folder_path in self.organized_music_path.iterdir():
                if folder_path.is_dir():
                    # Count songs in this folder
                    song_count = len([f for f in folder_path.iterdir()
                                    if f.is_file() and any(f.name.lower().endswith(ext)
                                                         for ext in self.music_extensions)])
                    folder_counts[folder_path.name] = song_count

        # Add folders from current session
        for folder_name in self.created_folders:
            if folder_name not in folder_counts:
                # Count planned songs for this folder
                planned_count = sum(1 for dest_folder in self.organization_plan.values()
                                  if dest_folder == folder_name)
                folder_counts[folder_name] = planned_count
            else:
                # Add planned songs to existing count
                planned_count = sum(1 for dest_folder in self.organization_plan.values()
                                  if dest_folder == folder_name)
                folder_counts[folder_name] += planned_count

        return folder_counts

    def select_folder_dialog_with_counts(self, folder_counts):
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Folder")
        dialog.geometry("500x300")
        dialog.grab_set()

        ttk.Label(dialog, text="Select a folder (showing song counts):").pack(pady=10)

        listbox = tk.Listbox(dialog)
        folder_names = []
        for folder_name, count in sorted(folder_counts.items()):
            display_name = f"{folder_name} ({count}/500)"
            listbox.insert(tk.END, display_name)
            folder_names.append(folder_name)

        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_folder = folder_names[selection[0]]
                current_count = folder_counts[selected_folder]

                # Check if adding selected songs would exceed 500
                if current_count + len(self.selected_songs) > 500:
                    # Ask if user wants to create a new folder
                    overflow = current_count + len(self.selected_songs) - 500
                    result = messagebox.askyesno(
                        "Folder Full",
                        f"Adding {len(self.selected_songs)} songs to '{selected_folder}' would exceed the 500 song limit by {overflow} songs.\n\n"
                        f"Would you like to create '{self.get_next_folder_name(selected_folder)}' for the additional songs?"
                    )
                    if result:
                        self.assign_selected_to_folder_with_overflow(selected_folder, current_count)
                    dialog.destroy()
                else:
                    self.assign_selected_to_folder(selected_folder)
                    dialog.destroy()

        ttk.Button(dialog, text="Select", command=on_select).pack(pady=10)

    def get_next_folder_name(self, base_name):
        """Generate next folder name in sequence (Rock 2.0, Rock 3.0, etc.)"""
        folder_counts = self.get_folder_song_counts()

        # Find highest number for this base name
        max_num = 1
        for folder_name in folder_counts.keys():
            if folder_name.startswith(base_name):
                if folder_name == base_name:
                    max_num = max(max_num, 1)
                elif ' ' in folder_name:
                    parts = folder_name.split(' ')
                    if len(parts) >= 2 and parts[-1].replace('.', '').isdigit():
                        try:
                            num = float(parts[-1])
                            max_num = max(max_num, int(num))
                        except ValueError:
                            pass

        return f"{base_name} {max_num + 1}.0"

    def assign_selected_to_folder_with_overflow(self, folder_name, current_count):
        """Assign selected songs, creating new folder if needed for overflow"""
        songs_to_assign = list(self.selected_songs)

        # Calculate how many can fit in current folder
        can_fit = max(0, 500 - current_count)

        if can_fit > 0:
            # Assign some to current folder
            for song_path in songs_to_assign[:can_fit]:
                self.organization_plan[song_path] = folder_name
                self.processed_songs.add(song_path)

            songs_to_assign = songs_to_assign[can_fit:]

        # Create new folder for remaining songs
        if songs_to_assign:
            new_folder_name = self.get_next_folder_name(folder_name)
            for song_path in songs_to_assign:
                self.organization_plan[song_path] = new_folder_name
                self.processed_songs.add(song_path)
                self.created_folders.add(new_folder_name)

        self.created_folders.add(folder_name)
        self.selected_songs.clear()
        self.populate_song_list()  # Refresh the list
        self.update_progress_display()

    def assign_selected_to_folder(self, folder_name):
        """Assign all selected songs to the specified folder"""
        for song_path in self.selected_songs:
            self.organization_plan[song_path] = folder_name
            self.processed_songs.add(song_path)

        self.created_folders.add(folder_name)
        self.selected_songs.clear()
        self.populate_song_list()  # Refresh the list
        self.update_progress_display()

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

    def create_new_folder_for_selected(self):
        if not self.selected_songs:
            messagebox.showwarning("Warning", "Please select songs first!")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Folder")
        dialog.geometry("400x150")
        dialog.grab_set()

        ttk.Label(dialog, text=f"Enter folder name for {len(self.selected_songs)} selected songs:").pack(pady=10)

        entry = ttk.Entry(dialog, width=40)
        entry.pack(pady=10)
        entry.focus()

        def on_create():
            folder_name = entry.get().strip()
            if folder_name:
                self.assign_selected_to_folder(folder_name)
                dialog.destroy()
            else:
                messagebox.showwarning("Warning", "Please enter a folder name")

        ttk.Button(dialog, text="Create", command=on_create).pack(pady=10)
        entry.bind('<Return>', lambda e: on_create())

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
            self.created_folders.add(folder_name)  # Track this folder as created
            self.processed_songs.add(current_song)
            self.next_song()

    def skip_selected_songs(self):
        if not self.selected_songs:
            messagebox.showwarning("Warning", "Please select songs first!")
            return

        for song_path in self.selected_songs:
            self.processed_songs.add(song_path)

        self.selected_songs.clear()
        self.populate_song_list()  # Refresh the list
        self.update_progress_display()

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
            'created_folders': list(self.created_folders),
            'duplicates': dict(self.duplicates),
            'destination_base_path': str(self.destination_base_path),
            'song_metadata': self.song_metadata
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
                self.created_folders = set(progress_data.get('created_folders', []))
                self.duplicates = defaultdict(list, progress_data.get('duplicates', {}))
                self.song_metadata = progress_data.get('song_metadata', {})

                # Load destination path if saved, otherwise use default
                saved_destination = progress_data.get('destination_base_path')
                if saved_destination:
                    self.destination_base_path = Path(saved_destination)
                    self.organized_music_path = self.destination_base_path / "Organized_Music"
                    self.destination_label.config(text=f"Destination: {self.organized_music_path}")

                self.update_folders_display()
                self.update_progress_display()
                self.populate_song_list()

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
        message = f"Move completed!\nSuccess: {success_count}\nErrors: {error_count}\n\nFiles moved to: {self.organized_music_path}"
        if errors:
            message += f"\n\nFirst few errors:\n" + "\n".join(errors[:5])

        messagebox.showinfo("Move Complete", message)

        # Clear the plan after successful execution
        if error_count == 0:
            self.organization_plan.clear()
            # Don't clear created_folders since they now physically exist
            # Clear source folders since files have been moved
            self.source_folders.clear()
            self.all_songs.clear()
            self.processed_songs.clear()
            self.current_index = 0
            self.save_progress()
            self.update_folders_display()
            self.update_progress_display()
            self.populate_song_list()

    def get_song_metadata(self, song_path):
        """Extract metadata from audio file using mutagen"""
        if song_path in self.song_metadata:
            return self.song_metadata[song_path]

        metadata = {
            'artist': '',
            'album': '',
            'genre': '',
            'title': ''
        }

        try:
            audio = MutagenFile(song_path)
            if audio is None:
                return metadata

            # Try different tag formats
            if hasattr(audio, 'tags') and audio.tags:
                # For MP3 files
                if isinstance(audio.tags, dict):
                    metadata['artist'] = str(audio.tags.get('©ART', [''])[0]) if '©ART' in audio.tags else str(audio.tags.get('artist', [''])[0])
                    metadata['album'] = str(audio.tags.get('©alb', [''])[0]) if '©alb' in audio.tags else str(audio.tags.get('album', [''])[0])
                    metadata['genre'] = str(audio.tags.get('©gen', [''])[0]) if '©gen' in audio.tags else str(audio.tags.get('genre', [''])[0])
                    metadata['title'] = str(audio.tags.get('©nam', [''])[0]) if '©nam' in audio.tags else str(audio.tags.get('title', [''])[0])
                else:
                    # EasyID3 or similar
                    metadata['artist'] = str(audio.tags.get('artist', [''])[0]) if 'artist' in audio.tags else ''
                    metadata['album'] = str(audio.tags.get('album', [''])[0]) if 'album' in audio.tags else ''
                    metadata['genre'] = str(audio.tags.get('genre', [''])[0]) if 'genre' in audio.tags else ''
                    metadata['title'] = str(audio.tags.get('title', [''])[0]) if 'title' in audio.tags else ''

            # For MP4/M4A files
            if song_path.lower().endswith(('.m4a', '.mp4')):
                try:
                    audio = MP4(song_path)
                    metadata['artist'] = str(audio.get('\xa9ART', [''])[0]) if '\xa9ART' in audio else ''
                    metadata['album'] = str(audio.get('\xa9alb', [''])[0]) if '\xa9alb' in audio else ''
                    metadata['genre'] = str(audio.get('\xa9gen', [''])[0]) if '\xa9gen' in audio else ''
                    metadata['title'] = str(audio.get('\xa9nam', [''])[0]) if '\xa9nam' in audio else ''
                except:
                    pass

            # Clean up metadata
            for key in metadata:
                if isinstance(metadata[key], list):
                    metadata[key] = metadata[key][0] if metadata[key] else ''
                metadata[key] = str(metadata[key]).strip()

        except Exception as e:
            pass  # Return empty metadata on error

        self.song_metadata[song_path] = metadata
        return metadata

    def sort_songs(self, songs, mode):
        """Sort songs based on the selected mode"""
        if mode == "artist":
            return sorted(songs, key=lambda s: (
                self.get_song_metadata(s)['artist'].lower() or 'zzz',
                self.get_song_metadata(s)['album'].lower() or 'zzz',
                os.path.basename(s).lower()
            ))
        elif mode == "album":
            return sorted(songs, key=lambda s: (
                self.get_song_metadata(s)['album'].lower() or 'zzz',
                self.get_song_metadata(s)['artist'].lower() or 'zzz',
                os.path.basename(s).lower()
            ))
        else:  # filename
            return sorted(songs, key=lambda s: os.path.basename(s).lower())

    def play_song(self, song_path):
        """Play a song using pygame mixer"""
        try:
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.play()
            self.currently_playing = song_path
            self.is_paused = False

            # Get song length
            try:
                audio = MutagenFile(song_path)
                if audio and hasattr(audio.info, 'length'):
                    self.song_length = audio.info.length
                else:
                    self.song_length = 0
            except:
                self.song_length = 0

            # Update UI
            song_name = os.path.basename(song_path)
            metadata = self.get_song_metadata(song_path)
            if metadata['artist'] and metadata['title']:
                display_name = f"{metadata['artist']} - {metadata['title']}"
            else:
                display_name = song_name
            self.now_playing_label.config(text=f"▶ {display_name}", foreground="green")

            # Update seek bar
            if self.song_length > 0:
                self.seek_bar.config(to=self.song_length)
                self.duration_label.config(text=self.format_time(self.song_length))

            # Start updating the seek bar position
            self.update_seek_bar()

        except Exception as e:
            messagebox.showerror("Playback Error", f"Could not play song:\n{str(e)}")

    def play_selected(self):
        """Play the first selected song"""
        if self.selected_songs:
            first_song = list(self.selected_songs)[0]
            self.play_song(first_song)
        elif self.currently_playing:
            # Resume if paused
            if self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.now_playing_label.config(text=self.now_playing_label.cget("text").replace("⏸", "▶"), foreground="green")
                # Resume seek bar updates
                self.update_seek_bar()
        else:
            messagebox.showinfo("Info", "Please select a song to play")

    def pause_audio(self):
        """Pause the currently playing audio"""
        if pygame.mixer.music.get_busy() and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.now_playing_label.config(text=self.now_playing_label.cget("text").replace("▶", "⏸"), foreground="orange")

    def stop_audio(self):
        """Stop the currently playing audio"""
        pygame.mixer.music.stop()
        self.currently_playing = None
        self.is_paused = False
        self.song_length = 0
        self.now_playing_label.config(text="No song playing", foreground="gray")

        # Reset seek bar
        self.seek_bar.set(0)
        self.time_label.config(text="0:00")
        self.duration_label.config(text="0:00")

        # Cancel update job
        if self.seek_update_job:
            self.root.after_cancel(self.seek_update_job)
            self.seek_update_job = None

    def format_time(self, seconds):
        """Format seconds to MM:SS"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"

    def update_seek_bar(self):
        """Update seek bar position based on current playback position"""
        if pygame.mixer.music.get_busy() and not self.is_paused:
            # Get current position (in seconds)
            pos = pygame.mixer.music.get_pos() / 1000.0

            # pygame.mixer.music.get_pos() can be unreliable, so we use our own tracking
            if hasattr(self, '_play_start_time'):
                current_time = (pygame.time.get_ticks() - self._play_start_time) / 1000.0
            else:
                self._play_start_time = pygame.time.get_ticks()
                current_time = 0

            if current_time <= self.song_length:
                self.seek_bar.set(current_time)
                self.time_label.config(text=self.format_time(current_time))

            # Schedule next update
            self.seek_update_job = self.root.after(100, self.update_seek_bar)
        elif self.is_paused:
            # Keep the position when paused
            pass
        else:
            # Song ended or stopped
            if self.currently_playing:
                self.seek_bar.set(0)
                self.time_label.config(text="0:00")

    def on_seek_start(self, event):
        """Called when user starts dragging the seek bar"""
        self.seeking = True

    def on_seek_end(self, event):
        """Called when user releases the seek bar"""
        if hasattr(self, 'seeking') and self.seeking:
            self.seeking = False
            # Perform the actual seek
            new_pos = self.seek_bar.get()
            if self.currently_playing and pygame.mixer.music.get_busy():
                try:
                    pygame.mixer.music.play(start=new_pos)
                    self._play_start_time = pygame.time.get_ticks() - (new_pos * 1000)
                except:
                    pass  # Some audio formats don't support seeking

    def on_seek(self, value):
        """Called when seek bar value changes"""
        if not hasattr(self, 'seeking') or not self.seeking:
            return
        # Update time label while dragging
        self.time_label.config(text=self.format_time(float(value)))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MusicOrganizer()
    app.run()