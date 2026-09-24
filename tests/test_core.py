"""
tests/test_core.py — AntigravityHub 核心模块单元测试
"""
import sys
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── proxy_detector 测试 ────────────────────────────────────────────

class TestProxyDetector(unittest.TestCase):

    def test_get_running_processes_returns_set(self):
        from core.proxy_detector import get_running_processes
        procs = get_running_processes()
        self.assertIsInstance(procs, set)
        # 至少应该有 python.exe 或 pwsh.exe 在运行
        self.assertTrue(len(procs) > 0)

    @patch("core.proxy_detector.get_running_processes")
    def test_detect_no_client_when_none_running(self, mock_procs):
        mock_procs.return_value = {"notepad.exe", "explorer.exe"}
        from core.proxy_detector import detect_proxy_clients
        clients = detect_proxy_clients()
        self.assertEqual(len(clients), 0)

    def test_proxy_node_to_socks5_url(self):
        from core.proxy_detector import ProxyNode
        node = ProxyNode(name="Test", protocol="ss", server="1.2.3.4", port=1234)
        url = node.to_socks5_url()
        self.assertIn("1.2.3.4", url)
        self.assertIn("1234", url)

    def test_parse_shadowsocks_with_mock_config(self):
        from core.proxy_detector import _parse_shadowsocks
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = {
                "configs": [{
                    "server": "1.2.3.4",
                    "server_port": 8388,
                    "method": "aes-256-gcm",
                    "password": "test",
                    "remarks": "TestSS"
                }],
                "index": 0
            }
            cfg_path = os.path.join(tmpdir, "gui-config.json")
            with open(cfg_path, "w") as f:
                json.dump(cfg, f)
            node = _parse_shadowsocks(tmpdir)
            self.assertIsNotNone(node)
            self.assertEqual(node.server, "1.2.3.4")
            self.assertEqual(node.port, 8388)
            self.assertEqual(node.protocol, "ss")


# ── antigravity_manager 测试 ──────────────────────────────────────

class TestAntigravityManager(unittest.TestCase):

    def test_get_version_returns_string(self):
        from core.antigravity_manager import AntigravityManager
        mgr = AntigravityManager()
        version = mgr.get_version()
        self.assertIsInstance(version, str)
        # 版本格式应包含数字
        self.assertTrue(any(c.isdigit() for c in version),
                        f"版本 '{version}' 不含数字")

    def test_get_config_port_reads_7895(self):
        from core.antigravity_manager import AntigravityManager, AG_CONFIG
        mgr = AntigravityManager()
        if AG_CONFIG.exists():
            port = mgr.get_config_port()
            self.assertIsInstance(port, int)
            self.assertGreater(port, 0)

    def test_heal_with_mock_paths(self):
        """测试自愈逻辑（模拟文件不存在的场景）"""
        from core.antigravity_manager import AntigravityManager
        import core.antigravity_manager as ag_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            mock_ag_dir = tmp / "antigravity"
            mock_ag_dir.mkdir()
            mock_backup_dir = tmp / "backup"
            mock_backup_dir.mkdir()

            # 写一个端口错误的 config.json
            bad_config = {"proxy": {"port": 7890, "host": "127.0.0.1", "type": "socks5"}}
            (mock_ag_dir / "config.json").write_text(json.dumps(bad_config))

            # 写一个备份 version.dll（内容随意）
            (mock_backup_dir / "version.dll").write_bytes(b"fake_dll")

            # 临时替换模块常量
            orig_ag_dir = ag_mod.AG_DIR
            orig_ag_config = ag_mod.AG_CONFIG
            orig_ag_dll = ag_mod.AG_DLL
            orig_backup_dir = ag_mod.BACKUP_DIR
            orig_backup_dll = ag_mod.BACKUP_DLL
            orig_backup_config = ag_mod.BACKUP_CONFIG

            ag_mod.AG_DIR = mock_ag_dir
            ag_mod.AG_CONFIG = mock_ag_dir / "config.json"
            ag_mod.AG_DLL = mock_ag_dir / "version.dll"
            ag_mod.BACKUP_DIR = mock_backup_dir
            ag_mod.BACKUP_DLL = mock_backup_dir / "version.dll"
            ag_mod.BACKUP_CONFIG = mock_backup_dir / "config.json"

            try:
                mgr = AntigravityManager()
                status = mgr.get_status()
                self.assertFalse(status.dll_present)
                self.assertFalse(status.port_correct)
                self.assertTrue(status.needs_heal)

                actions = mgr.heal()
                self.assertTrue(any("version.dll" in a for a in actions))
                self.assertTrue(any("7895" in a for a in actions))

                # 验证修复后状态
                status2 = mgr.get_status()
                self.assertTrue(status2.dll_present)
                self.assertTrue(status2.port_correct)
                self.assertFalse(status2.needs_heal)
            finally:
                ag_mod.AG_DIR = orig_ag_dir
                ag_mod.AG_CONFIG = orig_ag_config
                ag_mod.AG_DLL = orig_ag_dll
                ag_mod.BACKUP_DIR = orig_backup_dir
                ag_mod.BACKUP_DLL = orig_backup_dll
                ag_mod.BACKUP_CONFIG = orig_backup_config


# ── updater 测试 ──────────────────────────────────────────────────

class TestUpdater(unittest.TestCase):

    @patch("requests.get")
    def test_proxy_updater_get_remote_info(self, mock_get):
        from core.updater import ProxyUpdater
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": "v2.4",
            "assets": [{
                "name": "antigravity-proxy-v2.4-ide-win-x64.zip",
                "browser_download_url": "https://github.com/yuaotian/antigravity-proxy/releases/download/v2.4/antigravity-proxy-v2.4-ide-win-x64.zip"
            }],
            "body": ""
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        pu = ProxyUpdater()
        info = pu.get_remote_info()
        self.assertEqual(info["version"], "2.4")
        self.assertIn("v2.4", info["asset_url"])

    @patch("requests.get")
    def test_cn_updater_get_remote_commit(self, mock_get):
        from core.updater import CNUpdater
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"sha": "abc123def456789"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        cu = CNUpdater()
        sha = cu.get_remote_commit()
        self.assertEqual(sha, "abc123def456789")

    def test_version_comparison(self):
        """测试版本号比较逻辑"""
        def parse(v: str) -> tuple:
            parts = v.replace("-", ".").split(".")
            return tuple(int(x) if x.isdigit() else 0 for x in parts[:4])

        self.assertGreater(parse("2.4"), parse("2.3"))
        self.assertGreater(parse("2.4"), parse("2.3.1"))
        self.assertFalse(parse("2.4") > parse("2.4"))
        self.assertGreater(parse("3.0"), parse("2.9.9"))

    def test_settings_load_save(self):
        from core.updater import _load_settings, _save_settings
        import core.updater as upd_mod
        with tempfile.TemporaryDirectory() as tmpdir:
            orig = upd_mod.SETTINGS_FILE
            upd_mod.SETTINGS_FILE = Path(tmpdir) / "settings.json"
            try:
                # 加载空文件
                s = _load_settings()
                self.assertIsInstance(s, dict)

                # 保存并加载
                _save_settings({"test": "value", "num": 42})
                s2 = _load_settings()
                self.assertEqual(s2["test"], "value")
                self.assertEqual(s2["num"], 42)
            finally:
                upd_mod.SETTINGS_FILE = orig


# ── animations 测试 ───────────────────────────────────────────────

class TestAnimations(unittest.TestCase):

    def test_spring_ease_bounds(self):
        from ui.animations import spring_ease
        # t=0 应该接近 0，t=1 应该接近 1
        self.assertAlmostEqual(spring_ease(0.0), 0.0, places=2)
        self.assertAlmostEqual(spring_ease(1.0), 1.0, places=2)

    def test_ease_out_quad(self):
        from ui.animations import ease_out_quad
        self.assertEqual(ease_out_quad(0.0), 0.0)
        self.assertEqual(ease_out_quad(1.0), 1.0)
        # 中点应大于 0.5（加速型）
        self.assertGreater(ease_out_quad(0.5), 0.5)

    def test_lerp_color(self):
        from ui.animations import lerp_color
        result = lerp_color("#000000", "#ffffff", 0.5)
        self.assertEqual(result, "#7f7f7f")

        result_start = lerp_color("#ff0000", "#0000ff", 0.0)
        self.assertEqual(result_start, "#ff0000")

        result_end = lerp_color("#ff0000", "#0000ff", 1.0)
        self.assertEqual(result_end, "#0000ff")

    def test_ease_in_out_cubic(self):
        from ui.animations import ease_in_out_cubic
        self.assertAlmostEqual(ease_in_out_cubic(0.0), 0.0, places=5)
        self.assertAlmostEqual(ease_in_out_cubic(1.0), 1.0, places=5)
        # 对称：f(0.5) == 0.5
        self.assertAlmostEqual(ease_in_out_cubic(0.5), 0.5, places=5)


# ── mihomo_service 测试 ───────────────────────────────────────────

class TestMihomoService(unittest.TestCase):

    def test_generate_config_structure(self):
        from core.mihomo_service import MihomoService
        primary = {"name": "韩国Z01", "type": "ss", "server": "kr01.example.com", "port": 20042}
        fallback = {"name": "德国原生", "type": "vless", "server": "45.196.97.179", "port": 443}

        config_text = MihomoService.generate_config(primary, fallback)
        self.assertIn("Antigravity-Failover", config_text)
        self.assertIn("7895", config_text)
        self.assertIn("fallback", config_text)
        self.assertIn("韩国Z01", config_text)
        self.assertIn("德国原生", config_text)

    @patch("psutil.process_iter")
    def test_is_running_false(self, mock_iter):
        mock_iter.return_value = []
        from core.mihomo_service import MihomoService
        svc = MihomoService()
        self.assertFalse(svc.is_running())

    @patch("psutil.process_iter")
    def test_is_running_true(self, mock_iter):
        mock_proc = MagicMock()
        mock_proc.info = {"name": "mihomo.exe"}
        mock_iter.return_value = [mock_proc]
        from core.mihomo_service import MihomoService
        svc = MihomoService()
        self.assertTrue(svc.is_running())


if __name__ == "__main__":
    unittest.main(verbosity=2)
