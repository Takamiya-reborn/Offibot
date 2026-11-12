# PyInstaller 打包入口(见 package.spec / build.ps1)

from offibot.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
