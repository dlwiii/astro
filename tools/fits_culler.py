#!/usr/bin/env python3
"""
FITS File Culler - Quick preview and delete bad frames
Usage: python3 fits_culler.py <directory>

Keyboard shortcuts:
  Right/Space      - Next image
  Left             - Previous image
  PgDn/Shift+Right - Jump forward 10 frames
  PgUp/Shift+Left  - Jump backward 10 frames
  D                - Delete current file
  U                - Undo delete (restore last deleted)
  R                - Restore all deleted files
  C                - Commit deletions and reload (permanent!)
  Q/Escape         - Quit
  H                - Toggle histogram stretch
"""

import sys
import os
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import numpy as np
from astropy.io import fits

class FITSCuller:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.trash_dir = self.directory / '.trash'
        self.trash_dir.mkdir(exist_ok=True)

        # Find all FITS files
        self.files = sorted(list(self.directory.glob('*.fit')) +
                          list(self.directory.glob('*.fits')))

        if not self.files:
            print(f"No FITS files found in {directory}")
            sys.exit(1)

        self.current_index = 0
        self.auto_stretch = True
        self.deleted_files = set()

        # Setup GUI
        self.root = tk.Tk()
        self.root.title(f"FITS Culler - {len(self.files)} files")
        self.root.configure(bg='black')

        # Info label
        self.info_label = tk.Label(self.root, text="", fg='yellow', bg='black',
                                   font=('monospace', 12))
        self.info_label.pack(pady=5)

        # Main container with thumbnails
        main_frame = tk.Frame(self.root, bg='black')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left sidebar - previous thumbnails
        self.left_frame = tk.Frame(main_frame, bg='#0a0a0a', width=150)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        self.left_frame.pack_propagate(False)

        tk.Label(self.left_frame, text="Previous", fg='gray', bg='#0a0a0a',
                font=('monospace', 9)).pack(pady=5)

        self.left_canvas = tk.Canvas(self.left_frame, bg='#0a0a0a',
                                     highlightthickness=0)
        self.left_canvas.pack(fill=tk.BOTH, expand=True)
        self.left_canvas.bind('<Button-1>', self.on_left_click)

        # Center - main image
        center_frame = tk.Frame(main_frame, bg='black')
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(center_frame, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Right sidebar - next thumbnails
        self.right_frame = tk.Frame(main_frame, bg='#0a0a0a', width=150)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        self.right_frame.pack_propagate(False)

        tk.Label(self.right_frame, text="Next", fg='gray', bg='#0a0a0a',
                font=('monospace', 9)).pack(pady=5)

        self.right_canvas = tk.Canvas(self.right_frame, bg='#0a0a0a',
                                      highlightthickness=0)
        self.right_canvas.pack(fill=tk.BOTH, expand=True)
        self.right_canvas.bind('<Button-1>', self.on_right_click)

        # Status label
        self.status_label = tk.Label(self.root, text="", fg='yellow', bg='black',
                                     font=('monospace', 10))
        self.status_label.pack(pady=5)

        # Cache for thumbnails
        self.thumbnail_cache = {}
        self.thumbnail_photos = []  # Keep references
        self.left_thumb_positions = {}  # Maps y-range to frame index
        self.right_thumb_positions = {}  # Maps y-range to frame index

        # Help text
        help_text = "→/Space: Next | ←: Prev | PgDn/Shift+→: +10 | PgUp/Shift+←: -10 | D: Delete | U: Undo | R: Restore all | C: Commit & reload | H: Toggle stretch | Q: Quit"
        self.help_label = tk.Label(self.root, text=help_text, fg='gray', bg='black',
                                   font=('monospace', 9))
        self.help_label.pack(pady=5)

        # Bind keys
        self.root.bind('<Right>', lambda e: self.next_image())
        self.root.bind('<Left>', lambda e: self.prev_image())
        self.root.bind('<space>', lambda e: self.next_image())
        self.root.bind('<Next>', lambda e: self.jump_forward())  # Page Down
        self.root.bind('<Prior>', lambda e: self.jump_backward())  # Page Up
        self.root.bind('<Shift-Right>', lambda e: self.jump_forward())
        self.root.bind('<Shift-Left>', lambda e: self.jump_backward())
        self.root.bind('d', lambda e: self.delete_current())
        self.root.bind('D', lambda e: self.delete_current())
        self.root.bind('u', lambda e: self.undo_delete())
        self.root.bind('U', lambda e: self.undo_delete())
        self.root.bind('r', lambda e: self.undo_all())
        self.root.bind('R', lambda e: self.undo_all())
        self.root.bind('c', lambda e: self.commit_deletions())
        self.root.bind('C', lambda e: self.commit_deletions())
        self.root.bind('h', lambda e: self.toggle_stretch())
        self.root.bind('H', lambda e: self.toggle_stretch())
        self.root.bind('q', lambda e: self.quit())
        self.root.bind('Q', lambda e: self.quit())
        self.root.bind('<Escape>', lambda e: self.quit())

        # Set window size
        self.root.geometry('1400x900')

        # Wait for window to render before loading first image
        self.root.update()
        self.root.after(100, self.show_image)

    def load_fits(self, filepath):
        """Load and process FITS file"""
        with fits.open(filepath) as hdul:
            data = hdul[0].data
            header = hdul[0].header

            # Handle different data shapes
            if len(data.shape) == 3:
                # Color image - take first channel or average
                if data.shape[0] == 3:
                    # RGB
                    data = data[1]  # Use green channel
                else:
                    data = data[0]

            # Auto-stretch (default - better for previewing)
            if self.auto_stretch:
                # Robust percentile stretch - works well for light frames
                vmin, vmax = np.percentile(data, [1, 99.9])
                data = np.clip((data - vmin) / (vmax - vmin) * 255, 0, 255)
            else:
                # Linear stretch - shows raw data
                vmin, vmax = data.min(), data.max()
                data = np.clip((data - vmin) / (vmax - vmin) * 255, 0, 255)

            # Convert to uint8
            data = data.astype(np.uint8)

            # Get basic info
            info = {
                'exposure': header.get('EXPOSURE', 'N/A'),
                'date': header.get('DATE-OBS', 'N/A'),
                'temp': header.get('CCD-TEMP', 'N/A')
            }

            return data, info

    def get_thumbnail(self, index, size=120, force_refresh=False):
        """Get thumbnail for file at index"""
        if index < 0 or index >= len(self.files):
            return None

        filepath = self.files[index]
        is_deleted = filepath in self.deleted_files

        # Always regenerate if deletion status has changed
        cache_key = (filepath, size, is_deleted)
        if not force_refresh and cache_key in self.thumbnail_cache:
            return self.thumbnail_cache[cache_key]

        try:
            # Load from trash if deleted, otherwise from original location
            if is_deleted:
                actual_path = self.trash_dir / filepath.name
            else:
                actual_path = filepath

            data, _ = self.load_fits(actual_path)
            img = Image.fromarray(data)
            img.thumbnail((size, size), Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            self.thumbnail_cache[cache_key] = photo
            return photo

        except:
            return None

    def update_thumbnails(self):
        """Update thumbnail sidebars"""
        self.thumbnail_photos = []  # Clear references
        self.left_thumb_positions = {}
        self.right_thumb_positions = {}

        # Thumbnail settings (sized to fit ~7 images)
        thumb_display_size = 100
        thumb_spacing = 110
        y_start = 5
        max_thumbs = 7  # Show up to 7 thumbnails per sidebar

        # Left sidebar - previous images (most recent at top)
        self.left_canvas.delete('all')
        y_offset = y_start
        count = 0

        # Show previous frames in reverse order (most recent first)
        for i in range(self.current_index - 1, -1, -1):  # Count backwards
            if count >= max_thumbs:
                break

            thumb = self.get_thumbnail(i, size=thumb_display_size)
            if thumb:
                self.thumbnail_photos.append(thumb)
                img_y = y_offset + thumb_display_size//2
                self.left_canvas.create_image(75, img_y, image=thumb)

                # Add frame number (red if deleted, yellow otherwise)
                text_color = 'red' if self.files[i] in self.deleted_files else 'yellow'
                self.left_canvas.create_text(10, y_offset + 5, text=str(i+1),
                                            fill=text_color, font=('monospace', 10, 'bold'),
                                            anchor='nw')

                # Track position for click detection
                self.left_thumb_positions[(y_offset, y_offset + thumb_display_size)] = i

                y_offset += thumb_spacing
                count += 1

        # Right sidebar - next images (nearest at top)
        self.right_canvas.delete('all')
        y_offset = y_start
        count = 0

        # Show next frames in forward order from top
        end_index = min(self.current_index + 1 + max_thumbs, len(self.files))
        for i in range(self.current_index + 1, end_index):
            try:
                thumb = self.get_thumbnail(i, size=thumb_display_size)
                if thumb:
                    self.thumbnail_photos.append(thumb)
                    img_y = y_offset + thumb_display_size//2
                    self.right_canvas.create_image(75, img_y, image=thumb)

                    # Add frame number (red if deleted, yellow otherwise)
                    text_color = 'red' if self.files[i] in self.deleted_files else 'yellow'
                    self.right_canvas.create_text(10, y_offset + 5, text=str(i+1),
                                                 fill=text_color, font=('monospace', 10, 'bold'),
                                                 anchor='nw')

                    # Track position for click detection
                    self.right_thumb_positions[(y_offset, y_offset + thumb_display_size)] = i

                    y_offset += thumb_spacing
                    count += 1
            except Exception as e:
                print(f"Error creating thumbnail {i}: {e}")
                import traceback
                traceback.print_exc()

    def show_image(self):
        """Display current image"""
        if self.current_index >= len(self.files):
            self.status_label.config(text="No more files!")
            return

        filepath = self.files[self.current_index]
        is_deleted = filepath in self.deleted_files

        try:
            # Load from trash if deleted, otherwise from original location
            if is_deleted:
                actual_path = self.trash_dir / filepath.name
            else:
                actual_path = filepath

            # Load FITS
            data, info = self.load_fits(actual_path)

            # Convert to PIL Image
            img = Image.fromarray(data)

            # Resize to fit canvas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width > 1 and canvas_height > 1:
                img.thumbnail((canvas_width - 20, canvas_height - 20), Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            self.photo = ImageTk.PhotoImage(img)

            # Clear canvas and show image
            self.canvas.delete('all')
            self.canvas.create_image(canvas_width // 2, canvas_height // 2,
                                    image=self.photo, anchor=tk.CENTER)

            # Update info
            deleted_str = " [DELETED]" if filepath in self.deleted_files else ""
            info_text = (f"File {self.current_index + 1}/{len(self.files)}: {filepath.name}{deleted_str}\n"
                        f"Exposure: {info['exposure']}s | Date: {info['date']} | Temp: {info['temp']}°C")

            # Change text color to red if deleted, yellow otherwise
            text_color = 'red' if filepath in self.deleted_files else 'yellow'
            self.info_label.config(text=info_text, fg=text_color)

            # Update status
            deleted_count = len(self.deleted_files)
            remaining = len(self.files) - deleted_count
            self.status_label.config(text=f"Deleted: {deleted_count} | Remaining: {remaining} | Stretch: {'ON' if self.auto_stretch else 'OFF'}")

            # Update thumbnails
            self.update_thumbnails()

        except Exception as e:
            self.info_label.config(text=f"Error loading {filepath.name}: {str(e)}")

    def next_image(self):
        """Go to next image (cycles back to start)"""
        self.current_index = (self.current_index + 1) % len(self.files)
        self.show_image()

    def prev_image(self):
        """Go to previous image (cycles to end)"""
        self.current_index = (self.current_index - 1) % len(self.files)
        self.show_image()

    def jump_forward(self, count=10):
        """Jump forward multiple frames"""
        self.current_index = min(self.current_index + count, len(self.files) - 1)
        self.show_image()

    def jump_backward(self, count=10):
        """Jump backward multiple frames"""
        self.current_index = max(self.current_index - count, 0)
        self.show_image()

    def delete_current(self):
        """Toggle deletion status of current file"""
        filepath = self.files[self.current_index]

        if filepath in self.deleted_files:
            # File is already deleted - restore it
            trash_path = self.trash_dir / filepath.name
            try:
                shutil.move(str(trash_path), str(filepath))
                self.deleted_files.remove(filepath)

                # Clear cache entries only for this specific file
                keys_to_remove = [key for key in self.thumbnail_cache if key[0] == filepath]
                for key in keys_to_remove:
                    del self.thumbnail_cache[key]

                self.status_label.config(text=f"Restored: {filepath.name}")
                self.show_image()
            except Exception as e:
                messagebox.showerror("Error", f"Could not restore file: {str(e)}")
        else:
            # File is not deleted - delete it
            try:
                # Move to trash
                trash_path = self.trash_dir / filepath.name
                shutil.move(str(filepath), str(trash_path))
                self.deleted_files.add(filepath)

                # Clear cache entries only for this specific file
                keys_to_remove = [key for key in self.thumbnail_cache if key[0] == filepath]
                for key in keys_to_remove:
                    del self.thumbnail_cache[key]

                self.status_label.config(text=f"Deleted: {filepath.name}")

                # Refresh display at current position (don't auto-advance)
                self.show_image()

            except Exception as e:
                messagebox.showerror("Error", f"Could not delete file: {str(e)}")

    def undo_delete(self):
        """Restore last deleted file"""
        if not self.deleted_files:
            self.status_label.config(text="No files to restore!")
            return

        # Get most recent deleted file
        filepath = self.deleted_files.pop()
        trash_path = self.trash_dir / filepath.name

        try:
            shutil.move(str(trash_path), str(filepath))

            # Clear cache entries only for this specific file
            keys_to_remove = [key for key in self.thumbnail_cache if key[0] == filepath]
            for key in keys_to_remove:
                del self.thumbnail_cache[key]

            self.status_label.config(text=f"Restored: {filepath.name}")
            self.show_image()
        except Exception as e:
            messagebox.showerror("Error", f"Could not restore file: {str(e)}")
            self.deleted_files.add(filepath)  # Re-add if restore failed

    def undo_all(self):
        """Restore all deleted files"""
        if not self.deleted_files:
            self.status_label.config(text="No files to restore!")
            return

        restore_count = len(self.deleted_files)
        failed_files = []
        restored_files = []

        # Restore all deleted files
        for filepath in list(self.deleted_files):
            trash_path = self.trash_dir / filepath.name
            try:
                shutil.move(str(trash_path), str(filepath))
                self.deleted_files.remove(filepath)
                restored_files.append(filepath)
            except Exception as e:
                failed_files.append((filepath.name, str(e)))

        # Clear cache entries only for restored files
        for filepath in restored_files:
            keys_to_remove = [key for key in self.thumbnail_cache if key[0] == filepath]
            for key in keys_to_remove:
                del self.thumbnail_cache[key]

        if failed_files:
            error_msg = "Failed to restore:\n" + "\n".join([f"{f}: {e}" for f, e in failed_files])
            messagebox.showerror("Error", error_msg)
            self.status_label.config(text=f"Restored {restore_count - len(failed_files)}/{restore_count} files")
        else:
            self.status_label.config(text=f"Restored all {restore_count} files")

        self.show_image()

    def commit_deletions(self):
        """Permanently delete trash and reload file list"""
        if not self.deleted_files:
            self.status_label.config(text="No deletions to commit!")
            return

        deleted_count = len(self.deleted_files)
        result = messagebox.askyesno(
            "Commit Deletions",
            f"Permanently delete {deleted_count} files from trash and reload?\n\n"
            "This cannot be undone!"
        )

        if not result:
            return

        try:
            # Permanently delete all files in trash
            for trash_file in self.trash_dir.glob('*'):
                if trash_file.is_file():
                    trash_file.unlink()

            # Clear deleted files set
            self.deleted_files.clear()

            # Reload file list
            self.files = sorted(list(self.directory.glob('*.fit')) +
                              list(self.directory.glob('*.fits')))

            if not self.files:
                messagebox.showinfo("No Files", "No FITS files remaining!")
                self.quit()
                return

            # Update window title
            self.root.title(f"FITS Culler - {len(self.files)} files")

            # Reset to valid index
            if self.current_index >= len(self.files):
                self.current_index = len(self.files) - 1

            # Clear caches
            self.thumbnail_cache.clear()

            self.status_label.config(text=f"Committed: {deleted_count} files permanently deleted")
            self.show_image()

        except Exception as e:
            messagebox.showerror("Error", f"Could not commit deletions: {str(e)}")

    def toggle_stretch(self):
        """Toggle histogram stretch"""
        self.auto_stretch = not self.auto_stretch
        self.show_image()

    def on_left_click(self, event):
        """Handle click on left sidebar thumbnail"""
        y = event.y
        for (y_start, y_end), frame_index in self.left_thumb_positions.items():
            if y_start <= y <= y_end:
                self.current_index = frame_index
                self.show_image()
                return

    def on_right_click(self, event):
        """Handle click on right sidebar thumbnail"""
        y = event.y
        for (y_start, y_end), frame_index in self.right_thumb_positions.items():
            if y_start <= y <= y_end:
                self.current_index = frame_index
                self.show_image()
                return

    def quit(self):
        """Quit application"""
        if self.deleted_files:
            result = messagebox.askyesno(
                "Confirm Quit",
                f"{len(self.deleted_files)} files in trash.\n"
                "They can be restored from .trash folder.\n"
                "Quit anyway?"
            )
            if not result:
                return

        self.root.destroy()

    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        print(f"\nUsage: {sys.argv[0]} <directory>")
        sys.exit(1)

    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a directory")
        sys.exit(1)

    app = FITSCuller(directory)
    app.run()
