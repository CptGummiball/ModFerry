# Installation

## Requirements

- **Python 3.10 or newer**: [python.org/downloads](https://www.python.org/downloads/). On Windows, keep the `py` launcher option enabled during setup.
- An internet connection on the first start (to install the dependencies).
- A modern browser.

## Windows

1. Download the ZIP of the [latest release](https://github.com/CptGummiball/ModFerry/releases/latest) and unzip it to a folder of your choice.
2. Double-click **`start-windows.bat`**.
3. The first start creates `.venv` and installs the dependencies, then your browser opens **http://127.0.0.1:8765**.

Keep the console window open while you use ModFerry. Closing it stops the app.

## Linux / macOS

```bash
cd ModFerry
chmod +x start-linux.sh
./start-linux.sh
```

The script tries to open the browser (`xdg-open` / `open`); otherwise open http://127.0.0.1:8765 yourself.

## Manual start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Updating

Replace the program files with the new release but **keep the `data/` folder**: it holds your profiles, history and encrypted tokens. Then start as usual; new dependencies are installed automatically.

## Uninstalling

Delete the folder. To keep your profiles, back up `data/profiles.json` first.
