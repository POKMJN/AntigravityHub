"""
mihomo_service.py — 管理 Mihomo 进程生命周期和配置
"""
from __future__ import annotations
import os
import sys
import json
import time
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable
import psutil
import requests
import yaml


# Mihomo 安装目录（与之前 antigravity_proxy 项目相同）
MIHOMO_DIR = Path(r"C:\Users\22816\antigravity_proxy")
MIHOMO_EXE = MIHOMO_DIR / "mihomo.exe"
MIHOMO_CONFIG = MIHOMO_DIR / "config.yaml"
API_BASE = "http://127.0.0.1:9095"
API_SECRET = ""   # 如果 config.yaml 中设了 secret 则填写
PROXY_PORT = 7895  # Antigravity 专用代理端口


class MihomoService:
    """控制 Mihomo 单例进程"""

    def __init__(self, on_status_change: Optional[Callable] = None):
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.on_status_change = on_status_change  # (is_running, node_name, latency_ms)

    # ── 启动 ──────────────────────────────────────────────────────

    def start(self) -> bool:
        """启动 Mihomo，若已运行则跳过"""
        with self._lock:
            if self._is_running():
                return True
            if not MIHOMO_EXE.exists():
                print(f"[mihomo] 找不到 {MIHOMO_EXE}")
                return False
            try:
                self._proc = subprocess.Popen(
                    [str(MIHOMO_EXE), "-f", str(MIHOMO_CONFIG)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                # 等待 API 就绪
                for _ in range(20):
                    time.sleep(0.5)
                    if self._api_ready():
                        print(f"[mihomo] 已启动 PID={self._proc.pid}")
                        return True
                print("[mihomo] 启动超时")
                return False
            except Exception as e:
                print(f"[mihomo] 启动失败: {e}")
                return False

    # ── 停止 ──────────────────────────────────────────────────────

    def stop(self):
        """停止 Mihomo 进程"""
        with self._lock:
            # 先尝试终止自己启动的进程
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                self._proc = None
            # 再通过 psutil 找并结束所有 mihomo.exe
            for p in psutil.process_iter(["name", "pid"]):
                try:
                    if p.info["name"].lower() == "mihomo.exe":
                        p.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

    def restart(self) -> bool:
        self.stop()
        time.sleep(0.5)
        return self.start()

    # ── 状态 ──────────────────────────────────────────────────────

    def _is_running(self) -> bool:
        """检查 mihomo.exe 进程是否存在"""
        for p in psutil.process_iter(["name"]):
            try:
                if p.info["name"].lower() == "mihomo.exe":
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    def _api_ready(self) -> bool:
        try:
            r = requests.get(f"{API_BASE}/version", timeout=1)
            return r.status_code == 200
        except Exception:
            return False

    def is_running(self) -> bool:
        return self._is_running()

    def get_version(self) -> str:
        try:
            r = requests.get(f"{API_BASE}/version", timeout=2)
            return r.json().get("version", "unknown")
        except Exception:
            return "offline"

    def get_current_node(self) -> dict:
        """返回 Antigravity-Failover 组当前节点信息"""
        try:
            r = requests.get(
                f"{API_BASE}/proxies/Antigravity-Failover",
                timeout=2,
            )
            data = r.json()
            return {
                "name": data.get("now", "unknown"),
                "alive": data.get("alive", False),
            }
        except Exception:
            return {"name": "offline", "alive": False}

    def get_latency(self, proxy_name: str) -> Optional[int]:
        """查询指定节点延迟（ms），失败返回 None"""
        try:
            r = requests.get(
                f"{API_BASE}/proxies/{requests.utils.quote(proxy_name)}",
                timeout=2,
            )
            history = r.json().get("history", [])
            if history:
                return history[-1].get("delay")
        except Exception:
            pass
        return None

    def test_latency(self, proxy_name: str) -> Optional[int]:
        """主动测速并返回延迟（ms）"""
        try:
            r = requests.get(
                f"{API_BASE}/proxies/{requests.utils.quote(proxy_name)}/delay",
                params={"url": "https://www.google.com", "timeout": 5000},
                timeout=8,
            )
            return r.json().get("delay")
        except Exception:
            return None

    def get_all_proxies(self) -> dict:
        try:
            r = requests.get(f"{API_BASE}/proxies", timeout=3)
            return r.json().get("proxies", {})
        except Exception:
            return {}

    def switch_node(self, group: str, node: str) -> bool:
        """切换 proxy-group 的当前节点"""
        try:
            r = requests.put(
                f"{API_BASE}/proxies/{requests.utils.quote(group)}",
                json={"name": node},
                timeout=3,
            )
            return r.status_code == 204
        except Exception:
            return False

    # ── 配置生成 ──────────────────────────────────────────────────

    @staticmethod
    def generate_config(
        primary_node: dict,    # {"name":..., "type":"ss"/"vless", ...}
        fallback_node: dict,
        listen_port: int = PROXY_PORT,
        api_port: int = 9095,
    ) -> str:
        """生成 Mihomo config.yaml 内容"""
        config = {
            "mixed-port": listen_port,
            "allow-lan": False,
            "mode": "rule",
            "log-level": "info",
            "external-controller": f"127.0.0.1:{api_port}",
            "proxies": [primary_node, fallback_node],
            "proxy-groups": [
                {
                    "name": "Antigravity-Failover",
                    "type": "fallback",
                    "proxies": [primary_node["name"], fallback_node["name"]],
                    "url": "https://www.google.com/generate_204",
                    "interval": 60,
                    "tolerance": 50,
                }
            ],
            "rules": ["MATCH,Antigravity-Failover"],
        }
        return yaml.dump(config, allow_unicode=True, default_flow_style=False)

    @staticmethod
    def write_config(content: str):
        MIHOMO_CONFIG.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    svc = MihomoService()
    if svc.is_running():
        print(f"Mihomo 运行中，version={svc.get_version()}")
        print(f"当前节点: {svc.get_current_node()}")
    else:
        print("Mihomo 未运行，正在启动...")
        svc.start()
