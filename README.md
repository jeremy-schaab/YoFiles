# YoFiles - Windows Folder Size Viewer

A lightweight, fast Windows folder size analyzer with caching support. No more hunting for bloated freeware - this is your simple, effective solution for finding what's eating your disk space!

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **Lightning Fast Caching** - Scanned directories are cached for instant navigation
- **Real-time Folder Sizes** - See folder and file sizes with file/subfolder counts
- **Smart Navigation** - Double-click to enter folders, with instant scan interruption
- **Safe Deletion** - Delete files/folders with confirmation (supports Recycle Bin)
- **Multi-Drive Support** - Easy switching between all available drives
- **Sortable Columns** - Sort by name, size, file count, or folder count
- **Progress Tracking** - Visual feedback during scans with stop capability
- **Lightweight** - Pure Python with minimal dependencies

## Quick Install (Easiest Method)

### Option 1: Download Release (Recommended)
1. Go to [Releases](https://github.com/jeremy-schaab/YoFiles/releases)
2. Download `YoFiles.exe` 
3. Double-click to run - no installation needed!

### Option 2: Run from Source
```bash
# Clone the repository
git clone https://github.com/jeremy-schaab/YoFiles.git
cd YoFiles

# Install dependency
pip install send2trash

# Run the application
python folder_size_viewer.py
```

### Option 3: Use Install Script
1. Download the repository as ZIP
2. Extract to any folder
3. Double-click `install.bat`
4. Find `YoFiles.exe` in the `dist` folder

## Usage

1. **Select a Drive** - Choose from the dropdown or enter a custom path
2. **Scan** - Click "Scan" to analyze the current directory
3. **Navigate** - Double-click folders to explore deeper
4. **Delete Files** - Right-click for delete options:
   - Delete permanently
   - Send to Recycle Bin
   - View properties
5. **Refresh** - Force rescan of cached directories with the Refresh button

### Keyboard Shortcuts
- `Enter` in path field - Navigate to typed path
- `Double-click` - Open folder (interrupts current scan)
- `Right-click` - Context menu for delete/properties

## Building from Source

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Build Standalone EXE
```bash
# Install build requirements
pip install pyinstaller send2trash

# Create executable
pyinstaller --onefile --windowed --icon=icon.ico --name=YoFiles folder_size_viewer.py

# Find your exe in dist/YoFiles.exe
```

## System Requirements

- **OS**: Windows 7/8/10/11
- **Python**: 3.7+ (if running from source)
- **RAM**: 128MB minimum
- **Disk**: 10MB for application

## Screenshots

### Main Interface
- Tree view with folder/file icons
- Size information in human-readable format
- File and folder counts for directories
- Status bar with totals

### Features in Action
- Real-time scanning progress
- Cached directory indicator
- Right-click context menu
- Drive selection dropdown

## Technical Details

### Architecture
- **Threading**: Background scanning to maintain UI responsiveness
- **Caching**: In-memory cache with timestamps
- **File Operations**: Safe deletion with send2trash library
- **UI Framework**: Tkinter (included with Python)

### Performance
- Handles directories with 100,000+ files
- Cache eliminates redundant scans
- Instant navigation with scan interruption
- Memory efficient - clears old cache automatically

## Troubleshooting

### "Module not found" Error
```bash
pip install send2trash
```

### Slow Scanning
- Large directories take time on first scan
- Subsequent visits use cache (instant)
- Use "Stop" button to cancel long scans

### Permission Errors
- Run as Administrator for system directories
- Some folders may be inaccessible (normal)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Future Enhancements

- [ ] Export scan results to CSV/JSON
- [ ] Dark mode theme
- [ ] Duplicate file finder
- [ ] File type breakdown charts
- [ ] Network drive support
- [ ] Customizable file filters
- [ ] Scheduled scans
- [ ] Disk usage alerts

## License

This project is licensed under the MIT License - see below for details:

```
MIT License

Copyright (c) 2024 YoFiles

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Author

Created with frustration at bloated freeware and a desire for something simple that just works.

## Support

If you find this tool useful, give it a star on GitHub! 

For issues or questions, please use the [GitHub Issues](https://github.com/jeremy-schaab/YoFiles/issues) page.

---

**YoFiles** - Because finding large files shouldn't require large software.