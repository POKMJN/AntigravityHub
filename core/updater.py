"""
updater.py — 检查并下载 antigravity-proxy 和 antigravity2-cn 的更新
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional, Callable
import requests


# ── 路径常量 ──────────────────────────────────────────────────────
AG_DIR = Path(r"C:\Users\22816\AppData\Local\Programs\antigravity")
PROXY_DIR = Path(r"C:\Users\22816\antigravity_proxy")
BACKUP_DIR = PROXY_DIR / "backup"
SETTINGS_FILE = Path(r"C:\Users\22816\antigravity_manager\config\settings.json")

# ── GitHub API ────────────────────────────────────────────────────
PROXY_RELEASES_URL = "https://api.github.com/repos/yuaotian/antigravity-proxy/releases/latest"
CN_COMMITS_URL = "https://api.github.com/repos/qqxpee/antigravity2-cn/commits/main"
CN_ZIP_URL = "https://api.github.com/repos/qqxpee/antigravity2-cn/zipball/main"

# 国内镜像前缀（按优先级排列）
MIRRORS = [
    "https://gh.api.99988866.xyz/",
    "https://wget.la/",
    "https://mirror.ghproxy.com/",
    "https://fastgit.cc/",
    "https://github.boki.moe/",
    "https://gitproxy.mrhjx.cn/",
]

REQUEST_TIMEOUT = 10


# ── 设置持久化 ────────────────────────────────────────────────────

def _load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(data: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/vnd.github.v3+json",
}

# ── HTTP 工具 ─────────────────────────────────────────────────────

def _fetch_json(url: str, timeout: int = 6) -> dict:
    """
    高可用 JSON 请求：依次尝试 直连 -> 本地代理 -> API 镜像
    """
    # 候选代理
    proxy_candidates = [
        None,
        {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"},
        {"http": "socks5://127.0.0.1:7890", "https": "socks5://127.0.0.1:7890"},
    ]

    # 1. 尝试直连与本地代理
    for p in proxy_candidates:
        try:
            r = requests.get(url, headers=DEFAULT_HEADERS, proxies=p, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue

    # 2. 尝试 API 镜像
    mirror_prefixes = [
        "https://ghproxy.net/",
        "https://mirror.ghproxy.com/",
        "https://gh.api.99988866.xyz/",
    ]
    for m in mirror_prefixes:
        mirror_url = m + url
        try:
            r = requests.get(mirror_url, headers=DEFAULT_HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            continue

    raise RuntimeError("无法连接更新服务器，请确认网络连接或开启代理")


def _download_with_mirror(original_url: str, dest: Path,
                           progress_cb: Optional[Callable[[int, int], None]] = None) -> bool:
    """
    下载文件：逐个尝试直连、本地代理和国内镜像
    progress_cb(downloaded_bytes, total_bytes)
    """
    urls_to_try = [original_url] + [
        m + original_url.replace("https://github.com/", "").replace("https://", "")
        if m.endswith("/") else m + original_url
        for m in MIRRORS
    ]
    proxies_options = [
        None,
        {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"},
        {"http": "socks5://127.0.0.1:7890", "https": "socks5://127.0.0.1:7890"},
    ]

    for url in urls_to_try:
        for proxies in proxies_options:
            try:
                r = requests.get(url, headers=DEFAULT_HEADERS, proxies=proxies, stream=True, timeout=25)
                if r.status_code != 200:
                    continue
                total = int(r.headers.get("content-length", 0))
                downloaded = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=16384):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_cb and total:
                                progress_cb(downloaded, total)
                return True
            except Exception as e:
                continue
    return False


# ── antigravity-proxy 更新 ────────────────────────────────────────

class ProxyUpdater:
    """检查并更新 yuaotian/antigravity-proxy"""

    def get_local_version(self) -> str:
        """读取本地版本：优先 settings.json，其次 version.dll FileVersion，保底 2.4"""
        dll = AG_DIR / "version.dll"
        if not dll.exists():
            return "未安装"

        settings = _load_settings()
        saved = settings.get("proxy_version", "")
        if saved:
            return saved

        try:
            import subprocess
            result = subprocess.check_output(
                ["powershell", "-Command",
                 f"(Get-Item '{dll}').VersionInfo.FileVersion"],
                text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            v = result.strip()
            if v:
                return v
        except Exception:
            pass

        # 默认当前已安装为 2.4
        return "2.4"

    def get_remote_info(self) -> dict:
        """获取 GitHub 最新 release 信息"""
        data = _fetch_json(PROXY_RELEASES_URL)
        tag = data.get("tag_name", "v0.0.0")
        version = tag.lstrip("v")
        asset_url = ""
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if "ide-win-x64" in name and name.endswith(".zip"):
                asset_url = asset.get("browser_download_url", "")
                break
        return {"version": version, "tag": tag, "asset_url": asset_url, "body": data.get("body", "")}

    def needs_update(self) -> tuple[bool, str, str]:
        """返回 (需要更新, 本地版本, 远端版本)"""
        local = self.get_local_version()
        remote = self.get_remote_info()
        remote_ver = remote.get("version", "0.0.0")

        def parse(v: str) -> tuple:
            parts = v.replace("-", ".").split(".")
            return tuple(int(x) if x.isdigit() else 0 for x in parts[:4])

        if local == "未安装":
            return True, local, remote_ver

        return parse(remote_ver) > parse(local), local, remote_ver

    def update(self, progress_cb: Optional[Callable] = None,
               log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """执行更新流程"""
        def log(msg: str):
            print(f"[proxy-updater] {msg}")
            if log_cb:
                log_cb(msg)

        remote = self.get_remote_info()
        asset_url = remote.get("asset_url")
        if not asset_url:
            log("✗ 未找到下载地址")
            return False

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "proxy.zip"
            log(f"正在下载 {remote['tag']}...")
            if not _download_with_mirror(asset_url, zip_path, progress_cb):
                log("✗ 下载失败")
                return False

            log("正在解压...")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(tmpdir)

            # 查找 version.dll
            dll_candidates = list(Path(tmpdir).rglob("version.dll"))
            config_candidates = list(Path(tmpdir).rglob("config.json"))
            if not dll_candidates:
                log("✗ 压缩包中未找到 version.dll")
                return False

            src_dll = dll_candidates[0]
            log("正在备份当前文件...")
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            if (AG_DIR / "version.dll").exists():
                shutil.copy2(AG_DIR / "version.dll", BACKUP_DIR / "version.dll")

            log("正在替换 version.dll...")
            shutil.copy2(src_dll, AG_DIR / "version.dll")

            if config_candidates:
                # 仅在端口与我们的配置不冲突时才替换 config.json（实际上我们有自己的配置）
                # 所以这里只备份，不覆盖用户的 config.json
                log("✓ 跳过 config.json 替换（保留当前代理端口配置）")

            # 记录更新后的版本号到 settings.json
            settings = _load_settings()
            settings["proxy_version"] = remote.get("version", "2.4")
            _save_settings(settings)

            log(f"✓ antigravity-proxy 已更新到 {remote['tag']}")
            return True


# ── antigravity2-cn 更新 ──────────────────────────────────────────

class CNUpdater:
    """检查并更新 qqxpee/antigravity2-cn 汉化包"""

    APP_ASAR = AG_DIR / "resources" / "app.asar"
    APP_ASAR_BAK = AG_DIR / "resources" / "app.asar.bak"

    def get_local_commit(self) -> str:
        settings = _load_settings()
        return settings.get("cn_commit_sha", "")

    def get_remote_commit(self) -> str:
        data = _fetch_json(CN_COMMITS_URL)
        return data.get("sha", "")

    def needs_update(self) -> tuple[bool, str, str]:
        """返回 (需要更新, 本地SHA短, 远端SHA短)"""
        local = self.get_local_commit()
        remote = self.get_remote_commit()
        if not remote:
            return False, (local[:7] if local else "未记录"), "连接失败"

        if not local:
            # 本地未记录 commit，提示可安装/更新
            return True, "未记录", remote[:7]

        needs = local != remote
        return needs, local[:7], remote[:7]

    def is_installed(self) -> bool:
        """通过检查 app.asar 备份判断是否安装过汉化"""
        return self.APP_ASAR_BAK.exists()

    def update(self, progress_cb: Optional[Callable] = None,
               log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """
        下载最新汉化包并注入 app.asar。
        注意：需要 Antigravity IDE 未运行。
        """
        def log(msg: str):
            print(f"[cn-updater] {msg}")
            if log_cb:
                log_cb(msg)

        remote_sha = self.get_remote_commit()
        if not remote_sha:
            log("✗ 无法获取远端版本信息")
            return False

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "cn.zip"
            log("正在下载汉化包...")

            # CN_ZIP_URL 是 GitHub zipball，需要镜像
            download_url = CN_ZIP_URL
            if not _download_with_mirror(download_url, zip_path, progress_cb):
                log("✗ 下载失败")
                return False

            log("正在解压...")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(tmpdir)

            # 找解压出的根目录
            extracted_dirs = [p for p in Path(tmpdir).iterdir() if p.is_dir()]
            if not extracted_dirs:
                log("✗ 解压目录为空")
                return False

            cn_root = extracted_dirs[0]

            # 寻找注入脚本
            inject_script = None
            for name in ["inject.py", "install.py", "patch.py"]:
                candidate = cn_root / name
                if candidate.exists():
                    inject_script = candidate
                    break

            # 寻找翻译文件（字典文件）
            dict_files = list(cn_root.rglob("*.json"))
            asar_files = list(cn_root.rglob("*.asar"))

            if asar_files:
                # 如果包里直接有 app.asar，直接替换
                log("找到预打包 app.asar，直接替换...")
                if not self.APP_ASAR_BAK.exists() and self.APP_ASAR.exists():
                    shutil.copy2(self.APP_ASAR, self.APP_ASAR_BAK)
                    log("✓ 已备份原版 app.asar")
                shutil.copy2(asar_files[0], self.APP_ASAR)
                log("✓ 汉化包已替换 app.asar")
            elif inject_script:
                # 运行注入脚本
                log("正在执行汉化注入脚本...")
                try:
                    import subprocess
                    result = subprocess.run(
                        [sys.executable, str(inject_script)],
                        cwd=str(cn_root),
                        capture_output=True, text=True, timeout=60
                    )
                    if result.returncode == 0:
                        log("✓ 汉化注入成功")
                    else:
                        log(f"✗ 注入脚本报错:\n{result.stderr}")
                        return False
                except Exception as e:
                    log(f"✗ 运行注入脚本失败: {e}")
                    return False
            else:
                log("✗ 未找到注入方式（无 app.asar 也无注入脚本），请手动执行汉化")
                return False

            # 记录 commit SHA
            settings = _load_settings()
            settings["cn_commit_sha"] = remote_sha
            _save_settings(settings)
            log(f"✓ 已记录版本 SHA: {remote_sha[:7]}")
            return True

    def restore_original(self, log_cb: Optional[Callable[[str], None]] = None) -> bool:
        """恢复原版 app.asar"""
        def log(msg: str):
            print(f"[cn-updater] {msg}")
            if log_cb:
                log_cb(msg)

        if not self.APP_ASAR_BAK.exists():
            log("✗ 没有备份，无法恢复")
            return False
        shutil.copy2(self.APP_ASAR_BAK, self.APP_ASAR)
        log("✓ 已恢复原版 app.asar")
        settings = _load_settings()
        settings["cn_commit_sha"] = ""
        _save_settings(settings)
        return True


if __name__ == "__main__":
    pu = ProxyUpdater()
    needs, local, remote = pu.needs_update()
    print(f"antigravity-proxy: local={local}, remote={remote}, needs_update={needs}")

    cu = CNUpdater()
    needs_cn, local_cn, remote_cn = cu.needs_update()
    print(f"antigravity2-cn: local={local_cn}, remote={remote_cn}, needs_update={needs_cn}")
