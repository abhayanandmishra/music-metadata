#!/usr/bin/env python3
"""GUI for Music Organizer."""

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

from . import config
from .core import (
    build_filename,
    ensure_music_dirs,
    find_music_files,
    format_metadata_block,
    process_file,
    process_files_batch,
)
from .core.metadata import (
    clean_metadata,
    fill_missing_metadata,
    metadata_changed,
    write_metadata,
)


class MusicRenamerGUI(tk.Tk):
    """GUI for Music Organizer using tkinter."""
    
    def __init__(self):
        super().__init__()
        self.title("Music Organizer")
        self.geometry("980x720")
        self.minsize(880, 620)

        app_config = config.CONFIG.get("application", {})
        default_pattern = app_config.get("default_pattern", "{album} - {title}")
        default_dry_run = app_config.get("default_dry_run", True)
        default_write_metadata = app_config.get("write_metadata_default", True)

        self.folder_var = tk.StringVar(value="")
        self.pattern_var = tk.StringVar(value=default_pattern)
        self.search_var = tk.StringVar(value="")
        self.dry_run_var = tk.BooleanVar(value=default_dry_run)
        self.write_metadata_var = tk.BooleanVar(value=default_write_metadata)

        self.files = []
        self.records = {}
        self.filtered = []
        self.current_path = None

        self.build_ui()

    def build_ui(self):
        """Build the GUI layout."""
        pad = {"padx": 10, "pady": 6}
        title_label = tk.Label(self, text="Music Organizer", font=("Segoe UI", 16, "bold"))
        title_label.pack(anchor="w", **pad)

        folder_frame = tk.Frame(self)
        folder_frame.pack(fill="x", **pad)
        tk.Label(folder_frame, text="Folder:").pack(anchor="w")

        folder_row = tk.Frame(folder_frame)
        folder_row.pack(fill="x")
        tk.Entry(folder_row, textvariable=self.folder_var).pack(side="left", fill="x", expand=True)
        tk.Button(folder_row, text="Browse", command=self.browse_folder).pack(side="left", padx=(8, 0))
        tk.Button(folder_row, text="Scan", command=self.scan_files).pack(side="left", padx=(8, 0))

        settings = tk.Frame(self)
        settings.pack(fill="x", **pad)
        tk.Label(settings, text="Default Name Pattern:").grid(row=0, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.pattern_var).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        settings.columnconfigure(1, weight=1)

        tk.Checkbutton(
            settings,
            text="Dry run",
            variable=self.dry_run_var,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        tk.Checkbutton(
            settings,
            text="Write cleaned metadata",
            variable=self.write_metadata_var,
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))

        search_frame = tk.Frame(self)
        search_frame.pack(fill="x", **pad)
        tk.Label(search_frame, text="Search / Filter:").pack(side="left")
        tk.Entry(search_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.search_var.trace_add("write", lambda *_: self.refresh_file_list())

        body = tk.PanedWindow(self, orient="horizontal", sashrelief="raised")
        body.pack(fill="both", expand=True, **pad)

        list_frame = tk.Frame(body)
        tk.Label(list_frame, text="Music Files").pack(anchor="w")
        self.file_list = tk.Listbox(list_frame, exportselection=False)
        self.file_list.pack(fill="both", expand=True)
        self.file_list.bind("<<ListboxSelect>>", self.on_file_select)
        body.add(list_frame, minsize=300)

        edit_frame = tk.Frame(body)
        tk.Label(edit_frame, text="Editable Metadata").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.meta_vars = {key: tk.StringVar(value="") for key in config.METADATA_KEYS if key != "original"}
        row = 1
        for key in ("artist", "title", "album", "track", "genre", "year", "albumartist", "composer", "publisher", "comments"):
            tk.Label(edit_frame, text=f"{key.capitalize()}:").grid(row=row, column=0, sticky="w", pady=4)
            tk.Entry(edit_frame, textvariable=self.meta_vars[key]).grid(row=row, column=1, sticky="ew", pady=4)
            row += 1

        edit_frame.columnconfigure(1, weight=1)

        tk.Button(edit_frame, text="Apply Clean", command=self.apply_clean_selected).grid(row=row, column=0, pady=(8, 0), sticky="w")
        tk.Button(edit_frame, text="Save Metadata", command=self.save_selected_metadata).grid(row=row, column=1, pady=(8, 0), sticky="w")
        row += 1
        tk.Button(edit_frame, text="Process Selected", command=self.rename_selected).grid(row=row, column=0, pady=(8, 0), sticky="w")
        tk.Button(edit_frame, text="Process All", command=self.process_all).grid(row=row, column=1, pady=(8, 0), sticky="w")
        row += 1

        compare_frame = tk.Frame(edit_frame)
        compare_frame.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        compare_frame.columnconfigure(0, weight=1)
        compare_frame.columnconfigure(1, weight=1)

        tk.Label(compare_frame, text="Original (Read-only)").grid(row=0, column=0, sticky="w", padx=(0, 6))
        tk.Label(compare_frame, text="Current (Read-only)").grid(row=0, column=1, sticky="w", padx=(6, 0))

        self.original_box = tk.Text(compare_frame, height=10, wrap="word")
        self.original_box.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(4, 0))
        self.current_box = tk.Text(compare_frame, height=10, wrap="word")
        self.current_box.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(4, 0))
        self.original_box.configure(state="disabled")
        self.current_box.configure(state="disabled")

        body.add(edit_frame)

        output_header = tk.Frame(self)
        output_header.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(output_header, text="Output:").pack(side="left")
        tk.Button(output_header, text="Clear", command=self.clear_output).pack(side="right")
        self.output = tk.Text(self, height=11, wrap="word")
        self.output.pack(fill="both", expand=False, padx=10, pady=(0, 10))
        self.output.configure(state="disabled")

    def browse_folder(self):
        """Browse for folder."""
        directory = filedialog.askdirectory(title="Select music folder")
        if directory:
            self.folder_var.set(directory)
            self.scan_files()

    def clear_output(self):
        """Clear output text box."""
        self.output.configure(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.configure(state="disabled")

    def _set_readonly_text(self, widget: tk.Text, content: str):
        """Set text in read-only widget."""
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state="disabled")

    def clear_metadata_views(self):
        """Clear metadata comparison views."""
        self._set_readonly_text(self.original_box, "")
        self._set_readonly_text(self.current_box, "")

    def refresh_metadata_views(self):
        """Refresh metadata comparison views."""
        if not self.current_path or self.current_path not in self.records:
            self.clear_metadata_views()
            return

        original = self.records[self.current_path].get("original", {})
        current = self.records[self.current_path].get("current", {})
        audio_quality = self.records[self.current_path].get("audio_quality", {})
        original_text = format_metadata_block(self.current_path, original, "Original", audio_quality=audio_quality)
        current_text = format_metadata_block(self.current_path, current, "Current", audio_quality=audio_quality)
        self._set_readonly_text(self.original_box, original_text)
        self._set_readonly_text(self.current_box, current_text)

    def log(self, text):
        """Write to output log."""
        self.output.configure(state="normal")
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.output.configure(state="disabled")

    def scan_files(self):
        """Scan folder for music files."""
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Folder required", "Please select a folder first.")
            return

        folder_path = Path(folder)
        if not folder_path.exists():
            messagebox.showerror("Folder not found", f"Folder does not exist: {folder_path}")
            return

        self.output.configure(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.configure(state="disabled")
        self.clear_metadata_views()

        self.files = find_music_files(folder_path)
        self.records.clear()

        for path in self.files:
            original, completed, audio_quality = process_file(path)
            self.records[path] = {"original": original, "current": completed, "audio_quality": audio_quality}

        self.refresh_file_list()
        self.log(f"Loaded {len(self.files)} file(s).")

    def refresh_file_list(self):
        """Refresh the file list based on search filter."""
        query = self.search_var.get().strip().lower()
        self.file_list.delete(0, tk.END)
        self.filtered = []

        for path in self.files:
            record = self.records.get(path, {})
            metadata = record.get("current", {})
            haystack = " ".join(
                [path.name]
                + [str(metadata.get(k, "")) for k in ("artist", "title", "album", "genre", "year")]
            ).lower()
            if query and query not in haystack:
                continue

            self.filtered.append(path)
            self.file_list.insert(tk.END, path.name)

    def on_file_select(self, _event=None):
        """Handle file selection from list."""
        selection = self.file_list.curselection()
        if not selection:
            self.current_path = None
            self.clear_metadata_views()
            return

        index = selection[0]
        self.current_path = self.filtered[index]
        current = self.records[self.current_path]["current"]
        audio_quality = self.records[self.current_path].get("audio_quality", {})

        for key in self.meta_vars:
            self.meta_vars[key].set(current.get(key, ""))

        self.refresh_metadata_views()
        self.log(format_metadata_block(self.current_path, self.records[self.current_path]["original"], "Original", audio_quality=audio_quality))
        self.log(format_metadata_block(self.current_path, current, "Current", audio_quality=audio_quality))

    def apply_clean_selected(self):
        """Apply cleaning rules to selected file."""
        if not self.current_path:
            self.log("Select a file first.")
            return

        metadata = {key: self.meta_vars[key].get().strip() for key in self.meta_vars}
        metadata["original"] = self.current_path.stem
        metadata = fill_missing_metadata(self.current_path, clean_metadata(metadata))
        self.records[self.current_path]["current"] = metadata

        for key in self.meta_vars:
            self.meta_vars[key].set(metadata.get(key, ""))
        self.refresh_metadata_views()
        self.log(f"Applied cleaning rules to: {self.current_path.name}")

    def save_selected_metadata(self):
        """Save metadata for selected file."""
        if not self.current_path:
            self.log("Select a file first.")
            return

        metadata = {key: self.meta_vars[key].get().strip() for key in self.meta_vars}
        metadata["original"] = self.current_path.stem
        metadata = fill_missing_metadata(self.current_path, clean_metadata(metadata))

        try:
            write_metadata(self.current_path, metadata)
            self.records[self.current_path]["current"] = metadata
            self.refresh_metadata_views()
            self.log(f"Saved metadata for: {self.current_path.name}")
        except Exception as exc:
            self.log(f"Metadata save failed: {exc}")
            messagebox.showerror("Metadata save failed", str(exc))

    def rename_selected(self):
        """Rename selected file."""
        if not self.current_path:
            self.log("Select a file first.")
            return

        pattern = self.pattern_var.get().strip() or "{album} - {title}"
        metadata = {key: self.meta_vars[key].get().strip() for key in self.meta_vars}
        metadata["original"] = self.current_path.stem
        metadata = fill_missing_metadata(self.current_path, clean_metadata(metadata))

        original = self.records.get(self.current_path, {}).get("original", {})
        changed = metadata_changed(original, metadata)

        if changed:
            if self.dry_run_var.get():
                self.log("Would update metadata tags")
            elif self.write_metadata_var.get():
                try:
                    write_metadata(self.current_path, metadata)
                    self.log(f"Updated metadata tags for: {self.current_path.name}")
                except Exception as exc:
                    self.log(f"Metadata update failed: {exc}")
                    messagebox.showerror("Metadata update failed", str(exc))
                    return

        self.records[self.current_path]["current"] = metadata
        for key in self.meta_vars:
            self.meta_vars[key].set(metadata.get(key, ""))

        candidate = build_filename(pattern, metadata) + self.current_path.suffix.lower()

        if self.current_path.name == candidate:
            self.refresh_metadata_views()
            self.log(f"No rename needed for: {self.current_path.name}")
            return

        if self.dry_run_var.get():
            self.refresh_metadata_views()
            self.log(f"Would rename: {self.current_path.name} -> {candidate}")
            return

        try:
            new_path = self.current_path.with_name(candidate)
            if new_path.exists():
                self.log(f"Rename skipped (target exists): {candidate}")
                return

            old_path = self.current_path
            old_path.rename(new_path)
            record = self.records.pop(old_path)
            self.current_path = new_path
            record["current"]["original"] = new_path.stem
            self.records[new_path] = record
            self.files = [new_path if p == old_path else p for p in self.files]
            self.refresh_file_list()
            self.refresh_metadata_views()
            self.log(f"Renamed: {new_path.name}")
        except Exception as exc:
            self.log(f"Rename failed: {exc}")
            messagebox.showerror("Rename failed", str(exc))

    def process_all(self):
        """Process all files in scanned folder."""
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Folder required", "Please select a folder first.")
            return

        try:
            music_root = config.DEFAULT_ROOT
            _, op_dir, nc_dir = ensure_music_dirs(music_root)
            report_path = music_root / "music_organizer_report.json"
            is_dry_run = self.dry_run_var.get()
            
            files = find_music_files(Path(folder))
            summary = process_files_batch(
                files,
                self.pattern_var.get().strip() or "{album} - {title}",
                dry_run=is_dry_run,
                write_back=self.write_metadata_var.get(),
                apply_changes=not is_dry_run,
                op_dir=op_dir if not is_dry_run else None,
                nc_dir=nc_dir if not is_dry_run else None,
            )
            
            processed = summary["totals"]["processed"]
            self.log(f"Processed {processed} file(s). Report: {report_path}")
            self.scan_files()
        except Exception as exc:
            self.log(f"Process failed: {exc}")
            messagebox.showerror("Process failed", str(exc))


def run_gui():
    """Run the GUI application."""
    config.load_config()
    app = MusicRenamerGUI()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
