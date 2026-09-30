"""PyInstaller 打包入口:pyinstaller --onefile --collect-data offibot -n offibot offibot_entry.py"""

from offibot.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
