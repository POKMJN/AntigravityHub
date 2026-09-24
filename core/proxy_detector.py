"""
proxy_detector.py — 自动探测用户代理软件，提取当前活跃节点配置
支持：FlClash, Clash Verge Rev, Mihomo Party, Clash for Windows, V2RayN,
      Shadowsocks-Windows, sing-box
"""
from __future__ import annotations
import os
import json
import sqlite3
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml
import psutil


@dataclass
class ProxyNode:
    name: str
    protocol: str   # ss / vmess / vless / trojan / http / socks5
    server: str
    port: int
    extra: dict = field(default_factory=dict)   # cipher, uuid, etc.

    def to_socks5_url(self) -> str:
        """返回可供 Mihomo 使用的代理信息摘要"""
        return f"{self.protocol}://{self.server}:{self.port}"


@dataclass
class ProxyClientInfo:
    name: str               # "FlClash"
    process_name: str       # "FlClash.exe"
    http_port: int
    socks5_port: int
    active_node: Optional[ProxyNode] = None
    config_dir: str = ""


# ────────────────────────────────────────────────────────────────
# 已知代理客户端清单
# ────────────────────────────────────────────────────────────────
APPDATA = os.environ.get("APPDATA", "")
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")

KNOWN_CLIENTS = [
    {
        "name": "FlClash",
        "process": "FlClash.exe",
        "config_dir": os.path.join(APPDATA, "com.follow", "clash"),
        "http_port": 7890,
        "socks5_port": 7891,
        "parser": "flclash",
    },
    {
        "name": "Clash Verge Rev",
        "process": "clash-verge.exe",
        "config_dir": os.path.join(APPDATA, "io.github.clash-verge-rev", "clash-verge-rev"),
        "http_port": 7897,
        "socks5_port": 7898,
        "parser": "clash_generic",
    },
    {
        "name": "Mihomo Party",
        "process": "mihomo-party.exe",
        "config_dir": os.path.join(APPDATA, "mihomo-party"),
        "http_port": 7890,
        "socks5_port": 7891,
        "parser": "clash_generic",
    },
    {
        "name": "Clash for Windows",
        "process": "Clash for Windows.exe",
        "config_dir": os.path.join(APPDATA, "Clash for Windows"),
        "http_port": 7890,
        "socks5_port": 7891,
        "parser": "clash_generic",
    },
    {
        "name": "V2RayN",
        "process": "v2rayN.exe",
        "config_dir": os.path.join(APPDATA, "v2rayN"),
        "http_port": 10809,
        "socks5_port": 10808,
        "parser": "v2rayn",
    },
    {
        "name": "Shadowsocks",
        "process": "Shadowsocks.exe",
        "config_dir": os.path.join(APPDATA, "Shadowsocks"),
        "http_port": 8118,
        "socks5_port": 1080,
        "parser": "shadowsocks",
    },
    {
        "name": "sing-box",
        "process": "sing-box.exe",
        "config_dir": os.path.join(APPDATA, "sing-box"),
        "http_port": 2080,
        "socks5_port": 2080,
        "parser": "singbox",
    },
]


# ────────────────────────────────────────────────────────────────
# 进程扫描
# ────────────────────────────────────────────────────────────────

def get_running_processes() -> set[str]:
    """返回当前正在运行的进程名集合（小写）"""
    names: set[str] = set()
    for p in psutil.process_iter(["name"]):
        try:
            names.add(p.info["name"].lower())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return names


# ────────────────────────────────────────────────────────────────
# 各客户端节点解析器
# ────────────────────────────────────────────────────────────────

def _parse_flclash(config_dir: str) -> Optional[ProxyNode]:
    """解析 FlClash SQLite 数据库获取当前选中节点"""
    db_path = os.path.join(config_dir, "database.sqlite")
    prefs_path = os.path.join(config_dir, "shared_preferences.json")
    if not os.path.exists(db_path):
        return None
    try:
        # 1. 获取当前活跃 profile ID
        current_profile_id = None
        if os.path.exists(prefs_path):
            with open(prefs_path, "r", encoding="utf-8") as f:
                prefs = json.load(f)
            flutter_config_raw = prefs.get("flutter.config", "{}")
            if isinstance(flutter_config_raw, str):
                flutter_config = json.loads(flutter_config_raw)
            else:
                flutter_config = flutter_config_raw
            current_profile_id = flutter_config.get("currentProfileId")

        # 2. 从数据库读取 selected_map 和 yaml 路径
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        if current_profile_id:
            cur.execute(
                "SELECT id, selected_map FROM profiles WHERE id=?",
                (str(current_profile_id),),
            )
        else:
            cur.execute("SELECT id, selected_map FROM profiles LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if not row:
            return None

        profile_id, selected_map_raw = row
        selected_map = json.loads(selected_map_raw or "{}")

        # 3. 读取 YAML 订阅，找到 selected 节点的详情
        yaml_path = os.path.join(config_dir, "profiles", f"{profile_id}.yaml")
        if not os.path.exists(yaml_path):
            return None
        with open(yaml_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        proxies = cfg.get("proxies", [])
        proxy_map = {p["name"]: p for p in proxies}

        # 找第一个 proxy-group 的选中节点
        for group_name, node_name in selected_map.items():
            if node_name in proxy_map:
                p = proxy_map[node_name]
                return ProxyNode(
                    name=p.get("name", node_name),
                    protocol=p.get("type", "ss"),
                    server=p.get("server", ""),
                    port=int(p.get("port", 0)),
                    extra={k: v for k, v in p.items() if k not in ("name", "type", "server", "port")},
                )
    except Exception as e:
        print(f"[proxy_detector] FlClash parse error: {e}")
    return None


def _parse_clash_generic(config_dir: str) -> Optional[ProxyNode]:
    """解析 Clash 系通用 config.yaml"""
    config_path = os.path.join(config_dir, "config.yaml")
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        proxies = cfg.get("proxies", [])
        if proxies:
            p = proxies[0]
            return ProxyNode(
                name=p.get("name", "Unknown"),
                protocol=p.get("type", "unknown"),
                server=p.get("server", ""),
                port=int(p.get("port", 0)),
                extra={k: v for k, v in p.items() if k not in ("name", "type", "server", "port")},
            )
    except Exception as e:
        print(f"[proxy_detector] Clash generic parse error: {e}")
    return None


def _parse_v2rayn(config_dir: str) -> Optional[ProxyNode]:
    """解析 V2RayN guiNConfig.json"""
    config_path = os.path.join(config_dir, "guiNConfig.json")
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        idx = cfg.get("indexId", "")
        profiles = cfg.get("vmess", cfg.get("profiles", []))
        for p in profiles:
            if p.get("configType") in (1, None):
                return ProxyNode(
                    name=p.get("remarks", "V2RayN节点"),
                    protocol=p.get("configType_str", "vmess"),
                    server=p.get("address", ""),
                    port=int(p.get("port", 0)),
                    extra={"id": p.get("id", "")},
                )
    except Exception as e:
        print(f"[proxy_detector] V2RayN parse error: {e}")
    return None


def _parse_shadowsocks(config_dir: str) -> Optional[ProxyNode]:
    """解析 Shadowsocks-Windows gui-config.json"""
    config_path = os.path.join(config_dir, "gui-config.json")
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        servers = cfg.get("configs", [])
        idx = cfg.get("index", 0)
        if servers:
            s = servers[min(idx, len(servers) - 1)]
            return ProxyNode(
                name=s.get("remarks", "SS节点"),
                protocol="ss",
                server=s.get("server", ""),
                port=int(s.get("server_port", 0)),
                extra={"method": s.get("method", ""), "password": s.get("password", "")},
            )
    except Exception as e:
        print(f"[proxy_detector] Shadowsocks parse error: {e}")
    return None


def _parse_singbox(config_dir: str) -> Optional[ProxyNode]:
    """解析 sing-box config.json"""
    config_path = os.path.join(config_dir, "config.json")
    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        outbounds = cfg.get("outbounds", [])
        for o in outbounds:
            if o.get("type") not in ("direct", "block", "dns", "selector", "urltest"):
                return ProxyNode(
                    name=o.get("tag", "sing-box节点"),
                    protocol=o.get("type", "unknown"),
                    server=o.get("server", ""),
                    port=int(o.get("server_port", 0)),
                    extra={},
                )
    except Exception as e:
        print(f"[proxy_detector] sing-box parse error: {e}")
    return None


PARSERS = {
    "flclash": _parse_flclash,
    "clash_generic": _parse_clash_generic,
    "v2rayn": _parse_v2rayn,
    "shadowsocks": _parse_shadowsocks,
    "singbox": _parse_singbox,
}


# ────────────────────────────────────────────────────────────────
# 主探测函数
# ────────────────────────────────────────────────────────────────

def detect_proxy_clients() -> list[ProxyClientInfo]:
    """
    扫描正在运行的代理客户端，返回所有发现的客户端信息列表（含活跃节点）。
    """
    running = get_running_processes()
    found: list[ProxyClientInfo] = []

    for client_def in KNOWN_CLIENTS:
        proc_name = client_def["process"].lower()
        if proc_name not in running:
            continue

        parser_fn = PARSERS.get(client_def["parser"])
        active_node = None
        if parser_fn:
            active_node = parser_fn(client_def["config_dir"])

        info = ProxyClientInfo(
            name=client_def["name"],
            process_name=client_def["process"],
            http_port=client_def["http_port"],
            socks5_port=client_def["socks5_port"],
            active_node=active_node,
            config_dir=client_def["config_dir"],
        )
        found.append(info)

    return found


def get_primary_proxy_port() -> tuple[str, int]:
    """
    返回当前最优代理的 (host, socks5_port)。
    优先返回第一个探测到的客户端的 SOCKS5 端口。
    """
    clients = detect_proxy_clients()
    if clients:
        c = clients[0]
        return ("127.0.0.1", c.socks5_port)
    return ("127.0.0.1", 7890)  # fallback


if __name__ == "__main__":
    clients = detect_proxy_clients()
    if not clients:
        print("未发现运行中的代理客户端")
    for c in clients:
        print(f"✓ {c.name} (port={c.socks5_port})")
        if c.active_node:
            print(f"  节点: {c.active_node.name} [{c.active_node.protocol}] {c.active_node.server}:{c.active_node.port}")
