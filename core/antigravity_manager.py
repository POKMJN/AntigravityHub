"""
antigravity_manager.py — 检测 Antigravity IDE 状态，执行自愈
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import psutil


AG_DIR = Path(r"C:\Users\22816\AppData\Local\Programs\antigravity")
AG_EXE = AG_DIR / "Antigravity.exe"
AG_CONFIG = AG_DIR / "config.json"
AG_DLL = AG_DIR / "version.dll"

BACKUP_DIR = Path(r"C:\Users\22816\antigravity_proxy\backup")
BACKUP_DLL = BACKUP_DIR / "version.dll"
BACKUP_CONFIG = BACKUP_DIR / "config.json"

REQUIRED_PROXY_PORT = 7895


@dataclass
class AGStatus:
    version: str
    is_running: bool
    dll_present: bool
    config_port: int          # 当前 config.json 中的 proxy.port
    port_correct: bool        # config_port == REQUIRED_PROXY_PORT
    backup_dll_exists: bool
    needs_heal: bool

    def summary(self) -> str:
        lines = [f"Antigravity IDE v{self.version}"]
        lines.append("✓ 进程运行中" if self.is_running else "· 进程未运行")
        lines.append("✓ version.dll 存在" if self.dll_present else "✗ version.dll 缺失")
        lines.append(
            f"✓ 代理端口 {self.config_port}" if self.port_correct
            else f"✗ 代理端口异常: {self.config_port} (需要 {REQUIRED_PROXY_PORT})"
        )
        return "\n".join(lines)


class AntigravityManager:

    def get_version(self) -> str:
        """从 Antigravity.exe 读取文件版本"""
        if not AG_EXE.exists():
            return "未安装"
        try:
            import win32api
            info = win32api.GetFileVersionInfo(str(AG_EXE), "\\")
            ms = info["FileVersionMS"]
            ls = info["FileVersionLS"]
            return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
        except Exception:
            pass
        # fallback: powershell
        try:
            result = subprocess.check_output(
                ["powershell", "-Command",
                 f"(Get-Item '{AG_EXE}').VersionInfo.FileVersion"],
                text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.strip()
        except Exception:
            return "unknown"

    def is_running(self) -> bool:
        for p in psutil.process_iter(["name"]):
            try:
                n = p.info["name"].lower()
                if "antigravity" in n and n.endswith(".exe"):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    def get_config_port(self) -> int:
        if not AG_CONFIG.exists():
            return -1
        try:
            with open(AG_CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return cfg.get("proxy", {}).get("port", -1)
        except Exception:
            return -1

    def get_status(self) -> AGStatus:
        version = self.get_version()
        is_running = self.is_running()
        dll_present = AG_DLL.exists()
        config_port = self.get_config_port()
        port_correct = config_port == REQUIRED_PROXY_PORT
        backup_dll_exists = BACKUP_DLL.exists()
        needs_heal = not dll_present or not port_correct
        return AGStatus(
            version=version,
            is_running=is_running,
            dll_present=dll_present,
            config_port=config_port,
            port_correct=port_correct,
            backup_dll_exists=backup_dll_exists,
            needs_heal=needs_heal,
        )

    def heal(self) -> list[str]:
        """自愈：修复 version.dll 缺失 + config.json 端口漂移"""
        actions: list[str] = []
        status = self.get_status()

        # 1. 修复 version.dll
        if not status.dll_present:
            if status.backup_dll_exists:
                shutil.copy2(str(BACKUP_DLL), str(AG_DLL))
                actions.append("✓ 已从备份恢复 version.dll")
            else:
                actions.append("✗ 备份不存在，无法恢复 version.dll")

        # 2. 修复 config.json 端口
        if not status.port_correct:
            try:
                with open(AG_CONFIG, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if "proxy" not in cfg:
                    cfg["proxy"] = {}
                cfg["proxy"]["port"] = REQUIRED_PROXY_PORT
                with open(AG_CONFIG, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2, ensure_ascii=False)
                actions.append(f"✓ 已将代理端口修复为 {REQUIRED_PROXY_PORT}")
            except Exception as e:
                actions.append(f"✗ 修复 config.json 失败: {e}")

        if not actions:
            actions.append("✓ 状态正常，无需修复")
        return actions

    def backup_current(self):
        """备份当前 version.dll 和 config.json"""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if AG_DLL.exists():
            shutil.copy2(str(AG_DLL), str(BACKUP_DLL))
        if AG_CONFIG.exists():
            shutil.copy2(str(AG_CONFIG), str(BACKUP_CONFIG))

    def launch(self):
        """启动 Antigravity IDE"""
        if AG_EXE.exists():
            subprocess.Popen(
                [str(AG_EXE)],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

    def open_install_dir(self):
        """打开安装目录"""
        os.startfile(str(AG_DIR))


if __name__ == "__main__":
    mgr = AntigravityManager()
    status = mgr.get_status()
    print(status.summary())
    if status.needs_heal:
        print("\n执行自愈...")
        for action in mgr.heal():
            print(action)
