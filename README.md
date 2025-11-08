# File Viewer Application

This project contains a lightweight desktop file explorer implemented with
[Tkinter](https://docs.python.org/3/library/tkinter.html). The UI mimics key
behaviour from the Windows File Explorer and can be packaged as a standalone
`.exe` for Windows users.

## Features

- Drive and folder tree navigation with lazy loading
- File detail pane showing type, size, and last modified date
- Toolbar with back, forward, up, path entry, and refresh actions
- Double-click files to open them with their associated application
- Graceful handling of missing permissions and unavailable paths

## Getting started

```bash
python -m venv .venv
source .venv/Scripts/activate  # On Linux/macOS use: source .venv/bin/activate
python -m pip install --upgrade pip
pip install pyinstaller
```

Run the application directly during development:

```bash
python src/file_viewer.py
```

## Building a Windows `.exe`

1. Ensure you are on Windows with Python 3.9 or later installed.
2. Install the dependencies above inside a virtual environment.
3. Use [PyInstaller](https://pyinstaller.org/) to bundle the project:

   ```bash
   pyinstaller --noconfirm --onefile --windowed src/file_viewer.py
   ```

4. The generated executable will be available at `dist/file_viewer.exe`.
5. Optionally rename the executable and distribute it together with the
   generated `icon.ico` (if you add one) and `LICENSE` files.

## Customisation tips

- Update window geometry, fonts, or colours in `FileViewerApp._create_widgets`.
- Adjust the metadata columns or add a preview pane in `_refresh_file_list`.
- Extend `_open_file` with custom handlers for specific file types.
