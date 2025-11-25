import tkinter as tk
from tkinter import ttk, messagebox
import os
import threading
from pathlib import Path
import string
import time
from collections import defaultdict
import shutil
import send2trash
import stat
import queue
from datetime import datetime

class FolderSizeViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows Folder Size Viewer")
        self.root.geometry("1200x750")

        # Store folder sizes for sorting
        self.folder_data = {}
        self.current_path = ""
        self.scan_thread = None
        self.stop_scan = False
        self.is_scanning = False

        # Session cache for scanned directories
        self.directory_cache = {}
        self.cache_timestamps = {}

        # Progress tracking
        self.scan_start_time = None
        self.items_processed = 0
        self.total_items = 0

        # Queue for thread-safe UI updates
        self.update_queue = queue.Queue()

        self.setup_ui()
        self.load_drives()

        # Start the queue processor
        self.process_queue()

    def setup_ui(self):
        # Top frame for controls
        control_frame = ttk.Frame(self.root, padding="5")
        control_frame.pack(fill=tk.X)

        # Drive selection
        ttk.Label(control_frame, text="Drive:").pack(side=tk.LEFT, padx=(0, 5))
        self.drive_var = tk.StringVar()
        self.drive_combo = ttk.Combobox(control_frame, textvariable=self.drive_var, width=10, state="readonly")
        self.drive_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.drive_combo.bind("<<ComboboxSelected>>", self.on_drive_change)

        # Current path display
        ttk.Label(control_frame, text="Path:").pack(side=tk.LEFT, padx=(0, 5))
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(control_frame, textvariable=self.path_var, width=50)
        self.path_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        self.path_entry.bind("<Return>", self.on_path_change)

        # Buttons
        self.scan_button = ttk.Button(control_frame, text="Scan", command=self.scan_folder)
        self.scan_button.pack(side=tk.LEFT, padx=5)

        self.refresh_button = ttk.Button(control_frame, text="Refresh", command=self.refresh_folder)
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_scanning, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Go Up", command=self.go_up).pack(side=tk.LEFT, padx=5)

        self.delete_button = ttk.Button(control_frame, text="Delete Selected", command=self.delete_selected)
        self.delete_button.pack(side=tk.LEFT, padx=5)

        # Progress frame with more detail
        self.progress_frame = ttk.Frame(self.root)
        self.progress_frame.pack(fill=tk.X, padx=5, pady=5)

        # Progress info on left
        progress_info_frame = ttk.Frame(self.progress_frame)
        progress_info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_label = ttk.Label(progress_info_frame, text="Ready")
        self.progress_label.pack(side=tk.LEFT, padx=(0, 10))

        self.progress_detail = ttk.Label(progress_info_frame, text="", foreground="gray")
        self.progress_detail.pack(side=tk.LEFT, padx=(0, 10))

        self.time_label = ttk.Label(progress_info_frame, text="", foreground="blue")
        self.time_label.pack(side=tk.LEFT)

        # Progress bar - determinate mode for better feedback
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate', length=200)
        self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))

        self.progress_percent = ttk.Label(self.progress_frame, text="0%", width=5)
        self.progress_percent.pack(side=tk.RIGHT)

        # Main content area with PanedWindow for resizable panels
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - Treeview
        tree_container = ttk.Frame(self.main_pane)
        self.main_pane.add(tree_container, weight=3)

        # Create Treeview with scrollbars
        tree_frame = ttk.Frame(tree_container)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Treeview
        self.tree = ttk.Treeview(tree_frame, columns=("Size", "Type", "Files", "Folders"),
                                 yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Configure columns
        self.tree.heading("#0", text="Name", command=lambda: self.sort_tree("name"))
        self.tree.heading("Size", text="Size", command=lambda: self.sort_tree("size"))
        self.tree.heading("Type", text="Type")
        self.tree.heading("Files", text="Files", command=lambda: self.sort_tree("files"))
        self.tree.heading("Folders", text="Folders", command=lambda: self.sort_tree("folders"))

        self.tree.column("#0", width=350)
        self.tree.column("Size", width=120)
        self.tree.column("Type", width=80)
        self.tree.column("Files", width=80)
        self.tree.column("Folders", width=80)

        # Pack treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Bind events
        self.tree.bind("<Double-1>", self.on_item_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)

        # Create context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open", command=self.open_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.delete_selected)
        self.context_menu.add_command(label="Delete to Recycle Bin", command=self.delete_to_recycle)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Properties", command=self.show_properties_dialog)

        # Right panel - Metadata details
        self.details_frame = ttk.LabelFrame(self.main_pane, text="Details", padding="10")
        self.main_pane.add(self.details_frame, weight=1)

        self.setup_details_panel()

        # Status bar
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(self.status_frame, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X, padx=2, pady=2)

    def setup_details_panel(self):
        """Setup the metadata details panel"""
        # Icon and name at top
        self.detail_icon_label = ttk.Label(self.details_frame, text="", font=('Segoe UI Emoji', 32))
        self.detail_icon_label.pack(anchor=tk.W, pady=(0, 5))

        self.detail_name_label = ttk.Label(self.details_frame, text="Select an item to view details",
                                           font=('TkDefaultFont', 11, 'bold'), wraplength=250)
        self.detail_name_label.pack(anchor=tk.W, pady=(0, 10))

        # Separator
        ttk.Separator(self.details_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # Details grid
        self.details_grid = ttk.Frame(self.details_frame)
        self.details_grid.pack(fill=tk.BOTH, expand=True)

        # Create detail labels
        self.detail_labels = {}
        detail_fields = [
            ("type", "Type:"),
            ("size", "Size:"),
            ("size_bytes", "Size (bytes):"),
            ("files", "Files:"),
            ("folders", "Folders:"),
            ("path", "Path:"),
            ("created", "Created:"),
            ("modified", "Modified:"),
            ("accessed", "Accessed:"),
            ("extension", "Extension:"),
            ("attributes", "Attributes:"),
            ("permissions", "Permissions:"),
        ]

        for i, (key, label_text) in enumerate(detail_fields):
            label = ttk.Label(self.details_grid, text=label_text, font=('TkDefaultFont', 9, 'bold'))
            label.grid(row=i, column=0, sticky=tk.W, pady=2)

            value_label = ttk.Label(self.details_grid, text="-", wraplength=200)
            value_label.grid(row=i, column=1, sticky=tk.W, padx=(10, 0), pady=2)

            self.detail_labels[key] = value_label

        # Initially hide all detail rows
        self.clear_details()

    def clear_details(self):
        """Clear the details panel"""
        self.detail_icon_label.config(text="")
        self.detail_name_label.config(text="Select an item to view details")
        for key, label in self.detail_labels.items():
            label.config(text="-")

    def update_details(self, item_name, item_path):
        """Update the details panel with metadata for the selected item"""
        try:
            # Get basic info from folder_data
            if item_name in self.folder_data:
                data = self.folder_data[item_name]
                is_folder = data['type'] == 'Folder'

                # Update icon and name
                self.detail_icon_label.config(text="📁" if is_folder else "📄")
                self.detail_name_label.config(text=item_name)

                # Type
                self.detail_labels['type'].config(text=data['type'])

                # Size
                self.detail_labels['size'].config(text=self.format_size(data['size']))
                self.detail_labels['size_bytes'].config(text=f"{data['size']:,} bytes")

                # Files and folders (for directories)
                if is_folder:
                    self.detail_labels['files'].config(text=f"{data['files']:,}")
                    self.detail_labels['folders'].config(text=f"{data['folders']:,}")
                else:
                    self.detail_labels['files'].config(text="-")
                    self.detail_labels['folders'].config(text="-")

                # Path
                self.detail_labels['path'].config(text=item_path)

            # Get filesystem metadata
            if os.path.exists(item_path):
                stat_info = os.stat(item_path)

                # Dates
                created = datetime.fromtimestamp(stat_info.st_ctime)
                modified = datetime.fromtimestamp(stat_info.st_mtime)
                accessed = datetime.fromtimestamp(stat_info.st_atime)

                self.detail_labels['created'].config(text=created.strftime("%Y-%m-%d %H:%M:%S"))
                self.detail_labels['modified'].config(text=modified.strftime("%Y-%m-%d %H:%M:%S"))
                self.detail_labels['accessed'].config(text=accessed.strftime("%Y-%m-%d %H:%M:%S"))

                # Extension (for files)
                if os.path.isfile(item_path):
                    ext = os.path.splitext(item_name)[1]
                    self.detail_labels['extension'].config(text=ext if ext else "(none)")
                else:
                    self.detail_labels['extension'].config(text="-")

                # Attributes (Windows-specific)
                attributes = []
                try:
                    if os.name == 'nt':
                        import ctypes
                        attrs = ctypes.windll.kernel32.GetFileAttributesW(item_path)
                        if attrs != -1:
                            if attrs & 0x1: attributes.append("Read-only")
                            if attrs & 0x2: attributes.append("Hidden")
                            if attrs & 0x4: attributes.append("System")
                            if attrs & 0x10: attributes.append("Directory")
                            if attrs & 0x20: attributes.append("Archive")
                            if attrs & 0x80: attributes.append("Normal")
                            if attrs & 0x400: attributes.append("Reparse Point")
                            if attrs & 0x800: attributes.append("Compressed")
                            if attrs & 0x4000: attributes.append("Encrypted")
                except Exception:
                    pass

                self.detail_labels['attributes'].config(
                    text=", ".join(attributes) if attributes else "-"
                )

                # Permissions (simplified)
                perms = []
                if os.access(item_path, os.R_OK): perms.append("Read")
                if os.access(item_path, os.W_OK): perms.append("Write")
                if os.access(item_path, os.X_OK): perms.append("Execute")

                self.detail_labels['permissions'].config(
                    text=", ".join(perms) if perms else "-"
                )

        except Exception as e:
            self.detail_name_label.config(text=f"Error: {str(e)}")

    def on_item_select(self, event):
        """Handle item selection to update details panel"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            item_text = item['text']
            item_name = item_text.replace("📁 ", "").replace("📄 ", "")
            item_path = os.path.join(self.current_path, item_name)

            self.update_details(item_name, item_path)
        else:
            self.clear_details()

    def load_drives(self):
        """Load available drives on Windows"""
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(drive)

        # Also add root for Unix systems
        if not drives and os.path.exists("/"):
            drives = ["/"]

        self.drive_combo['values'] = drives
        if drives:
            self.drive_combo.current(0)
            self.path_var.set(drives[0])
            self.current_path = drives[0]

    def format_size(self, size_bytes):
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def get_folder_size(self, folder_path):
        """Calculate folder size with file and folder counts - optimized with frequent stop checks"""
        total_size = 0
        file_count = 0
        folder_count = 0
        check_interval = 100  # Check stop flag every N files
        files_checked = 0

        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                # Check if scan should stop at directory level
                if self.stop_scan:
                    return total_size, file_count, folder_count

                folder_count += len(dirnames)

                for filename in filenames:
                    files_checked += 1

                    # Frequent stop checks for large directories
                    if files_checked % check_interval == 0:
                        if self.stop_scan:
                            return total_size, file_count, folder_count

                    file_count += 1
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, PermissionError):
                        pass

        except (OSError, PermissionError):
            pass

        return total_size, file_count, folder_count

    def load_from_cache(self, path):
        """Load directory data from cache if available"""
        if path in self.directory_cache:
            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Load cached data
            cached_data = self.directory_cache[path]
            self.folder_data = cached_data['folder_data'].copy()

            # Populate tree from cache
            for name, data in self.folder_data.items():
                if data['type'] == 'Folder':
                    self.tree.insert("", "end", text=f"📁 {name}",
                                   values=(self.format_size(data['size']), data['type'],
                                          data['files'], data['folders']))
                else:
                    self.tree.insert("", "end", text=f"📄 {name}",
                                   values=(self.format_size(data['size']), data['type'], "", ""))

            # Update status
            total_size = cached_data['total_size']
            total_files = cached_data['total_files']
            total_folders = cached_data['total_folders']
            cache_time = time.strftime('%H:%M:%S', time.localtime(self.cache_timestamps[path]))

            self.status_label.config(text=f"Total: {self.format_size(total_size)} | "
                                        f"{total_files:,} files | {total_folders:,} folders | "
                                        f"Cached at {cache_time}")
            return True
        return False

    def save_to_cache(self, path):
        """Save current directory data to cache"""
        total_size = sum(data['size'] for data in self.folder_data.values())
        total_files = sum(data['files'] for data in self.folder_data.values())
        total_folders = sum(data['folders'] for data in self.folder_data.values())

        self.directory_cache[path] = {
            'folder_data': self.folder_data.copy(),
            'total_size': total_size,
            'total_files': total_files,
            'total_folders': total_folders
        }
        self.cache_timestamps[path] = time.time()

    def process_queue(self):
        """Process UI update queue - runs on main thread"""
        try:
            while True:
                task = self.update_queue.get_nowait()
                task_type = task[0]

                if task_type == 'add_item':
                    _, name, size, item_type, files, folders = task
                    self.add_tree_item(name, size, item_type, files, folders)

                elif task_type == 'update_progress':
                    _, current, total, item_name = task
                    self.update_progress(current, total, item_name)

                elif task_type == 'scan_complete':
                    _, cancelled = task
                    self.scan_complete(cancelled)

                elif task_type == 'update_status':
                    _, text = task
                    self.status_label.config(text=text)

        except queue.Empty:
            pass

        # Schedule next queue check
        self.root.after(50, self.process_queue)

    def update_progress(self, current, total, item_name=""):
        """Update progress indicators"""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar['value'] = percent
            self.progress_percent.config(text=f"{percent}%")
            self.progress_detail.config(text=f"({current:,} of {total:,} items)")

        if item_name:
            display_name = item_name[:40] + "..." if len(item_name) > 40 else item_name
            self.progress_label.config(text=f"Scanning: {display_name}")

        # Update elapsed time
        if self.scan_start_time:
            elapsed = time.time() - self.scan_start_time
            mins, secs = divmod(int(elapsed), 60)
            self.time_label.config(text=f"Elapsed: {mins:02d}:{secs:02d}")

    def scan_folder_thread(self):
        """Scan folder in a separate thread - optimized for large folders"""
        self.scan_start_time = time.time()

        try:
            # Get all items in current directory first (quick operation)
            items = []

            try:
                dir_contents = os.listdir(self.current_path)
            except (OSError, PermissionError) as e:
                self.update_queue.put(('update_status', f"Error: Cannot access directory - {str(e)}"))
                self.update_queue.put(('scan_complete', False))
                return

            # Quick first pass - separate files and folders
            for item_name in dir_contents:
                if self.stop_scan:
                    self.update_queue.put(('scan_complete', True))
                    return

                item_path = os.path.join(self.current_path, item_name)

                try:
                    if os.path.isdir(item_path):
                        items.append((item_name, item_path, "folder"))
                    else:
                        try:
                            size = os.path.getsize(item_path)
                        except (OSError, PermissionError):
                            size = 0
                        items.append((item_name, item_path, "file", size))
                except (OSError, PermissionError):
                    pass

            total_items = len(items)
            self.total_items = total_items

            # Process files first (quick) then folders (slow)
            # This gives the user something to see quickly
            file_items = [i for i in items if len(i) == 4]
            folder_items = [i for i in items if len(i) == 3]

            processed = 0

            # Process files first (instant)
            for item_data in file_items:
                if self.stop_scan:
                    self.update_queue.put(('scan_complete', True))
                    return

                name, path, item_type, size = item_data

                self.folder_data[name] = {
                    'size': size,
                    'files': 1,  # Count the file itself
                    'folders': 0,
                    'type': 'File'
                }

                self.update_queue.put(('add_item', name, size, "File", 0, 0))
                processed += 1

                # Update progress every 10 files for performance
                if processed % 10 == 0:
                    self.update_queue.put(('update_progress', processed, total_items, name))

            # Now process folders (slower due to recursive size calculation)
            for item_data in folder_items:
                if self.stop_scan:
                    self.update_queue.put(('scan_complete', True))
                    return

                name, path, item_type = item_data

                self.update_queue.put(('update_progress', processed, total_items, name))

                # Calculate folder size
                size, files, folders = self.get_folder_size(path)

                if self.stop_scan:
                    self.update_queue.put(('scan_complete', True))
                    return

                self.folder_data[name] = {
                    'size': size,
                    'files': files,
                    'folders': folders,
                    'type': 'Folder'
                }

                self.update_queue.put(('add_item', name, size, "Folder", files, folders))
                processed += 1

            # Final progress update
            self.update_queue.put(('update_progress', total_items, total_items, ""))

            # Calculate totals
            total_size = sum(data['size'] for data in self.folder_data.values())
            total_files = sum(data['files'] for data in self.folder_data.values())
            total_folders = sum(data['folders'] for data in self.folder_data.values())

            # Save to cache
            self.save_to_cache(self.current_path)

            elapsed = time.time() - self.scan_start_time
            mins, secs = divmod(int(elapsed), 60)

            self.update_queue.put(('update_status',
                f"Total: {self.format_size(total_size)} | "
                f"{total_files:,} files | {total_folders:,} folders | "
                f"Scanned in {mins:02d}:{secs:02d}"))

            self.update_queue.put(('scan_complete', False))

        except Exception as e:
            self.update_queue.put(('update_status', f"Error scanning folder: {str(e)}"))
            self.update_queue.put(('scan_complete', False))

    def scan_complete(self, cancelled=False):
        """Called when scan is complete"""
        self.progress_bar['value'] = 0
        self.progress_percent.config(text="")
        self.progress_detail.config(text="")
        self.time_label.config(text="")

        if cancelled:
            self.progress_label.config(text="Cancelled")
        else:
            self.progress_label.config(text="Ready")

        self.scan_button.config(state=tk.NORMAL)
        self.refresh_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.is_scanning = False
        self.stop_scan = False

    def add_tree_item(self, name, size, item_type, files, folders):
        """Add item to tree view"""
        if item_type == "Folder":
            self.tree.insert("", "end", text=f"📁 {name}",
                           values=(self.format_size(size), item_type, files, folders))
        else:
            self.tree.insert("", "end", text=f"📄 {name}",
                           values=(self.format_size(size), item_type, "", ""))

    def scan_folder(self, force_refresh=False):
        """Start scanning the current folder"""
        if self.is_scanning:
            return

        # Try to load from cache first (unless force refresh)
        if not force_refresh and self.load_from_cache(self.current_path):
            self.progress_label.config(text="Loaded from cache")
            return

        # Clear UI for new scan
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.folder_data.clear()
        self.clear_details()

        # Setup UI for scanning
        self.is_scanning = True
        self.stop_scan = False
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Starting scan...")
        self.scan_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # Start scan thread
        self.scan_thread = threading.Thread(target=self.scan_folder_thread, daemon=True)
        self.scan_thread.start()

    def refresh_folder(self):
        """Force refresh the current folder"""
        # Clear cache for current path
        if self.current_path in self.directory_cache:
            del self.directory_cache[self.current_path]
            if self.current_path in self.cache_timestamps:
                del self.cache_timestamps[self.current_path]

        # Scan with force refresh
        self.scan_folder(force_refresh=True)

    def stop_scanning(self):
        """Stop the current scan immediately"""
        self.stop_scan = True
        self.progress_label.config(text="Stopping...")
        self.stop_button.config(state=tk.DISABLED)

    def on_drive_change(self, event):
        """Handle drive selection change"""
        # Stop any current scan immediately
        if self.is_scanning:
            self.stop_scan = True
            # Wait briefly for thread to stop (max 200ms)
            if self.scan_thread:
                self.scan_thread.join(timeout=0.2)

        drive = self.drive_var.get()
        self.path_var.set(drive)
        self.current_path = drive
        self.clear_details()
        # Small delay to ensure previous scan is fully stopped
        self.root.after(100, self.scan_folder)

    def on_path_change(self, event):
        """Handle manual path entry"""
        path = self.path_var.get()
        if os.path.exists(path) and os.path.isdir(path):
            # Stop any current scan immediately
            if self.is_scanning:
                self.stop_scan = True
                if self.scan_thread:
                    self.scan_thread.join(timeout=0.2)

            self.current_path = path
            self.clear_details()
            self.root.after(100, self.scan_folder)
        else:
            messagebox.showerror("Error", "Invalid path")
            self.path_var.set(self.current_path)

    def on_item_double_click(self, event):
        """Handle double-click on tree item"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            item_text = item['text']
            item_values = item['values']

            if item_values[1] == "Folder":
                # Stop any current scan immediately
                if self.is_scanning:
                    self.stop_scan = True
                    if self.scan_thread:
                        self.scan_thread.join(timeout=0.2)

                # Remove folder icon and navigate
                folder_name = item_text.replace("📁 ", "")
                new_path = os.path.join(self.current_path, folder_name)

                if os.path.exists(new_path):
                    self.current_path = new_path
                    self.path_var.set(new_path)
                    self.clear_details()
                    self.root.after(100, self.scan_folder)
            else:
                # Double-click on file - open it
                self.open_selected()

    def open_selected(self):
        """Open the selected file or folder"""
        path = self.get_selected_path()
        if path and os.path.exists(path):
            try:
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    import subprocess
                    subprocess.run(['xdg-open', path], check=False)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot open: {str(e)}")

    def go_up(self):
        """Navigate to parent directory"""
        parent = os.path.dirname(self.current_path)
        if parent and os.path.exists(parent):
            # Stop any current scan immediately
            if self.is_scanning:
                self.stop_scan = True
                if self.scan_thread:
                    self.scan_thread.join(timeout=0.2)

            self.current_path = parent
            self.path_var.set(parent)
            self.clear_details()
            self.root.after(100, self.scan_folder)

    def sort_tree(self, col):
        """Sort tree by column"""
        if col == "name":
            items = [(self.tree.item(child)['text'], child) for child in self.tree.get_children('')]
            items.sort()
        elif col == "size":
            items = []
            for child in self.tree.get_children(''):
                item_text = self.tree.item(child)['text']
                name = item_text.replace("📁 ", "").replace("📄 ", "")
                if name in self.folder_data:
                    size = self.folder_data[name]['size']
                    items.append((size, child))
            items.sort(reverse=True)
        elif col == "files":
            items = []
            for child in self.tree.get_children(''):
                item_text = self.tree.item(child)['text']
                name = item_text.replace("📁 ", "").replace("📄 ", "")
                if name in self.folder_data:
                    files = self.folder_data[name]['files']
                    items.append((files, child))
            items.sort(reverse=True)
        elif col == "folders":
            items = []
            for child in self.tree.get_children(''):
                item_text = self.tree.item(child)['text']
                name = item_text.replace("📁 ", "").replace("📄 ", "")
                if name in self.folder_data:
                    folders = self.folder_data[name]['folders']
                    items.append((folders, child))
            items.sort(reverse=True)
        else:
            return

        # Rearrange items in sorted order
        for index, (_, child) in enumerate(items):
            self.tree.move(child, '', index)

    def show_context_menu(self, event):
        """Show context menu on right-click"""
        # Select item under cursor
        item = self.tree.identify('item', event.x, event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def get_selected_path(self):
        """Get the full path of the selected item"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            item_text = item['text']
            item_name = item_text.replace("📁 ", "").replace("📄 ", "")
            return os.path.join(self.current_path, item_name)
        return None

    def delete_selected(self):
        """Delete selected file or folder permanently"""
        path = self.get_selected_path()
        if not path:
            messagebox.showwarning("No Selection", "Please select a file or folder to delete.")
            return

        # Confirmation dialog
        item_type = "folder" if os.path.isdir(path) else "file"
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to permanently delete this {item_type}?\n\n{path}\n\n"
            "This action cannot be undone!",
            icon='warning'
        )

        if result:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

                messagebox.showinfo("Success", f"{item_type.capitalize()} deleted successfully.")

                # Clear cache for current directory and refresh
                if self.current_path in self.directory_cache:
                    del self.directory_cache[self.current_path]
                self.clear_details()
                self.scan_folder(force_refresh=True)

            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete {item_type}: {str(e)}")

    def delete_to_recycle(self):
        """Delete selected file or folder to recycle bin"""
        path = self.get_selected_path()
        if not path:
            messagebox.showwarning("No Selection", "Please select a file or folder to delete.")
            return

        # Confirmation dialog
        item_type = "folder" if os.path.isdir(path) else "file"
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Move this {item_type} to the Recycle Bin?\n\n{path}",
            icon='question'
        )

        if result:
            try:
                send2trash.send2trash(path)
                messagebox.showinfo("Success", f"{item_type.capitalize()} moved to Recycle Bin.")

                # Clear cache for current directory and refresh
                if self.current_path in self.directory_cache:
                    del self.directory_cache[self.current_path]
                self.clear_details()
                self.scan_folder(force_refresh=True)

            except Exception as e:
                messagebox.showerror("Error", f"Failed to move {item_type} to Recycle Bin: {str(e)}")

    def show_properties_dialog(self):
        """Show detailed properties in a dialog"""
        path = self.get_selected_path()
        if not path:
            messagebox.showwarning("No Selection", "Please select a file or folder.")
            return

        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            item_text = item['text']
            item_name = item_text.replace("📁 ", "").replace("📄 ", "")

            if item_name in self.folder_data:
                data = self.folder_data[item_name]

                props = f"Name: {item_name}\n"
                props += f"Path: {path}\n"
                props += f"Type: {data['type']}\n"
                props += f"Size: {self.format_size(data['size'])} ({data['size']:,} bytes)\n"

                if data['type'] == 'Folder':
                    props += f"Files: {data['files']:,}\n"
                    props += f"Folders: {data['folders']:,}\n"

                # Add file system metadata
                if os.path.exists(path):
                    try:
                        stat_info = os.stat(path)
                        props += f"\nCreated: {datetime.fromtimestamp(stat_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}\n"
                        props += f"Modified: {datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
                        props += f"Accessed: {datetime.fromtimestamp(stat_info.st_atime).strftime('%Y-%m-%d %H:%M:%S')}\n"
                    except Exception:
                        pass

                messagebox.showinfo("Properties", props)

if __name__ == "__main__":
    root = tk.Tk()
    app = FolderSizeViewer(root)
    root.mainloop()
