"""
injector.py — 内置补丁管理与注入引擎
支持离线注入 antigravity-proxy (version.dll + config.json) 和 antigravity2-cn (app.asar)
支持状态探测、进程安全管控、备份与一键还原
"""
from __future__ import annotations
import os
import sys
import json
import shutil
from pathlib import Path
from typing import NamedTuple, Tuple, List, Optional
import psutil

# ── 路径定位 ──────────────────────────────────────────────────────

AG_DIR = Path(r"C:\Users\22816\AppData\Local\Programs\antigravity")
AG_EXE = AG_DIR / "Antigravity.exe"
AG_DLL = AG_DIR / "version.dll"
AG_CONFIG = AG_DIR / "config.json"
AG_RESOURCES = AG_DIR / "resources"
AG_ASAR = AG_RESOURCES / "app.asar"
AG_ASAR_BAK = AG_RESOURCES / "app.asar.bak"
BACKUP_DIR = Path(r"C:\Users\22816\antigravity_proxy\backup")


def get_builtin_asset(relative_path: str) -> Path:
    """获取内置资产路径，兼容 PyInstaller 单文件打包 (sys._MEIPASS)"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS)
    else:
        # 开发模式：位于项目根目录下的 builtin_assets
        base_dir = Path(__file__).resolve().parent.parent

    target = base_dir / "builtin_assets" / relative_path
    if not target.exists():
        # 回退检查
        alt_target = Path(__file__).resolve().parent.parent / "builtin_assets" / relative_path
        if alt_target.exists():
            return alt_target
    return target


class InjectionStatus(NamedTuple):
    is_installed: bool          # 反重力是否已安装
    is_running: bool            # 反重力当前是否在运行
    proxy_injected: bool        # version.dll 是否到位
    port_configured: bool       # config.json 端口是否为 7890
    cn_injected: bool           # 汉化包是否已注入
    version_str: str            # IDE 版本号
    needs_injection: bool       # 是否需要补丁注入/修复
    status_summary: str         # 简述文本


class PatchInjector:
    """反重力补丁注入与管理核心"""

    @staticmethod
    def get_ag_version() -> str:
        """获取 Antigravity.exe 的 FileVersion"""
        if not AG_EXE.exists():
            return "未安装"
        try:
            import subprocess
            res = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-Item '{AG_EXE}').VersionInfo.FileVersion"],
                text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            v = res.strip()
            return v if v else "2.15.1"
        except Exception:
            return "2.15.1"

    @staticmethod
    def is_ag_running() -> bool:
        """检查 Antigravity 是否正在运行"""
        for p in psutil.process_iter(["name"]):
            try:
                name = p.info.get("name", "")
                if name and "antigravity.exe" in name.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    @staticmethod
    def close_ag_process() -> bool:
        """安全关闭正在运行的反重力进程"""
        closed_any = False
        for p in psutil.process_iter(["name", "pid"]):
            try:
                name = p.info.get("name", "")
                if name and "antigravity" in name.lower() and not "hub" in name.lower() and not "manager" in name.lower():
                    p.terminate()
                    closed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return closed_any

    @classmethod
    def check_status(cls) -> InjectionStatus:
        """全面检测反重力状态"""
        is_installed = AG_EXE.exists()
        is_running = cls.is_ag_running()
        version_str = cls.get_ag_version() if is_installed else "未检测到"

        # 1. 检查 version.dll (存在且大于 100KB)
        proxy_injected = AG_DLL.exists() and AG_DLL.stat().st_size > 100_000

        # 2. 检查 config.json 代理端口是否严格对齐 7890
        port_configured = False
        if AG_CONFIG.exists():
            try:
                data = json.loads(AG_CONFIG.read_text(encoding="utf-8"))
                p = data.get("proxy", {}).get("port")
                port_configured = (p == 7890)
            except Exception:
                port_configured = False

        # 3. 检查汉化包 (原版 app.asar 约 4.5MB，汉化版约 21MB；或存在 app.asar.bak)
        cn_injected = False
        if AG_ASAR.exists():
            size = AG_ASAR.stat().st_size
            # 汉化包大于 15MB 或有 bak 备份则视为已汉化
            if size > 15_000_000 or AG_ASAR_BAK.exists():
                cn_injected = True

        needs_injection = is_installed and (not proxy_injected or not port_configured or not cn_injected)

        # 汇总文本
        if not is_installed:
            summary = "未检测到 Antigravity 安装目录"
        elif needs_injection:
            missing = []
            if not proxy_injected: missing.append("免代理补丁未注入")
            if not port_configured: missing.append("端口未对齐7890")
            if not cn_injected: missing.append("汉化包未注入")
            summary = "，".join(missing) + "（建议立即注入）"
        else:
            summary = "全部补丁就绪（免代理补丁已就绪，端口对齐7890，已汉化）"

        return InjectionStatus(
            is_installed=is_installed,
            is_running=is_running,
            proxy_injected=proxy_injected,
            port_configured=port_configured,
            cn_injected=cn_injected,
            version_str=version_str,
            needs_injection=needs_injection,
            status_summary=summary,
        )

    @classmethod
    def inject_proxy(cls, log_cb: Optional[callable] = None) -> bool:
        """注入代理补丁 (version.dll + 端口配置)"""
        def log(msg: str):
            if log_cb: log_cb(msg)

        if not AG_DIR.exists():
            log("✗ 错误：未找到 Antigravity 目录！")
            return False

        if cls.is_ag_running():
            log("⚠ 检测到 Antigravity 正在运行，正在尝试关闭进程…")
            cls.close_ag_process()
            import time; time.sleep(1)

        src_dll = get_builtin_asset("proxy/version.dll")
        if not src_dll.exists():
            log(f"✗ 错误：内置代理补丁文件缺失：{src_dll}")
            return False

        # 备份并替换 version.dll
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            if AG_DLL.exists():
                shutil.copy2(AG_DLL, BACKUP_DIR / "version.dll.bak")
            shutil.copy2(src_dll, AG_DLL)
            log("✓ 已注入内置核心代理劫持补丁 (version.dll)")
        except Exception as e:
            log(f"✗ 注入 version.dll 失败：{e}")
            return False

        # 修复或写入 config.json
        try:
            config_data = {}
            if AG_CONFIG.exists():
                try:
                    config_data = json.loads(AG_CONFIG.read_text(encoding="utf-8"))
                except Exception:
                    pass

            if not config_data:
                src_cfg = get_builtin_asset("proxy/config.json")
                if src_cfg.exists():
                    config_data = json.loads(src_cfg.read_text(encoding="utf-8"))

            if "proxy" not in config_data:
                config_data["proxy"] = {}

            target_port = 7890
            config_data["proxy"]["port"] = target_port
            config_data["proxy"]["host"] = "127.0.0.1"
            config_data["proxy"]["type"] = "socks5"
            config_data["proxy"]["enabled"] = True

            AG_CONFIG.write_text(json.dumps(config_data, indent=2, ensure_ascii=False), encoding="utf-8")
            log(f"✓ 已同步代理端口配置 (严格对齐 127.0.0.1:{target_port})")
            return True
        except Exception as e:
            log(f"✗ 写入 config.json 失败：{e}")
            return False

    @classmethod
    def inject_cn(cls, log_cb: Optional[callable] = None) -> bool:
        """注入汉化包 (app.asar)"""
        def log(msg: str):
            if log_cb: log_cb(msg)

        if not AG_RESOURCES.exists():
            log("✗ 错误：未找到 Antigravity resources 目录！")
            return False

        if cls.is_ag_running():
            log("⚠ 检测到 Antigravity 正在运行，正在尝试关闭进程…")
            cls.close_ag_process()
            import time; time.sleep(1)

        src_asar = get_builtin_asset("cn/app.asar")
        if not src_asar.exists():
            log(f"✗ 错误：内置汉化补丁文件缺失：{src_asar}")
            return False

        try:
            # 备份原版（若无备份）
            if AG_ASAR.exists() and not AG_ASAR_BAK.exists():
                shutil.copy2(AG_ASAR, AG_ASAR_BAK)
                log("✓ 已备份官方原版 app.asar 至 app.asar.bak")

            shutil.copy2(src_asar, AG_ASAR)
            log("✓ 已注入内置完整中文汉化包 (app.asar)")
            return True
        except Exception as e:
            log(f"✗ 注入汉化包失败：{e}")
            return False

    @classmethod
    def inject_all(cls, log_cb: Optional[callable] = None) -> bool:
        """一键全自动注入全部内置补丁 (Proxy + CN + 端口配置)"""
        def log(msg: str):
            if log_cb: log_cb(msg)

        log("========== 开始执行一键全自动注入 ==========")
        ok1 = cls.inject_proxy(log_cb)
        ok2 = cls.inject_cn(log_cb)
        if ok1 and ok2:
            log("🎉 一键注入圆满完成！反重力代理与汉化补丁已全部生效。")
            return True
        else:
            log("⚠ 一键注入过程中存在错误，请查阅上方日志。")
            return False

    @classmethod
    def restore_original(cls, log_cb: Optional[callable] = None) -> bool:
        """还原官方原版状态"""
        def log(msg: str):
            if log_cb: log_cb(msg)

        log("========== 正在还原官方原版状态 ==========")
        if cls.is_ag_running():
            log("⚠ 正在关闭反重力运行进程…")
            cls.close_ag_process()
            import time; time.sleep(1)

        # 1. 还原 app.asar
        if AG_ASAR_BAK.exists():
            try:
                shutil.copy2(AG_ASAR_BAK, AG_ASAR)
                log("✓ 已从备份恢复官方原版英文 app.asar")
            except Exception as e:
                log(f"✗ 恢复 app.asar 失败：{e}")

        # 2. 移除 version.dll 劫持
        if AG_DLL.exists():
            try:
                AG_DLL.unlink()
                log("✓ 已移除代理劫持补丁 (version.dll)")
            except Exception as e:
                log(f"✗ 移除 version.dll 失败：{e}")

        log("✓ 原版环境还原完毕。")
        return True

    # 兼容别名
    restore = restore_original
