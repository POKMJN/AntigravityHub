"""
main.py — AntigravityHub 入口
"""
import sys
import os

# 确保项目根目录在 path 中（PyInstaller 打包后路径会变）
if getattr(sys, "frozen", False):
    # 打包后的 exe 运行路径
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

# 设置 DPI 感知（Windows 高分屏）
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from ui.win_app_window import WinAppWindow


def main():
    app = WinAppWindow()
    app.run()


if __name__ == "__main__":
    main()
