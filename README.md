# 🎮 CS2 Auto Clip Extractor

An automated video processing tool that detects and extracts kill moments from Counter-Strike 2 gameplay recordings. The application uses computer vision techniques to identify kill feed events and automatically creates clip compilations.

![Version](https://img.shields.io/badge/version-1.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 📋 Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [How to Use](#how-to-use)
- [Future Development](#future-development)

---

## ✨ Features

- **Automatic Kill Detection**: Uses template matching and edge detection to identify kill feed events
- **Smart Clip Merging**: Combines consecutive kills into single highlight clips
- **ROI (Region of Interest)**: Focus detection on specific screen areas for better performance
- **Color Filtering**: Distinguishes between player kills (red border) and teammate kills (gray border)
- **Multi-language Support**: Available in Turkish and English
- **Modern GUI**: Built with CustomTkinter for a sleek, dark-themed interface
- **Real-time Preview**: Watch detection in action with live frame preview
- **Batch Processing**: Process multiple videos automatically
- **Smart Caching**: Skips already processed videos
- **FFmpeg Integration**: Fast, lossless clip extraction with audio preservation

---

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- FFmpeg (must be in system PATH)
- Windows OS (currently optimized for Windows)

### Step 1: Install Python Dependencies

```bash
pip install opencv-python numpy customtkinter pillow
```

Or use the requirements file if provided:

```bash
pip install -r requirements.txt
```

### Step 2: Install FFmpeg

1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract the archive
3. Add the `bin` folder to your system PATH
4. Verify installation: `ffmpeg -version`

### Step 3: Prepare Template Image

You need a template image of the CS2 kill feed icon:
- Take a screenshot during a kill
- Crop just the kill feed icon/symbol
- Save as `killfeed_template.jpg` in the project root

**Optional**: For ROI preview, include an `example.jpg` screenshot showing your typical CS2 UI.

### Step 4: Run the Application

Double-click `start.bat` or run:

```bash
pythonw gui.py
```

---

## ⚙️ Configuration

The application is configured through `config.json`. All settings can also be adjusted via the GUI Settings tab.

### General Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `LANGUAGE` | `"tr"` | Interface language (`"tr"` or `"en"`) |
| `INPUT_FOLDER` | `"input_videos"` | Folder containing videos to process |
| `OUTPUT_FOLDER` | `"kills"` | Folder where clips will be saved |
| `TEMPLATE_PATH` | `"killfeed_template.jpg"` | Path to kill feed template image |

### Detection Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `THRESHOLD` | `0.55` | Template matching threshold (0.0-1.0). Higher = more strict |
| `FRAME_SKIP` | `120` | Process every Nth frame (120 = every 2 seconds at 60fps) |
| `KILL_COOLDOWN` | `2.0` | Minimum seconds between kill detections |
| `USE_EDGE_DETECTION` | `true` | Use Canny edge detection for better accuracy |
| `USE_COLOR_FILTER` | `true` | Filter by red border (player kills only) |
| `CANNY_THRESHOLD1` | `150` | Canny edge detection lower threshold |
| `CANNY_THRESHOLD2` | `250` | Canny edge detection upper threshold |
| `MIN_COLOR_PIXELS` | `150` | Minimum red pixels to confirm player kill |

### Buffer Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `BUFFER_BEFORE` | `4.0` | Seconds to include before kill |
| `BUFFER_AFTER` | `4.0` | Seconds to include after kill |
| `MIN_KILL_GAP` | `7.0` | Merge kills within this time gap (seconds) |

### ROI (Region of Interest) Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `USE_ROI` | `true` | Only scan specific screen region |
| `ROI_X_START` | `0.83` | ROI left edge (0.0-1.0, percentage of width) |
| `ROI_Y_START` | `0.07` | ROI top edge (0.0-1.0, percentage of height) |
| `ROI_X_END` | `1.0` | ROI right edge (0.0-1.0, percentage of width) |
| `ROI_Y_END` | `0.25` | ROI bottom edge (0.0-1.0, percentage of height) |

### Color Filter Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `KILL_COLOR_LOWER` | `[0, 120, 80]` | HSV lower bound for red (range 1) |
| `KILL_COLOR_UPPER` | `[10, 255, 255]` | HSV upper bound for red (range 1) |
| `KILL_COLOR_LOWER2` | `[170, 120, 80]` | HSV lower bound for red (range 2) |
| `KILL_COLOR_UPPER2` | `[180, 255, 255]` | HSV upper bound for red (range 2) |

---

## 📖 How to Use

### 1. Prepare Your Videos

1. Place your CS2 gameplay recordings in the `input_videos` folder
2. Supported formats: `.mp4`, `.avi`, `.mov`, `.mkv`, `.flv`, `.wmv`

### 2. Launch the Application

Run `start.bat` or execute `pythonw gui.py`

### 3. Navigate the Interface

#### 🎬 Process Tab
- Click **"▶ Start Processing"** to begin
- Monitor real-time logs showing detection progress
- View live preview of detected kills
- Track progress bar and statistics

#### 📁 Videos Tab
- View all videos in the input folder
- See processing status (✓ Processed / ⏳ Waiting)
- File size information
- Quick access to input folder

#### ✂️ Clips Tab
- Browse all extracted clips
- See file details and source video
- Play clips directly from the interface
- Quick access to output folder

#### ⚙️ Settings Tab
- Adjust all detection parameters
- Configure ROI with live preview overlay
- Change buffer times
- Modify detection thresholds
- Save settings with one click

### 4. Processing Flow

The application follows this workflow:

1. **Scan Input**: Discovers all video files in `input_videos`
2. **Skip Processed**: Checks `processed_videos.json` to avoid reprocessing
3. **Detect Kills**: Uses template matching to find kill feed events
4. **Filter Results**: Applies edge detection and color filtering
5. **Merge Clips**: Combines consecutive kills into single segments
6. **Extract Clips**: Uses FFmpeg to create video clips with buffers
7. **Save Results**: Outputs clips to `kills` folder with descriptive names

### 5. Output Format

Clips are named descriptively:
```
{original_video_name}_kill_{number}_{start_time}s-{end_time}s.mp4
```

Example:
```
competitive_match_kill_001_45.3s-52.1s.mp4
```

### 6. Tips for Best Results

- **Template Quality**: Use a clear, high-contrast screenshot of the kill feed icon
- **ROI Configuration**: Use the ROI preview to ensure the kill feed area is covered
- **Threshold Tuning**: 
  - Too low (< 0.50): False positives
  - Too high (> 0.70): Missed kills
  - Start at 0.55 and adjust
- **Frame Skip**: Higher values = faster processing but may miss quick kills
- **Color Filter**: Disable if you want teammate kills included
- **Buffer Times**: Adjust for desired clip length (default: 8 seconds total)

---

## 🔮 Future Development

### Planned Features

#### Core Functionality
- [ ] **Multi-game Support**: Expand to other FPS games (Valorant, Apex Legends, COD)
- [ ] **Auto-template Generation**: Automatically detect and extract kill feed templates
- [ ] **Smart Scene Detection**: Use ML to identify kill contexts (clutches, aces, headshots)
- [ ] **Audio Detection**: Detect kills by analyzing game audio peaks
- [ ] **Death Detection**: Also extract clips where player dies (for analysis)

#### Advanced Processing
- [ ] **Highlight Scoring**: Rank clips by "epicness" (multi-kills, quick succession)
- [ ] **Auto-compilation**: Combine best clips into montages with transitions
- [ ] **Music Sync**: Beat-match clips to background music
- [ ] **Slow-motion Effects**: Automatically slow down key moments
- [ ] **Text Overlays**: Add kill count, weapon info, timestamp overlays

#### Detection Improvements
- [ ] **Deep Learning Model**: Train a neural network for more accurate kill detection
- [ ] **OCR Integration**: Read kill feed text for detailed statistics
- [ ] **Weapon Recognition**: Identify weapons used for clip categorization
- [ ] **Player Name Extraction**: Track individual players across clips
- [ ] **Scoreboard Reading**: Extract match stats from scoreboards

#### User Experience
- [ ] **Video Player Integration**: Built-in video player with frame-by-frame scrubbing
- [ ] **Timeline Editor**: Visual timeline to manually adjust clip boundaries
- [ ] **Bulk Operations**: Delete, rename, merge multiple clips at once
- [ ] **Cloud Upload**: Direct upload to YouTube, Twitch, TikTok
- [ ] **Discord Bot**: Share clips directly to Discord servers
- [ ] **Mobile Companion**: Remote monitoring and clip playback on phones

#### Performance & Quality
- [ ] **GPU Acceleration**: Use CUDA for faster processing
- [ ] **Multi-threading**: Process multiple videos simultaneously
- [ ] **Quality Presets**: Export profiles (web, HD, 4K, mobile)
- [ ] **Hardware Encoding**: H.265/HEVC support for smaller file sizes
- [ ] **Batch Compression**: Automatically optimize clip file sizes

#### Analytics & Statistics
- [ ] **Session Statistics**: Track kills per match, accuracy trends
- [ ] **Weapon Stats**: Most used weapons, success rates
- [ ] **Map Analytics**: Performance breakdown by map
- [ ] **Improvement Tracking**: Monitor skill progression over time
- [ ] **Export Reports**: Generate PDF/HTML stat summaries

#### Configuration & Customization
- [ ] **Multiple Profiles**: Save different settings for different games
- [ ] **Preset Library**: Community-shared detection settings
- [ ] **Custom Themes**: UI color schemes and layouts
- [ ] **Hotkey Support**: Keyboard shortcuts for all actions
- [ ] **Auto-update**: Built-in update checker and installer

#### Integration & Export
- [ ] **OBS Integration**: Trigger clip extraction during live streams
- [ ] **Replay Buffer**: Process shadowplay/instant replay footage
- [ ] **Format Conversion**: Export for social media (9:16, 1:1)
- [ ] **Thumbnail Generation**: Auto-create attractive thumbnails
- [ ] **Metadata Tagging**: Add keywords, descriptions for organization

#### Technical Improvements
- [ ] **Cross-platform**: MacOS and Linux support
- [ ] **Installer Package**: One-click installation with bundled dependencies
- [ ] **Error Recovery**: Resume processing after crashes
- [ ] **Logging System**: Detailed debug logs for troubleshooting
- [ ] **Unit Tests**: Comprehensive test coverage
- [ ] **Documentation**: Video tutorials and wiki

### Community Features
- [ ] **Clip Sharing Platform**: Upload and browse community clips
- [ ] **Rating System**: Vote on best plays
- [ ] **Leaderboards**: Compete for best clips
- [ ] **Tournaments**: Organize clip competitions
- [ ] **Plugin System**: Allow community-created extensions

---

## 📝 License

This project is provided as-is for personal use.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## 💡 Support

For issues, questions, or suggestions, please open an issue on the repository.

---

**Made with ❤️ for the CS2 community**
