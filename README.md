# Music Organizer

A Python GUI application designed to help organize large music collections (7000+ songs) across multiple sessions with progress saving capabilities.

## Overview

This tool allows you to:
- Browse and select source folders containing unorganized music files
- Go through each song individually and decide where to organize it
- Create new folders or add to existing ones on-the-fly
- Save progress and resume later (essential for large collections)
- Detect and handle duplicate files
- Safely preview the organization plan before executing file moves
- Move all files to a clean organized structure on your Desktop

## Features

### Core Functionality
- **GUI Folder Browser**: Select multiple source directories containing music
- **Multi-format Support**: Scans for mp3, mp4, m4a, wav, flac, aac, ogg files
- **Interactive Organization**: Review each song and choose destination
- **Progress Persistence**: Save/load progress across multiple sessions
- **Duplicate Detection**: Identifies identical files and alerts user
- **Safe Execution**: Preview organization plan before moving files

### Organization Options
For each song, you can:
- Add to existing folder (choose from dropdown)
- Create new folder (type custom name)
- Skip song (leave in original location)
- Navigate back to previous songs

### File Management
- **Destination**: Creates `~/Desktop/Organized_Music/` folder
- **Folder Structure**: Creates subfolders based on your choices
- **Duplicate Handling**: Renames files if name conflicts occur
- **Safe Moves**: Uses `shutil.move()` to preserve file integrity

## How to Run

1. **Install Python** (3.7+ recommended)
2. **Navigate to project directory**:
   ```bash
   cd C:\Users\Kishore\Documents\GitHub\OrganizeMusic
   ```
3. **Run the application**:
   ```bash
   python music_organizer.py
   ```

## How to Use

### Step 1: Select Source Folders
1. Click "Browse Folders" to select directories containing music files
2. You can select multiple folders - each one will be added to the list
3. Click "Scan for Music" to find all audio files

### Step 2: Review and Organize Songs
1. The application shows each song filename and full path
2. For each song, choose one of:
   - **Add to Existing Folder**: Choose from previously created folders
   - **Create New Folder**: Type a new folder name (e.g., "Rock", "Jazz", "Workout")
   - **Skip Song**: Leave in original location
3. Use "Previous"/"Next" to navigate between songs
4. **Save Progress frequently** (every 50-100 songs recommended)

### Step 3: Execute Organization
1. Click "View Plan" to review all organization decisions
2. Click "Execute Moves" to actually move the files
3. Files will be moved to `~/Desktop/Organized_Music/[FolderName]/`

## Progress Management

### Auto-Save Features
- Progress is saved to `music_organizer_progress.json`
- Automatically loads previous session on startup
- Tracks which songs have been processed
- Remembers current position in the list

### Multi-Session Workflow
1. Process songs until you need a break
2. Click "Save Progress"
3. Close the application
4. Later: Run `python music_organizer.py` again
5. Progress automatically resumes where you left off

## File Structure

```
OrganizeMusic/
├── music_organizer.py              # Main application
├── music_organizer_progress.json   # Progress save file (auto-created)
└── README.md                       # This file

~/Desktop/Organized_Music/          # Destination folder (auto-created)
├── Rock/                          # Example folders you create
├── Jazz/
├── Classical/
└── ...
```

## Current Status

**Project Status**: ✅ Complete and ready to use

**Development Complete**:
- [x] GUI file browser for source folder selection
- [x] Music file scanner (multiple formats)
- [x] Song review interface with organization options
- [x] Progress saving/loading system
- [x] File moving functionality
- [x] Desktop destination folder structure
- [x] Duplicate detection and alerting
- [x] Testing completed

**Ready for Production Use**: The application has been tested and is ready to organize large music collections.

## Technical Details

### Dependencies
- **tkinter**: GUI framework (built into Python)
- **pathlib**: Modern path handling
- **hashlib**: Duplicate detection via MD5 hashing
- **shutil**: Safe file operations
- **json**: Progress data serialization

### Supported Audio Formats
- MP3 (.mp3)
- MP4 Audio (.mp4, .m4a)
- WAV (.wav)
- FLAC (.flac)
- AAC (.aac)
- OGG (.ogg)

### Safety Features
- Non-destructive preview mode
- Progress auto-save every operation
- Duplicate filename handling
- Error reporting and rollback capabilities
- Confirmation dialogs for destructive operations

## Troubleshooting

**GUI doesn't appear**: Ensure tkinter is installed (usually built-in with Python)
**Progress lost**: Check for `music_organizer_progress.json` in the same directory
**Duplicate files**: Use the duplicate viewer to identify and manually delete unwanted copies
**Move errors**: Check file permissions and ensure destination drive has enough space

## Next Steps

1. Run the application
2. Select your source folders containing unorganized music
3. Start organizing! Remember to save progress frequently
4. For 7000+ songs, plan multiple sessions over several days/weeks