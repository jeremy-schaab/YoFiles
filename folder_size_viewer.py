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

class FolderSizeViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows Folder Size Viewer")
        self.root.geometry("1000x700")
        
        # Store folder sizes for sorting
        self.folder_data = {}
        self.current_path = ""
        self.scan_thread = None
        self.stop_scan = False
        
        # Session cache for scanned directories
        self.directory_cache = {}
        self.cache_timestamps = {}
        
        self.setup_ui()
        self.load_drives()
        
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
        
        # Progress bar
        self.progress_frame = ttk.Frame(self.root)
        self.progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_label = ttk.Label(self.progress_frame, text="Ready")
        self.progress_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Create Treeview with scrollbars
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
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
        
        self.tree.column("#0", width=400)
        self.tree.column("Size", width=150)
        self.tree.column("Type", width=100)
        self.tree.column("Files", width=100)
        self.tree.column("Folders", width=100)
        
        # Pack treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind double-click to open folder
        self.tree.bind("<Double-1>", self.on_item_double_click)
        
        # Bind right-click for context menu
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Create context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Delete", command=self.delete_selected)
        self.context_menu.add_command(label="Delete to Recycle Bin", command=self.delete_to_recycle)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Properties", command=self.show_properties)
        
        # Status bar
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_frame, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X, padx=2, pady=2)
        
    def load_drives(self):
        """Load available drives on Windows"""
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(drive)
        
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
        """Calculate folder size with file and folder counts"""
        total_size = 0
        file_count = 0
        folder_count = 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                folder_count += len(dirnames)
                for filename in filenames:
                    file_count += 1
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, PermissionError):
                        pass
                
                # Check if scan should stop
                if self.stop_scan:
                    break
                    
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
                                        f"{total_files} files | {total_folders} folders | "
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
    
    def scan_folder_thread(self):
        """Scan folder in a separate thread"""
        self.progress_bar.start(10)
        self.progress_label.config(text="Scanning...")
        self.scan_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.folder_data.clear()
        
        try:
            # Get all items in current directory
            items = []
            total_items = 0
            
            for item_name in os.listdir(self.current_path):
                if self.stop_scan:
                    break
                    
                item_path = os.path.join(self.current_path, item_name)
                
                try:
                    if os.path.isdir(item_path):
                        items.append((item_name, item_path, "folder"))
                    else:
                        size = os.path.getsize(item_path)
                        items.append((item_name, item_path, "file", size))
                    total_items += 1
                except (OSError, PermissionError):
                    pass
            
            # Process items
            processed = 0
            for item_data in items:
                if self.stop_scan:
                    break
                
                if len(item_data) == 3:  # Folder
                    name, path, item_type = item_data
                    self.progress_label.config(text=f"Scanning: {name[:50]}...")
                    self.status_label.config(text=f"Processing {processed}/{total_items}: {name}")
                    
                    size, files, folders = self.get_folder_size(path)
                    
                    # Store data
                    self.folder_data[name] = {
                        'size': size,
                        'files': files,
                        'folders': folders,
                        'type': 'Folder'
                    }
                    
                    # Add to tree
                    self.root.after(0, self.add_tree_item, name, size, "Folder", files, folders)
                    
                else:  # File
                    name, path, item_type, size = item_data
                    
                    # Store data
                    self.folder_data[name] = {
                        'size': size,
                        'files': 0,
                        'folders': 0,
                        'type': 'File'
                    }
                    
                    # Add to tree
                    self.root.after(0, self.add_tree_item, name, size, "File", 0, 0)
                
                processed += 1
            
            # Calculate total size
            total_size = sum(data['size'] for data in self.folder_data.values())
            total_files = sum(data['files'] for data in self.folder_data.values())
            total_folders = sum(data['folders'] for data in self.folder_data.values())
            
            # Save to cache
            self.save_to_cache(self.current_path)
            
            self.status_label.config(text=f"Total: {self.format_size(total_size)} | "
                                         f"{total_files} files | {total_folders} folders")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error scanning folder: {str(e)}")
        finally:
            self.progress_bar.stop()
            self.progress_label.config(text="Ready")
            self.scan_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
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
        if self.scan_thread and self.scan_thread.is_alive():
            return
        
        # Try to load from cache first (unless force refresh)
        if not force_refresh and self.load_from_cache(self.current_path):
            self.progress_label.config(text="Loaded from cache")
            return
        
        self.stop_scan = False
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
        """Stop the current scan"""
        self.stop_scan = True
        self.progress_label.config(text="Stopping...")
    
    def on_drive_change(self, event):
        """Handle drive selection change"""
        # Stop any current scan immediately
        if self.scan_thread and self.scan_thread.is_alive():
            self.stop_scan = True
            # Wait briefly for thread to stop (max 100ms)
            self.scan_thread.join(timeout=0.1)
        
        drive = self.drive_var.get()
        self.path_var.set(drive)
        self.current_path = drive
        # Small delay to ensure previous scan is fully stopped
        self.root.after(50, self.scan_folder)
    
    def on_path_change(self, event):
        """Handle manual path entry"""
        path = self.path_var.get()
        if os.path.exists(path) and os.path.isdir(path):
            # Stop any current scan immediately
            if self.scan_thread and self.scan_thread.is_alive():
                self.stop_scan = True
                # Wait briefly for thread to stop (max 100ms)
                self.scan_thread.join(timeout=0.1)
            
            self.current_path = path
            # Small delay to ensure previous scan is fully stopped
            self.root.after(50, self.scan_folder)
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
                if self.scan_thread and self.scan_thread.is_alive():
                    self.stop_scan = True
                    # Wait briefly for thread to stop (max 100ms)
                    self.scan_thread.join(timeout=0.1)
                
                # Remove folder icon and navigate
                folder_name = item_text.replace("📁 ", "")
                new_path = os.path.join(self.current_path, folder_name)
                
                if os.path.exists(new_path):
                    self.current_path = new_path
                    self.path_var.set(new_path)
                    # Small delay to ensure previous scan is fully stopped
                    self.root.after(50, self.scan_folder)
    
    def go_up(self):
        """Navigate to parent directory"""
        parent = os.path.dirname(self.current_path)
        if parent and os.path.exists(parent):
            # Stop any current scan immediately
            if self.scan_thread and self.scan_thread.is_alive():
                self.stop_scan = True
                # Wait briefly for thread to stop (max 100ms)
                self.scan_thread.join(timeout=0.1)
            
            self.current_path = parent
            self.path_var.set(parent)
            # Small delay to ensure previous scan is fully stopped
            self.root.after(50, self.scan_folder)
    
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
                self.scan_folder(force_refresh=True)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to move {item_type} to Recycle Bin: {str(e)}")
    
    def show_properties(self):
        """Show properties of selected item"""
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
                props += f"Size: {self.format_size(data['size'])}\n"
                
                if data['type'] == 'Folder':
                    props += f"Files: {data['files']}\n"
                    props += f"Folders: {data['folders']}\n"
                
                messagebox.showinfo("Properties", props)

if __name__ == "__main__":
    root = tk.Tk()
    app = FolderSizeViewer(root)
    root.mainloop()