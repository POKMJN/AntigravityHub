"""
win_app_window.py — AntigravityHub 现代化桌面主窗口 (Windows 11 Fluent / Mica 质感)
基于 CustomTkinter 构建，原生高 DPI 矢量自适应、圆角卡片流、水平胶囊状态与抽屉式日志
"""
from __future__ import annotations
import os
import sys
import queue
import threading
import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
from typing import Optional, Callable

from ui.win_components import (
    BG_ROOT, BG_CARD, BG_CARD_HOVER, BG_SUB, BORDER_COLOR,
    COLOR_ACCENT, COLOR_ACCENT_HOVER,
    COLOR_SUCCESS, COLOR_SUCCESS_HOVER,
    COLOR_WARNING, COLOR_DANGER, COLOR_DANGER_HOVER,
    COLOR_NEUTRAL, COLOR_NEUTRAL_HOVER,
    TEXT_MAIN, TEXT_MUTED, TEXT_DIM,
    get_win_font, WinBadge,
)
from core.injector import PatchInjector, InjectionStatus
from core.updater import ProxyUpdater, CNUpdater

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

WINDOW_W = 780
WINDOW_H = 680


class WinAppWindow:
    """AntigravityHub 现代化主管理窗口"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("AntigravityHub — 反重力补丁注入与汉化中心")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.minsize(720, 580)
        self.root.configure(fg_color=BG_ROOT)

        self._center_window()

        # 线程安全 UI 调度队列
        self._queue = queue.Queue()
        self._schedule_queue_check()

        # 加载专属高质感科技图标
        try:
            ico_path = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
            if ico_path.exists():
                self.root.iconbitmap(str(ico_path))
        except Exception:
            pass

        # 核心服务
        self._proxy_updater = ProxyUpdater()
        self._cn_updater = CNUpdater()
        self._log_drawer_visible = False

        # 构建现代化 Fluent 界面
        self._build_ui()

        # 启动后执行状态检测
        self.root.after(400, self._auto_check_and_prompt)

    def _center_window(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - WINDOW_W) // 2)
        y = max(0, (sh - WINDOW_H) // 2)
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}+{x}+{y}")

    def _schedule_queue_check(self):
        try:
            while True:
                fn = self._queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.root.after(50, self._schedule_queue_check)

    def dispatch(self, fn: Callable):
        """线程安全地在 UI 主线程调度执行"""
        self._queue.put(fn)

    def _build_ui(self):
        root = self.root
        pad_x = 22

        # ── 1. 顶部智能横幅通知栏 (InfoBar) ─────────────────────────
        self._infobar_frame = ctk.CTkFrame(
            root,
            fg_color="#163820",
            border_color="#1F5C34",
            border_width=1,
            corner_radius=10,
            height=38,
        )
        self._infobar_frame.pack(fill="x", padx=pad_x, pady=(14, 6))
        self._infobar_frame.pack_propagate(False)

        info_box = ctk.CTkFrame(self._infobar_frame, fg_color="transparent")
        info_box.pack(fill="both", expand=True, padx=14)

        self._lbl_infobar = ctk.CTkLabel(
            info_box,
            text="✓ 反重力环境状态优良，内置代理补丁与中文汉化已全部生效就绪。",
            font=get_win_font(12, "bold"),
            text_color="#54D28C",
            anchor="w",
        )
        self._lbl_infobar.pack(side="left")

        # ── 2. 主卡片列表 (平滑滚动视图) ───────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            root,
            fg_color="transparent",
            corner_radius=10,
        )
        self._scroll.pack(fill="both", expand=True, padx=pad_x, pady=(4, 6))

        # 卡片 1: 反重力核心补丁注入与汉化管理
        self._build_patch_card(self._scroll)

        # 卡片 2: 云端版本同步与检查
        self._build_update_card(self._scroll)

        # ── 3. 日志抽屉面板 (可折叠) ──────────────────────────────
        self._drawer_frame = ctk.CTkFrame(
            root,
            fg_color=BG_CARD,
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=12,
        )

        drawer_top = ctk.CTkFrame(self._drawer_frame, fg_color="transparent")
        drawer_top.pack(fill="x", padx=16, pady=(10, 6))

        ctk.CTkLabel(
            drawer_top,
            text="📜 运行事件与注入操作日志",
            font=get_win_font(12, "bold"),
            text_color=TEXT_MAIN,
        ).pack(side="left")

        ctk.CTkButton(
            drawer_top,
            text="收起 ✕",
            command=self._toggle_log_drawer,
            font=get_win_font(11),
            fg_color=COLOR_NEUTRAL,
            hover_color=COLOR_NEUTRAL_HOVER,
            corner_radius=6,
            width=65,
            height=26,
        ).pack(side="right")

        self._log_textbox = ctk.CTkTextbox(
            self._drawer_frame,
            font=("Consolas", 11),
            fg_color=BG_SUB,
            text_color=TEXT_MUTED,
            corner_radius=8,
            height=140,
            wrap="word",
        )
        self._log_textbox.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self._log_textbox.configure(state="disabled")

        # ── 4. 底部现代状态栏 ─────────────────────────────────────
        self._build_bottom_bar(root, pad_x)

    def _build_patch_card(self, parent):
        """卡片 1: 反重力运行环境与内置补丁"""
        card = ctk.CTkFrame(
            parent,
            fg_color=BG_CARD,
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=14,
        )
        card.pack(fill="x", pady=(0, 10))

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=16)

        # 标题栏
        head = ctk.CTkFrame(content, fg_color="transparent")
        head.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            head,
            text="反重力补丁注入与中文汉化中心",
            font=get_win_font(15, "bold"),
            text_color=TEXT_MAIN,
        ).pack(side="left")

        ctk.CTkLabel(
            head,
            text="内置免代理补丁与中文汉化，支持一键注入与官方原版一键还原",
            font=get_win_font(11),
            text_color=TEXT_MUTED,
            padx=12,
        ).pack(side="left")

        # 状态行：左侧应用高质感图标与版本信息，右侧水平胶囊徽章
        status_row = ctk.CTkFrame(content, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 12))

        # 3D 悬浮图标
        try:
            ico_png = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
            if ico_png.exists():
                from PIL import Image
                pil_img = Image.open(ico_png)
                self._app_logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(44, 44))
                lbl_logo = ctk.CTkLabel(status_row, text="", image=self._app_logo_img)
                lbl_logo.pack(side="left", padx=(0, 14))
        except Exception:
            pass

        left = ctk.CTkFrame(status_row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        self._lbl_ag_ver = ctk.CTkLabel(
            left,
            text="Antigravity IDE: 检测中…",
            font=get_win_font(13, "bold"),
            text_color=TEXT_MAIN,
            anchor="w",
        )
        self._lbl_ag_ver.pack(anchor="w")

        self._lbl_ag_detail = ctk.CTkLabel(
            left,
            text="正在读取本地环境配置与离线补丁完整性…",
            font=get_win_font(11),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self._lbl_ag_detail.pack(anchor="w", pady=(3, 0))

        # 状态胶囊组 (水平排布，绝不重叠)
        badges_row = ctk.CTkFrame(status_row, fg_color="transparent")
        badges_row.pack(side="right")

        self._badge_proxy = WinBadge(badges_row, text="免代理补丁: 检测中", state="info")
        self._badge_proxy.pack(side="left", padx=(0, 6))

        self._badge_cn = WinBadge(badges_row, text="中文汉化: 检测中", state="info")
        self._badge_cn.pack(side="left")

        # 分割线
        sep = ctk.CTkFrame(content, fg_color=BORDER_COLOR, height=1)
        sep.pack(fill="x", pady=(0, 12))

        # 操作按钮第一行：超显眼「⚡ 一键全自动热注入」主按钮
        btn_r1 = ctk.CTkFrame(content, fg_color="transparent")
        btn_r1.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            btn_r1,
            text="⚡ 一键全自动注入 (免代理补丁 + 完整中文汉化，推荐)",
            command=self._action_inject_all,
            font=get_win_font(13, "bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            corner_radius=8,
            height=38,
        ).pack(fill="x")

        # 操作按钮第二行：四个均分次要功能按钮
        btn_r2 = ctk.CTkFrame(content, fg_color="transparent")
        btn_r2.pack(fill="x")

        btn_r2.columnconfigure(0, weight=1)
        btn_r2.columnconfigure(1, weight=1)
        btn_r2.columnconfigure(2, weight=1)
        btn_r2.columnconfigure(3, weight=1)

        ctk.CTkButton(
            btn_r2,
            text="🌐 改中文 (注入汉化)",
            command=self._action_inject_cn,
            font=get_win_font(12),
            fg_color=COLOR_NEUTRAL,
            hover_color=COLOR_NEUTRAL_HOVER,
            corner_radius=8,
            height=34,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            btn_r2,
            text="🛡 注入免代理补丁",
            command=self._action_inject_proxy,
            font=get_win_font(12),
            fg_color=COLOR_NEUTRAL,
            hover_color=COLOR_NEUTRAL_HOVER,
            corner_radius=8,
            height=34,
        ).grid(row=0, column=1, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            btn_r2,
            text="↩ 还原官方原版英文",
            command=self._action_restore,
            font=get_win_font(12),
            fg_color=COLOR_NEUTRAL,
            hover_color=COLOR_NEUTRAL_HOVER,
            corner_radius=8,
            height=34,
        ).grid(row=0, column=2, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            btn_r2,
            text="⟳ 刷新检测",
            command=self._refresh_status,
            font=get_win_font(12),
            fg_color=COLOR_NEUTRAL,
            hover_color=COLOR_NEUTRAL_HOVER,
            corner_radius=8,
            height=34,
        ).grid(row=0, column=3, sticky="ew")



    def _build_update_card(self, parent):
        """卡片 3: 云端版本同步与检查"""
        card = ctk.CTkFrame(
            parent,
            fg_color=BG_CARD,
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=14,
        )
        card.pack(fill="x", pady=(0, 10))

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=16)

        head = ctk.CTkFrame(content, fg_color="transparent")
        head.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            head,
            text="云端补丁同步与更新检查",
            font=get_win_font(15, "bold"),
            text_color=TEXT_MAIN,
        ).pack(side="left")

        ctk.CTkLabel(
            head,
            text="内置离线补丁为基线保底，联网时可同步 GitHub 最新发布",
            font=get_win_font(11),
            text_color=TEXT_MUTED,
            padx=12,
        ).pack(side="left")

        # 两列子卡片
        cols = ctk.CTkFrame(content, fg_color="transparent")
        cols.pack(fill="x")
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        # 1. antigravity-proxy
        c1 = ctk.CTkFrame(cols, fg_color=BG_SUB, border_color=BORDER_COLOR, border_width=1, corner_radius=10)
        c1.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        c1_box = ctk.CTkFrame(c1, fg_color="transparent")
        c1_box.pack(fill="both", expand=True, padx=14, pady=12)

        ctk.CTkLabel(c1_box, text="🔧 antigravity-proxy", font=get_win_font(12, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        self._lbl_proxy_cloud = ctk.CTkLabel(c1_box, text="版本: 本地内置 2.4", font=get_win_font(11), text_color=TEXT_MUTED)
        self._lbl_proxy_cloud.pack(anchor="w", pady=(2, 8))

        ctk.CTkButton(
            c1_box,
            text="检查更新",
            command=self._check_proxy_update,
            font=get_win_font(11),
            fg_color=COLOR_NEUTRAL,
            hover_color=COLOR_NEUTRAL_HOVER,
            corner_radius=6,
            height=28,
        ).pack(anchor="w")

        # 2. antigravity2-cn
        c2 = ctk.CTkFrame(cols, fg_color=BG_SUB, border_color=BORDER_COLOR, border_width=1, corner_radius=10)
        c2.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

        c2_box = ctk.CTkFrame(c2, fg_color="transparent")
        c2_box.pack(fill="both", expand=True, padx=14, pady=12)

        ctk.CTkLabel(c2_box, text="🌐 antigravity2-cn", font=get_win_font(12, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        self._lbl_cn_cloud = ctk.CTkLabel(c2_box, text="汉化包: 本地内置就绪", font=get_win_font(11), text_color=TEXT_MUTED)
        self._lbl_cn_cloud.pack(anchor="w", pady=(2, 8))

        ctk.CTkButton(
            c2_box,
            text="检查更新",
            command=self._check_cn_update,
            font=get_win_font(11),
            fg_color=COLOR_NEUTRAL,
            hover_color=COLOR_NEUTRAL_HOVER,
            corner_radius=6,
            height=28,
        ).pack(anchor="w")

    def _build_bottom_bar(self, parent, pad_x: int):
        """底部精简状态栏"""
        bar = ctk.CTkFrame(
            parent,
            fg_color=BG_CARD,
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=10,
            height=40,
        )
        bar.pack(fill="x", padx=pad_x, pady=(4, 14), side="bottom")
        bar.pack_propagate(False)

        content = ctk.CTkFrame(bar, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=14)

        self._lbl_status_msg = ctk.CTkLabel(
            content,
            text="✓ 就绪：反重力综合管理中心运行中",
            font=get_win_font(11),
            text_color=TEXT_MUTED,
        )
        self._lbl_status_msg.pack(side="left")

        self._btn_drawer = ctk.CTkButton(
            content,
            text="📜 展开日志",
            command=self._toggle_log_drawer,
            font=get_win_font(11),
            fg_color="transparent",
            hover_color=BG_SUB,
            text_color=TEXT_MUTED,
            corner_radius=6,
            width=80,
            height=26,
        )
        self._btn_drawer.pack(side="right")

    def _toggle_log_drawer(self):
        pad_x = 22
        if self._log_drawer_visible:
            self._drawer_frame.pack_forget()
            self._btn_drawer.configure(text="📜 展开日志")
            self._log_drawer_visible = False
        else:
            self._drawer_frame.pack(fill="x", padx=pad_x, pady=(0, 6), before=self.root.winfo_children()[-1])
            self._btn_drawer.configure(text="收起日志 ▲")
            self._log_drawer_visible = True

    def log(self, text: str, level: str = "info"):
        import time
        ts = time.strftime("[%H:%M:%S]")
        msg = f"{ts} {text}\n"

        def _do():
            self._log_textbox.configure(state="normal")
            self._log_textbox.insert("end", msg)
            self._log_textbox.see("end")
            self._log_textbox.configure(state="disabled")
            self._lbl_status_msg.configure(text=f"{text}")

        self.dispatch(_do)

    # ────────────────────────────────────────────────────────────
    # 状态检测与业务交互
    # ────────────────────────────────────────────────────────────

    def _auto_check_and_prompt(self):
        """启动自检"""
        def _bg():
            status = PatchInjector.check_status()

            def _update():
                # 1. 刷新界面控件
                self._update_status_ui(status)

                # 2. 智能横幅与决策
                if not status.is_installed:
                    self._show_infobar("未检测到 Antigravity 安装目录，请确认反重力已正确安装。", "warning")
                elif status.needs_injection:
                    msg = f"检测到反重力处于未注入状态（{status.status_summary}）。是否立即一键热注入？"
                    self._show_infobar(f"⚠️ {msg}", "warning")
                    if messagebox.askyesno("智能检测决策提示", f"{msg}\n\n点击「是」将自动写入免代理补丁与中文汉化，完全不影响官方功能。", parent=self.root):
                        self._action_inject_all()
                else:
                    self._show_infobar("✓ 反重力运行环境优良，免代理补丁与中文汉化已全部生效就绪。", "success")

            self.dispatch(_update)

        threading.Thread(target=_bg, daemon=True).start()

    def _refresh_status(self):
        self.log("正在重新检测反重力运行环境与补丁状态…")
        self._auto_check_and_prompt()

    def _show_infobar(self, text: str, state: str = "info"):
        col_map = {
            "success": ("#163820", "#1F5C34", "#54D28C"),
            "warning": ("#3B2B11", "#664D1A", "#F2CC60"),
            "danger":  ("#3D1D1C", "#6E2B29", "#FF7B72"),
            "info":    ("#112A45", "#1D4775", "#58A6FF"),
        }
        bg, border, fg = col_map.get(state, col_map["info"])
        self._infobar_frame.configure(fg_color=bg, border_color=border)
        self._lbl_infobar.configure(text=text, text_color=fg)

    def _update_status_ui(self, status: InjectionStatus):
        run_tag = " (运行中)" if status.is_running else " (已停止)"
        self._lbl_ag_ver.configure(text=f"Antigravity IDE  {status.version_str}{run_tag}")
        self._lbl_ag_detail.configure(text=f"状态概况: {status.status_summary}")

        self._badge_proxy.update_badge(
            "免代理补丁: 已就绪" if status.proxy_injected else "免代理补丁: 未注入",
            "success" if status.proxy_injected else "danger"
        )
        self._badge_cn.update_badge(
            "语言: 简体中文" if status.cn_injected else "语言: 原版英文",
            "success" if status.cn_injected else "warning"
        )

    # ────────────────────────────────────────────────────────────
    # 补丁注入动作
    # ────────────────────────────────────────────────────────────

    def _action_inject_all(self):
        """一键全自动热注入"""
        self.log("🚀 开始执行一键全自动注入 (免代理补丁 + 中文汉化)...")

        def _bg():
            ok = PatchInjector.inject_all(log_cb=self.log)
            if ok:
                self.log("✓ 全自动注入完成！免代理补丁与中文汉化均已生效。", "success")
                self.dispatch(lambda: messagebox.showinfo(
                    "注入成功",
                    "反重力补丁已成功注入！\n免代理补丁已就绪，中文汉化已生效。\n若 Antigravity 正在运行，重启即可直接体验！",
                    parent=self.root
                ))
            else:
                self.log("✗ 注入过程中存在失败项，请检查日志", "error")
                self.dispatch(lambda: messagebox.showerror(
                    "注入失败",
                    "注入失败，请查看运行日志控制台获取详细报错。",
                    parent=self.root
                ))
            self._auto_check_and_prompt()

        threading.Thread(target=_bg, daemon=True).start()

    def _action_inject_proxy(self):
        """仅注入代理补丁"""
        self.log("🛡 开始注入免代理补丁 (version.dll + config.json)...")
        def _bg():
            ok = PatchInjector.inject_proxy(log_cb=self.log)
            if ok:
                self.log("✓ 免代理补丁注入成功！", "success")
                self.dispatch(lambda: messagebox.showinfo("注入成功", "免代理补丁注入成功！", parent=self.root))
            self._auto_check_and_prompt()
        threading.Thread(target=_bg, daemon=True).start()

    def _action_inject_cn(self):
        """仅注入汉化包"""
        self.log("🌐 开始改中文 (注入汉化包 app.asar)...")
        def _bg():
            ok = PatchInjector.inject_cn(log_cb=self.log)
            if ok:
                self.log("✓ 中文汉化包注入成功！", "success")
                self.dispatch(lambda: messagebox.showinfo("注入成功", "中文汉化包注入成功！重启 Antigravity 即可看到中文界面。", parent=self.root))
            self._auto_check_and_prompt()
        threading.Thread(target=_bg, daemon=True).start()

    def _action_restore(self):
        """还原官方原生"""
        if not messagebox.askyesno("确认还原", "确定要卸载代理补丁和汉化包、还原为官方原版 Antigravity 吗？", parent=self.root):
            return
        self.log("↩ 正在还原官方原版...")
        def _bg():
            ok = PatchInjector.restore_original(log_cb=self.log)
            if ok:
                self.log("✓ 已成功还原为官方原生状态！", "success")
                self.dispatch(lambda: messagebox.showinfo("还原完成", "已恢复为官方原生英文版本。", parent=self.root))
            self._auto_check_and_prompt()
        threading.Thread(target=_bg, daemon=True).start()

    # ────────────────────────────────────────────────────────────
    # 云端更新检查
    # ────────────────────────────────────────────────────────────

    def _check_proxy_update(self):
        self.log("正在检查 antigravity-proxy 云端更新...")
        def _bg():
            info = self._proxy_updater.check_update()
            def _update():
                if info.has_update:
                    self._lbl_proxy_cloud.configure(text=f"发现新版本: {info.latest_version}", text_color=COLOR_WARNING)
                    self.log(f"发现新版本: {info.latest_version}")
                else:
                    self._lbl_proxy_cloud.configure(text=f"已是最新 ({info.current_version})", text_color=COLOR_SUCCESS)
                    self.log("✓ antigravity-proxy 已是最新版", "success")
            self.dispatch(_update)
        threading.Thread(target=_bg, daemon=True).start()

    def _check_cn_update(self):
        self.log("正在检查 antigravity2-cn 云端更新...")
        def _bg():
            info = self._cn_updater.check_update()
            def _update():
                if info.has_update:
                    self._lbl_cn_cloud.configure(text=f"发现新汉化: {info.latest_version}", text_color=COLOR_WARNING)
                    self.log(f"发现新汉化: {info.latest_version}")
                else:
                    self._lbl_cn_cloud.configure(text="本地汉化已是最新", text_color=COLOR_SUCCESS)
                    self.log("✓ antigravity2-cn 已是最新版", "success")
            self.dispatch(_update)
        threading.Thread(target=_bg, daemon=True).start()

    def run(self):
        self.root.mainloop()
