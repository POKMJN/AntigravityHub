"""
app_window.py — AntigravityHub 主窗口
Apple 风格深色 UI，无边框自定义标题栏，Spring 动画
"""
from __future__ import annotations
import os
import sys
import json
import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional, Callable
from pathlib import Path

from ui.components import (
    BG_PRIMARY, BG_CARD, BG_CARD_HOVER,
    ACCENT, SUCCESS, WARNING, DANGER, TEXT_PRIMARY, TEXT_SECONDARY, SEPARATOR,
    CARD_PAD, RADIUS,
    StatusCard, ToggleSwitch, AppleButton, LogPanel, UpdateBadge,
    SectionLabel, Divider, ProgressBar, WindowControlButton,
    _rounded_rect,
)
from ui.animations import Animator, spring_ease, ease_out_quad, fade_in

# 延迟导入核心模块（避免打包问题）
def _import_core():
    from core.mihomo_service import MihomoService
    from core.antigravity_manager import AntigravityManager
    from core.proxy_detector import detect_proxy_clients
    from core.updater import ProxyUpdater, CNUpdater
    return MihomoService, AntigravityManager, detect_proxy_clients, ProxyUpdater, CNUpdater


WINDOW_W = 620
WINDOW_H = 800
TITLE_BAR_H = 46


class TitleBar(tk.Frame):
    """自定义无边框标题栏，支持拖动，包含 macOS 点缀与 Windows 标准控制按钮"""

    def __init__(self, master, title: str, on_close: Callable, on_minimize: Callable, **kw):
        super().__init__(master, bg=BG_PRIMARY, height=TITLE_BAR_H, **kw)
        self.pack_propagate(False)

        # 拖动绑定
        self._drag_x = 0
        self._drag_y = 0
        self.bind("<Button-1>", self._start_drag)
        self.bind("<B1-Motion>", self._drag)

        # 左侧 macOS 风格胶囊小圆点点缀
        decor_frame = tk.Frame(self, bg=BG_PRIMARY)
        decor_frame.pack(side=tk.LEFT, padx=(18, 0))
        for col in ["#FF5F57", "#FEBC2E", "#28C840"]:
            dot = tk.Canvas(decor_frame, width=12, height=12, bg=BG_PRIMARY, highlightthickness=0)
            dot.create_oval(0, 0, 11, 11, fill=col, outline="")
            dot.pack(side=tk.LEFT, padx=3)

        # 右侧 Windows 风格控制按钮组（包含鲜艳醒目的关闭 ✕ 和最小化 —）
        right_frame = tk.Frame(self, bg=BG_PRIMARY)
        right_frame.pack(side=tk.RIGHT)

        WindowControlButton(right_frame, btn_type="minimize", on_click=on_minimize).pack(side=tk.LEFT)
        WindowControlButton(right_frame, btn_type="close", on_click=on_close).pack(side=tk.LEFT)

        # 标题（居中，高对比清晰字体）
        title_lbl = tk.Label(
            self, text=title,
            font=("SF Pro Display", 14, "bold"),
            fg=TEXT_PRIMARY, bg=BG_PRIMARY,
        )
        title_lbl.place(relx=0.5, rely=0.5, anchor="center")
        title_lbl.bind("<Button-1>", self._start_drag)
        title_lbl.bind("<B1-Motion>", self._drag)

    def _start_drag(self, e):
        self._drag_x = e.x_root
        self._drag_y = e.y_root

    def _drag(self, e):
        top = self.winfo_toplevel()
        dx = e.x_root - self._drag_x
        dy = e.y_root - self._drag_y
        x = top.winfo_x() + dx
        y = top.winfo_y() + dy
        top.geometry(f"+{x}+{y}")
        self._drag_x = e.x_root
        self._drag_y = e.y_root


class TrafficLight(tk.Canvas):
    """macOS 风格交通灯按钮"""

    D = 13

    def __init__(self, master, color: str, on_click: Callable, **kw):
        super().__init__(master, width=self.D, height=self.D,
                         bg=BG_PRIMARY, highlightthickness=0, **kw)
        self._color = color
        self._on_click = on_click
        self._hover = False
        self._draw()
        self.bind("<Button-1>", lambda e: on_click())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.configure(cursor="hand2")

    def _draw(self):
        self.delete("all")
        color = self._color if self._hover else self._color
        self.create_oval(0, 0, self.D, self.D, fill=color, outline="")

    def _enter(self, _=None):
        self._hover = True
        self._draw()

    def _leave(self, _=None):
        self._hover = False
        self._draw()


class ProxyCard(tk.Frame):
    """定向代理状态卡片"""

    def __init__(self, master, mihomo_svc, log_fn: Callable, **kw):
        super().__init__(master, bg=BG_CARD, **kw)
        self._svc = mihomo_svc
        self._log = log_fn
        self._running = False
        self._build()

    def _build(self):
        pad = CARD_PAD
        # 顶部行
        top = tk.Frame(self, bg=BG_CARD)
        top.pack(fill=tk.X, padx=pad, pady=(pad, 12))

        left = tk.Frame(top, bg=BG_CARD)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._dot = _PulseDot(left, bg=BG_CARD)
        self._dot.pack(side=tk.LEFT, padx=(0, 12))

        txt = tk.Frame(left, bg=BG_CARD)
        txt.pack(side=tk.LEFT)

        tk.Label(txt, text="🛡  定向代理 (Antigravity 专线)", font=("SF Pro Display", 16, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w")

        self._node_lbl = tk.Label(txt, text="检测节点状态中…",
                                  font=("SF Pro Text", 13), fg=TEXT_SECONDARY, bg=BG_CARD)
        self._node_lbl.pack(anchor="w", pady=(3, 0))

        # 开关
        self._toggle = ToggleSwitch(top, initial=False, on_toggle=self._on_toggle)
        self._toggle.pack(side=tk.RIGHT, padx=(10, 0))

        # 分隔线
        Divider(self).pack(fill=tk.X, padx=pad)

        # 底部行：延迟 + 按钮
        bottom = tk.Frame(self, bg=BG_CARD)
        bottom.pack(fill=tk.X, padx=pad, pady=(12, pad))

        self._latency_lbl = tk.Label(
            bottom, text="延迟: –",
            font=("SF Mono", 13, "bold") if "SF Mono" in tkfont.families() else ("Consolas", 13, "bold"),
            fg=TEXT_SECONDARY, bg=BG_CARD,
        )
        self._latency_lbl.pack(side=tk.LEFT)

        AppleButton(bottom, text="切换节点", on_click=self._switch_node,
                    style="secondary", width=96, height=36).pack(side=tk.RIGHT)
        AppleButton(bottom, text="测速", on_click=self._test_latency,
                    style="secondary", width=80, height=36).pack(side=tk.RIGHT, padx=(0, 10))

    def _on_toggle(self, state: bool):
        if state:
            self._log("正在启动定向代理…", "info")
            threading.Thread(target=self._do_start, daemon=True).start()
        else:
            self._log("正在停止定向代理…", "info")
            threading.Thread(target=self._do_stop, daemon=True).start()

    def _do_start(self):
        ok = self._svc.start()
        if ok:
            self._running = True
            self._dot.set_online(True)
            self._log("✓ 定向代理已启动 (端口 7895)", "success")
            self._refresh_node()
        else:
            self._running = False
            self._toggle.set_state(False, animate=True)
            self._dot.set_online(False)
            self._log("✗ 启动失败，请检查 mihomo.exe", "error")

    def _do_stop(self):
        self._svc.stop()
        self._running = False
        self._dot.set_online(False)
        self._node_lbl.configure(text="已停止运行")
        self._latency_lbl.configure(text="延迟: –")
        self._log("定向代理已停止", "info")

    def _refresh_node(self):
        info = self._svc.get_current_node()
        node_name = info.get("name", "未知")
        self._node_lbl.configure(text=f"活跃节点: {node_name}")

    def _test_latency(self):
        self._latency_lbl.configure(text="测速中…")
        self._log("正在测试当前节点延迟…", "info")

        def do():
            try:
                info = self._svc.get_current_node()
                node_name = info.get("name", "")
                ms = self._svc.test_latency(node_name) if node_name else None
                if ms:
                    color = SUCCESS if ms < 200 else (WARNING if ms < 500 else DANGER)
                    self._latency_lbl.configure(text=f"延迟: {ms}ms", fg=color)
                    self._log(f"✓ 节点 {node_name} 延迟: {ms}ms", "success")
                else:
                    self._latency_lbl.configure(text="延迟: 超时", fg=DANGER)
                    self._log("✗ 节点测速超时", "warning")
            except Exception as e:
                self._latency_lbl.configure(text="延迟: 错误")
                self._log(f"✗ 测速异常: {e}", "error")

        threading.Thread(target=do, daemon=True).start()

    def _switch_node(self):
        """在韩国→德国之间切换"""
        info = self._svc.get_current_node()
        current = info.get("name", "")
        next_node = "德国原生·H2·1倍消耗" if "韩国" in current else "🇰🇷 韩国Z01"
        ok = self._svc.switch_node("Antigravity-Failover", next_node)
        if ok:
            self._log(f"✓ 已切换节点至: {next_node}", "success")
            self._refresh_node()
        else:
            self._log("✗ 切换失败（请确认代理是否已开启）", "error")

    def refresh_from_service(self):
        """外部调用：刷新卡片状态"""
        running = self._svc.is_running()
        self._toggle.set_state(running, animate=False)
        self._dot.set_online(running)
        if running:
            self._refresh_node()
        else:
            self._node_lbl.configure(text="未运行 (点击开关启动)")


class _PulseDot(tk.Canvas):
    """紧凑脉冲点"""
    D = 10
    def __init__(self, master, **kw):
        super().__init__(master, width=self.D+4, height=self.D+4,
                         highlightthickness=0, **kw)
        self._online = False
        self._pulse = 0.0
        self._anim: Optional[Animator] = None
        self._draw()

    def set_online(self, state: bool):
        self._online = state
        self._draw()
        if state:
            self._start_pulse()

    def _start_pulse(self):
        if self._anim is None:
            self._anim = Animator(self)

        def do():
            if not self._online:
                return
            self._anim.animate(
                duration=1800, easing=ease_out_quad,
                start_value=0.0, end_value=1.0,
                on_update=self._on_pulse,
                on_done=lambda: self.after(800, do) if self._online else None,
            )
        do()

    def _on_pulse(self, v: float):
        self._pulse = v
        self._draw()

    def _draw(self):
        self.delete("all")
        cx = cy = (self.D + 4) / 2
        r = self.D / 2
        color = SUCCESS if self._online else "#48484A"
        if self._online and self._pulse > 0:
            pr = r + self._pulse * r * 0.8
            self.create_oval(cx-pr, cy-pr, cx+pr, cy+pr,
                             fill="", outline=color, width=1.5)
        self.create_oval(cx-r, cy-r, cx+r, cy+r, fill=color, outline="")


class UpdateCard(tk.Frame):
    """antigravity-proxy 或 antigravity2-cn 更新卡片"""

    def __init__(self, master, title: str, emoji: str,
                 updater, log_fn: Callable, **kw):
        super().__init__(master, bg=BG_CARD, **kw)
        self._updater = updater
        self._log = log_fn
        self._title = title
        self._emoji = emoji
        self._build()

    def _build(self):
        pad = CARD_PAD
        inner = tk.Frame(self, bg=BG_CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=pad, pady=pad)

        tk.Label(inner, text=f"{self._emoji}  {self._title}",
                 font=("SF Pro Text", 14, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w")

        self._badge = UpdateBadge(inner)
        self._badge.pack(anchor="w", pady=(8, 12))

        self._progress = ProgressBar(inner, width=220, height=4)
        self._progress.pack(anchor="w", pady=(0, 10))
        self._progress.pack_forget()  # 默认隐藏

        btn_row = tk.Frame(inner, bg=BG_CARD)
        btn_row.pack(anchor="w", pady=(2, 0))

        self._check_btn = AppleButton(
            btn_row, text="检查更新", style="secondary", width=98, height=36,
            on_click=self._check,
        )
        self._check_btn.pack(side=tk.LEFT, padx=(0, 10))

        self._update_btn = AppleButton(
            btn_row, text="立即更新", style="primary", width=98, height=36,
            on_click=self._do_update,
        )
        self._update_btn.pack(side=tk.LEFT)
        self._update_btn.pack_forget()

    def _check(self):
        self._badge.set_checking()
        self._update_btn.pack_forget()

        def do():
            try:
                needs, local, remote = self._updater.needs_update()
                if remote == "连接失败":
                    self._badge.set_error("网络受限")
                    self._log(f"✗ 检查 {self._title} 更新失败: 无法连接 GitHub API (可尝试开启定向代理后重试)", "warning")
                elif needs:
                    self._badge.set_update_available(remote)
                    self._update_btn.pack(side=tk.LEFT)
                    self._log(f"↑ {self._title} 发现新版本: {remote} (当前: {local})", "warning")
                else:
                    self._badge.set_ok(local)
                    self._log(f"✓ {self._title} 已是最新版本 ({local})", "success")
            except Exception as e:
                self._badge.set_error("检查失败")
                self._log(f"✗ 检查 {self._title} 异常: {e}", "error")

        threading.Thread(target=do, daemon=True).start()

    def _do_update(self):
        self._progress.set_progress(0)
        self._progress.pack(anchor="w", pady=(0, 10))
        self._update_btn.pack_forget()
        self._log(f"正在下载更新 {self._title}…", "info")

        def progress_cb(dl: int, total: int):
            if total:
                self._progress.set_progress(dl / total)

        def do():
            ok = self._updater.update(
                progress_cb=progress_cb,
                log_cb=lambda msg: self._log(msg, "info"),
            )
            self._progress.pack_forget()
            if ok:
                self._badge.set_ok()
                self._log(f"✓ {self._title} 更新已完成并就绪", "success")
            else:
                self._badge.set_error("更新失败")
                self._log(f"✗ {self._title} 更新未成功，请检查网络", "error")

        threading.Thread(target=do, daemon=True).start()


class AGStatusCard(tk.Frame):
    """Antigravity IDE 状态卡片"""

    def __init__(self, master, ag_mgr, log_fn: Callable, **kw):
        super().__init__(master, bg=BG_CARD, **kw)
        self._mgr = ag_mgr
        self._log = log_fn
        self._build()

    def _build(self):
        pad = CARD_PAD
        inner = tk.Frame(self, bg=BG_CARD)
        inner.pack(fill=tk.X, padx=pad, pady=pad)

        # 标题行
        title_row = tk.Frame(inner, bg=BG_CARD)
        title_row.pack(fill=tk.X)

        tk.Label(title_row, text="🚀  Antigravity IDE",
                 font=("SF Pro Display", 16, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_CARD).pack(side=tk.LEFT)

        self._ver_lbl = tk.Label(title_row, text="",
                                  font=("SF Pro Text", 13, "bold"),
                                  fg=TEXT_SECONDARY, bg=BG_CARD)
        self._ver_lbl.pack(side=tk.RIGHT)

        # 状态行
        self._status_frame = tk.Frame(inner, bg=BG_CARD)
        self._status_frame.pack(fill=tk.X, pady=(12, 4))

        self._dll_lbl = tk.Label(self._status_frame, text="",
                                  font=("SF Mono", 12) if "SF Mono" in tkfont.families() else ("Consolas", 12),
                                  fg=TEXT_SECONDARY, bg=BG_CARD)
        self._dll_lbl.pack(anchor="w", pady=(0, 3))

        self._port_lbl = tk.Label(self._status_frame, text="",
                                   font=("SF Mono", 12) if "SF Mono" in tkfont.families() else ("Consolas", 12),
                                   fg=TEXT_SECONDARY, bg=BG_CARD)
        self._port_lbl.pack(anchor="w")

        # 按钮行
        btn_row = tk.Frame(inner, bg=BG_CARD)
        btn_row.pack(anchor="w", pady=(14, 0))

        AppleButton(btn_row, text="自动自愈", style="primary", width=92, height=36,
                    on_click=self._heal).pack(side=tk.LEFT, padx=(0, 10))
        AppleButton(btn_row, text="备份配置", style="secondary", width=92, height=36,
                    on_click=self._backup).pack(side=tk.LEFT, padx=(0, 10))
        AppleButton(btn_row, text="刷新状态", style="secondary", width=92, height=36,
                    on_click=self.refresh).pack(side=tk.LEFT)

    def refresh(self):
        def do():
            status = self._mgr.get_status()
            self._ver_lbl.configure(text=f"IDE v{status.version}")
            dll_ok = status.dll_present
            port_ok = status.port_correct
            self._dll_lbl.configure(
                text=f"{'✓' if dll_ok else '✗'} version.dll 动态链接库劫持 {'已正常生效' if dll_ok else '缺失 (需自愈)'}",
                fg=SUCCESS if dll_ok else DANGER,
            )
            self._port_lbl.configure(
                text=f"{'✓' if port_ok else '✗'} 反重力专用代理端口: {status.config_port} {'(正确)' if port_ok else '(漂移异常)'}",
                fg=SUCCESS if port_ok else DANGER,
            )

        threading.Thread(target=do, daemon=True).start()

    def _heal(self):
        self._log("正在执行 IDE 状态自愈检测…", "info")

        def do():
            actions = self._mgr.heal()
            for a in actions:
                level = "success" if "✓" in a else "error"
                self._log(a, level)
            self.refresh()

        threading.Thread(target=do, daemon=True).start()

    def _backup(self):
        self._log("正在备份…", "info")

        def do():
            self._mgr.backup_current()
            self._log("✓ 备份完成", "success")

        threading.Thread(target=do, daemon=True).start()


class AppWindow:
    """主应用窗口"""

    def __init__(self):
        # 导入核心模块
        MihomoService, AntigravityManager, detect_proxy_clients, ProxyUpdater, CNUpdater = _import_core()

        self._mihomo = MihomoService()
        self._ag_mgr = AntigravityManager()
        self._proxy_updater = ProxyUpdater()
        self._cn_updater = CNUpdater()

        # 创建窗口
        self.root = tk.Tk()
        self.root.title("AntigravityHub")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.configure(bg=BG_PRIMARY)
        self.root.resizable(False, False)
        self.root.overrideredirect(True)  # 无边框

        # 居中显示
        self._center_window()

        # 设置图标
        try:
            icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass

        self._build_ui()
        fade_in(self.root, duration=300)

        # 自动刷新
        self._auto_refresh()

    def _center_window(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - WINDOW_W) // 2
        y = (sh - WINDOW_H) // 2
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}+{x}+{y}")

    def _build_ui(self):
        root = self.root

        # ── 标题栏 ──────────────────────────────────────────────
        TitleBar(
            root, title="AntigravityHub",
            on_close=self._quit,
            on_minimize=self._minimize,
        ).pack(fill=tk.X)

        # 分隔线
        Divider(root).pack(fill=tk.X)

        # ── 滚动区域 ─────────────────────────────────────────────
        canvas = tk.Canvas(root, bg=BG_PRIMARY, highlightthickness=0,
                           width=WINDOW_W, height=WINDOW_H - TITLE_BAR_H - 1)
        canvas.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview,
                                  bg=BG_PRIMARY, width=0)  # 隐藏滚动条
        canvas.configure(yscrollcommand=scrollbar.set)

        # 主内容 Frame
        content = tk.Frame(canvas, bg=BG_PRIMARY)
        canvas_win = canvas.create_window(0, 0, anchor="nw", window=content,
                                           width=WINDOW_W)

        def on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        content.bind("<Configure>", on_configure)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        # 全局边距与呼吸感间距
        pad_x = 24
        pad_y = 16

        # ── 定向代理 ─────────────────────────────────────────────
        SectionLabel(content, text="定向代理 (Failover 韩国首选 → 德国备用)").pack(anchor="w", padx=pad_x, pady=(18, 8))
        self._proxy_card = ProxyCard(content, self._mihomo, self._log)
        self._proxy_card.pack(fill=tk.X, padx=pad_x, pady=(0, pad_y))
        self._apply_card_style(self._proxy_card)

        # ── 更新管理 ─────────────────────────────────────────────
        SectionLabel(content, text="补丁与汉化更新 (多通道智能加速)").pack(anchor="w", padx=pad_x, pady=(6, 8))

        update_row = tk.Frame(content, bg=BG_PRIMARY)
        update_row.pack(fill=tk.X, padx=pad_x, pady=(0, pad_y))

        proxy_update_card = UpdateCard(
            update_row, title="代理注入补丁",
            emoji="🔧",
            updater=self._proxy_updater,
            log_fn=self._log,
        )
        proxy_update_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        self._apply_card_style(proxy_update_card)

        cn_update_card = UpdateCard(
            update_row, title="汉化补丁",
            emoji="🌐",
            updater=self._cn_updater,
            log_fn=self._log,
        )
        cn_update_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._apply_card_style(cn_update_card)

        # 启动时自动检查更新
        threading.Thread(target=lambda: (
            proxy_update_card._check(),
            cn_update_card._check(),
        ), daemon=True).start()

        # ── Antigravity IDE ──────────────────────────────────────
        SectionLabel(content, text="Antigravity 状态与自愈防护").pack(anchor="w", padx=pad_x, pady=(6, 8))
        self._ag_card = AGStatusCard(content, self._ag_mgr, self._log)
        self._ag_card.pack(fill=tk.X, padx=pad_x, pady=(0, pad_y))
        self._apply_card_style(self._ag_card)

        # ── 日志 ─────────────────────────────────────────────────
        SectionLabel(content, text="运行日志").pack(anchor="w", padx=pad_x, pady=(6, 8))
        self._log_panel = LogPanel(content, height=150)
        self._log_panel.pack(fill=tk.X, padx=pad_x, pady=(0, pad_y))

        # ── 底部控制按钮栏（包含显眼的退出软件按钮） ────────────
        bottom_row = tk.Frame(content, bg=BG_PRIMARY)
        bottom_row.pack(fill=tk.X, padx=pad_x, pady=(4, 28))

        AppleButton(bottom_row, text="全部启动", style="primary",
                    on_click=self._start_all, width=120, height=36).pack(side=tk.LEFT, padx=(0, 10))
        AppleButton(bottom_row, text="全部停止", style="secondary",
                    on_click=self._stop_all, width=96, height=36).pack(side=tk.LEFT, padx=(0, 10))
        AppleButton(bottom_row, text="安装目录", style="secondary",
                    on_click=self._ag_mgr.open_install_dir, width=96, height=36).pack(side=tk.LEFT)

        # 显眼的红色退出程序大按钮
        AppleButton(bottom_row, text="退出软件", style="danger",
                    on_click=self._quit, width=100, height=36).pack(side=tk.RIGHT)

        # 绑定快捷键（Esc / Alt+F4 直接退出）
        root.bind("<Escape>", lambda e: self._quit())
        root.bind("<Alt-F4>", lambda e: self._quit())

        # 初始刷新
        self.root.after(500, self._proxy_card.refresh_from_service)
        self.root.after(800, self._ag_card.refresh)

    @staticmethod
    def _apply_card_style(card: tk.Frame):
        """统一卡片圆角视觉（通过 configure highlightbackground）"""
        try:
            card.configure(relief="flat", bd=0,
                            highlightbackground=SEPARATOR,
                            highlightthickness=1)
        except Exception:
            pass

    def _log(self, msg: str, level: str = "info"):
        try:
            self._log_panel.append(msg, level)
        except Exception:
            print(f"[log] {msg}")

    def _start_all(self):
        self._log("一键全部启动…", "info")
        self._proxy_card._toggle.set_state(True)
        self._proxy_card._on_toggle(True)

    def _stop_all(self):
        self._log("一键全部停止…", "info")
        self._proxy_card._toggle.set_state(False)
        self._proxy_card._on_toggle(False)

    def _auto_refresh(self):
        """每 30 秒自动刷新状态"""
        def do():
            try:
                self._proxy_card.refresh_from_service()
                self._ag_card.refresh()
            except Exception:
                pass
            self.root.after(30_000, do)

        self.root.after(30_000, do)

    def _minimize(self):
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.after(200, lambda: self.root.overrideredirect(True))

    def _quit(self):
        self._mihomo.stop()
        self.root.destroy()
        sys.exit(0)

    def run(self):
        self.root.mainloop()
