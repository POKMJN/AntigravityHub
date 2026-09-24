"""
test_injector.py — 单元测试 PatchInjector
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.injector import PatchInjector, get_builtin_asset, InjectionStatus


class TestPatchInjector(unittest.TestCase):

    def test_builtin_assets_exist(self):
        """验证内置离线补丁资源完整"""
        dll = get_builtin_asset("proxy/version.dll")
        asar = get_builtin_asset("cn/app.asar")
        cfg = get_builtin_asset("proxy/config.json")
        self.assertTrue(dll.exists(), f"内置 DLL 不存在: {dll}")
        self.assertTrue(asar.exists(), f"内置 ASAR 不存在: {asar}")
        self.assertTrue(cfg.exists(), f"内置 Config 不存在: {cfg}")
        self.assertGreater(dll.stat().st_size, 100_000)
        self.assertGreater(asar.stat().st_size, 10_000_000)

    def test_check_status_returns_valid_namedtuple(self):
        """验证检测返回类型与结构"""
        status = PatchInjector.check_status()
        self.assertIsInstance(status, InjectionStatus)
        self.assertIsInstance(status.is_installed, bool)
        self.assertIsInstance(status.is_running, bool)
        self.assertIsInstance(status.proxy_injected, bool)
        self.assertIsInstance(status.port_configured, bool)
        self.assertIsInstance(status.cn_injected, bool)
        self.assertIsInstance(status.status_summary, str)

    def test_get_ag_version(self):
        """测试获取版本号返回字符串"""
        ver = PatchInjector.get_ag_version()
        self.assertIsInstance(ver, str)
        self.assertTrue(len(ver) > 0)


if __name__ == "__main__":
    unittest.main()
