"""A lightweight file explorer application built with Tkinter.

This module provides a desktop GUI similar to the Windows File Explorer that lets
users browse directories, inspect file metadata, and open files with their
associated applications.
"""

from __future__ import annotations

import os
import platform
import string
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import tkinter as tk
from tkinter import messagebox, ttk


@dataclass
class FileItem:
    """Represents a file system entry with metadata for display."""

    name: str
    path: Path
    is_dir: bool
    size: int
    modified: datetime

    @property
    def type_label(self) -> str:
        return "Folder" if self.is_dir else self.path.suffix.lower() or "File"

    @property
    def size_label(self) -> str:
        if self.is_dir:
            return ""
        if self.size < 1024:
            return f"{self.size} B"
        if self.size < 1024 ** 2:
            return f"{self.size / 1024:.1f} KB"
        if self.size < 1024 ** 3:
            return f"{self.size / (1024 ** 2):.1f} MB"
        return f"{self.size / (1024 ** 3):.1f} GB"

    @property
    def modified_label(self) -> str:
        return self.modified.strftime("%Y-%m-%d %H:%M")


class FileViewerApp(tk.Tk):
    """Main window that renders the file viewer interface."""

    def __init__(self) -> None:
        super().__init__()
        self.title("File Viewer")
        self.geometry("1100x650")
        self.minsize(900, 550)

        self.current_path = Path.home()
        self._history: List[Path] = []
        self._history_index = -1

        self._create_widgets()
        self._populate_drives()
        self._navigate_to(self.current_path, add_history=True)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _create_widgets(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="nsew")

        self.back_button = ttk.Button(toolbar, text="◀", width=3, command=self._go_back)
        self.forward_button = ttk.Button(toolbar, text="▶", width=3, command=self._go_forward)
        self.up_button = ttk.Button(toolbar, text="⬆", width=3, command=self._go_up)
        for widget in (self.back_button, self.forward_button, self.up_button):
            widget.pack(side=tk.LEFT, padx=(2, 0), pady=4)

        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(toolbar, textvariable=self.path_var)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        path_entry.bind("<Return>", self._on_path_entry)

        refresh_button = ttk.Button(toolbar, text="Refresh", command=self._refresh)
        refresh_button.pack(side=tk.LEFT, padx=4)

        # Paned layout
        panes = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        panes.grid(row=1, column=0, columnspan=2, sticky="nsew")

        # Directory tree
        tree_frame = ttk.Frame(panes)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.dir_tree = ttk.Treeview(tree_frame, columns=("#0",), show="tree")
        self.dir_tree.heading("#0", text="Folders")
        self.dir_tree.bind("<<TreeviewOpen>>", self._on_tree_expand)
        self.dir_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.dir_tree.grid(row=0, column=0, sticky="nsew")

        tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.dir_tree.yview)
        self.dir_tree.configure(yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.grid(row=0, column=1, sticky="ns")

        panes.add(tree_frame, weight=1)

        # File list
        list_frame = ttk.Frame(panes)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        columns = ("type", "size", "modified")
        self.file_list = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.file_list.heading("type", text="Type")
        self.file_list.heading("size", text="Size")
        self.file_list.heading("modified", text="Modified")
        self.file_list.column("type", width=150, anchor=tk.W)
        self.file_list.column("size", width=100, anchor=tk.E)
        self.file_list.column("modified", width=150, anchor=tk.W)
        self.file_list.grid(row=0, column=0, sticky="nsew")

        list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=list_scrollbar.set)
        list_scrollbar.grid(row=0, column=1, sticky="ns")

        self.file_list.bind("<Double-1>", self._on_file_activate)

        panes.add(list_frame, weight=3)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status_var, anchor=tk.W)
        status_bar.grid(row=2, column=0, columnspan=2, sticky="nsew")

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _populate_drives(self) -> None:
        self.dir_tree.delete(*self.dir_tree.get_children())
        for drive in self._iter_roots():
            node = self.dir_tree.insert("", tk.END, text=str(drive), values=(str(drive),))
            self.dir_tree.insert(node, tk.END, text="loading", values=("loading",))

    def _iter_roots(self) -> Iterable[Path]:
        system = platform.system()
        if system == "Windows":
            for letter in string.ascii_uppercase:
                drive = Path(f"{letter}:/")
                if drive.exists():
                    yield drive
        else:
            yield Path("/")
            home = Path.home()
            if home != Path("/"):
                yield home

    def _navigate_to(self, path: Path, add_history: bool = False) -> None:
        try:
            path = path.resolve()
        except OSError:
            messagebox.showerror("Navigation error", f"Cannot access {path}")
            return

        if not path.exists():
            messagebox.showerror("Not found", f"{path} does not exist")
            return

        if add_history:
            del self._history[self._history_index + 1 :]
            self._history.append(path)
            self._history_index += 1

        self.current_path = path
        self.path_var.set(str(path))
        self._update_toolbar_state()
        self._refresh_file_list()
        self.status_var.set(f"Showing {path}")
        self._ensure_tree_selection(path)

    def _refresh_file_list(self) -> None:
        entries = list(self._iter_directory(self.current_path))
        entries.sort(key=lambda item: (not item.is_dir, item.name.lower()))

        self.file_list.delete(*self.file_list.get_children())
        for entry in entries:
            self.file_list.insert(
                "",
                tk.END,
                iid=str(entry.path),
                values=(entry.type_label, entry.size_label, entry.modified_label),
                text=entry.name,
            )
        self.status_var.set(f"{len(entries)} items")

    def _iter_directory(self, directory: Path) -> Iterable[FileItem]:
        try:
            with os.scandir(directory) as it:
                for entry in it:
                    try:
                        stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    yield FileItem(
                        name=entry.name,
                        path=Path(entry.path),
                        is_dir=entry.is_dir(follow_symlinks=False),
                        size=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                    )
        except PermissionError:
            messagebox.showwarning("Permission denied", f"You do not have access to {directory}")
        except FileNotFoundError:
            messagebox.showwarning("Not found", f"{directory} is not available")

    def _ensure_tree_selection(self, target: Path) -> None:
        """Expand the tree to the target path and select it if possible."""

        parts = list(target.parents)[::-1] + [target]
        current_parent = ""
        for part in parts:
            node = self._find_tree_child(current_parent, part)
            if node is None:
                break
            self.dir_tree.item(node, open=True)
            self._populate_tree_node(node, Path(self.dir_tree.item(node, "text")))
            current_parent = node

        if current_parent:
            self.dir_tree.selection_set(current_parent)
            self.dir_tree.see(current_parent)

    def _find_tree_child(self, parent: str, target: Path) -> Optional[str]:
        for child in self.dir_tree.get_children(parent):
            child_path = Path(self.dir_tree.item(child, "text"))
            if child_path == target or target.is_relative_to(child_path):
                return child
        return None

    def _go_back(self) -> None:
        if self._history_index > 0:
            self._history_index -= 1
            self._navigate_to(self._history[self._history_index])

    def _go_forward(self) -> None:
        if self._history_index + 1 < len(self._history):
            self._history_index += 1
            self._navigate_to(self._history[self._history_index])

    def _go_up(self) -> None:
        parent = self.current_path.parent
        if parent != self.current_path:
            self._navigate_to(parent, add_history=True)

    def _refresh(self) -> None:
        self._refresh_file_list()

    def _update_toolbar_state(self) -> None:
        self.back_button.config(state=tk.NORMAL if self._history_index > 0 else tk.DISABLED)
        self.forward_button.config(
            state=tk.NORMAL if self._history_index + 1 < len(self._history) else tk.DISABLED
        )
        self.up_button.config(state=tk.NORMAL if self.current_path.parent != self.current_path else tk.DISABLED)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_tree_expand(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        node = self.dir_tree.focus()
        node_path = Path(self.dir_tree.item(node, "text"))
        self._populate_tree_node(node, node_path)

    def _on_tree_select(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        node = self.dir_tree.focus()
        node_path = Path(self.dir_tree.item(node, "text"))
        self._navigate_to(node_path, add_history=True)

    def _on_file_activate(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        selection = self.file_list.focus()
        if not selection:
            return
        path = Path(selection)
        if path.is_dir():
            self._navigate_to(path, add_history=True)
        else:
            self._open_file(path)

    def _on_path_entry(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        path = Path(self.path_var.get())
        self._navigate_to(path, add_history=True)

    def _populate_tree_node(self, node: str, path: Path) -> None:
        # Remove placeholder
        children = self.dir_tree.get_children(node)
        if children and self.dir_tree.item(children[0], "text") == "loading":
            self.dir_tree.delete(children[0])

        try:
            for entry in sorted(path.iterdir(), key=lambda p: p.name.lower()):
                if not entry.is_dir():
                    continue
                child = self.dir_tree.insert(node, tk.END, text=str(entry), values=(str(entry),))
                if self._has_subdirectories(entry):
                    self.dir_tree.insert(child, tk.END, text="loading", values=("loading",))
        except PermissionError:
            pass
        except FileNotFoundError:
            pass

    def _has_subdirectories(self, path: Path) -> bool:
        try:
            for child in path.iterdir():
                if child.is_dir():
                    return True
        except OSError:
            return False
        return False

    def _open_file(self, path: Path) -> None:
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(path)  # type: ignore[attr-defined]
            elif system == "Darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror("Open file", f"Failed to open {path}: {exc}")

    def _populate_tree_for_path(self, path: Path) -> None:
        for node in self.dir_tree.get_children(""):
            node_path = Path(self.dir_tree.item(node, "text"))
            if path == node_path or path.is_relative_to(node_path):
                self.dir_tree.item(node, open=True)
                self._populate_tree_node(node, node_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_path(self, path: Optional[Path] = None) -> None:
        """Navigate to the provided path when the application starts."""

        if path is None:
            path = Path.home()
        self._navigate_to(path, add_history=True)
        self._populate_tree_for_path(path)


def main() -> None:
    app = FileViewerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
