"""
win_components.py — AntigravityHub 现代化 Windows 11 Fluent / Mica 质感组件库
基于 CustomTkinter 提供高 DPI 矢量渲染、自适应排版、状态胶囊与深空灰阶设计系统
"""
from __future__ import annotations
import customtkinter as ctk

# ── 调色板 (Mica Dark / 深空灰阶层次) ───────────────────────────
BG_ROOT         = "#18191D"    # 主窗口底色 (深沉而不死黑)
BG_CARD         = "#222329"    # 顶层功能卡片底色
BG_CARD_HOVER   = "#272830"    # 卡片悬停微光
BG_SUB          = "#1A1B20"    # 嵌套小区域底色
BORDER_COLOR    = "#2F313A"    # 微妙轮廓线

# 强调色体系
COLOR_ACCENT    = "#0078D4"    # Windows 经典主题蓝
COLOR_ACCENT_HOVER = "#1A8CEB"
COLOR_SUCCESS   = "#2EA043"    # 微软流体绿
COLOR_SUCCESS_HOVER = "#3FB950"
COLOR_WARNING   = "#D29922"    # 琥珀黄
COLOR_DANGER    = "#F85149"    # 柔和红
COLOR_DANGER_HOVER = "#FF6B6B"
COLOR_NEUTRAL   = "#32333D"    # 中性次要按钮底色
COLOR_NEUTRAL_HOVER = "#3E404C"

# 文字层级
TEXT_MAIN       = "#FFFFFF"    # 一级高亮正文
TEXT_MUTED      = "#A0A2AD"    # 二级说明正文
TEXT_DIM        = "#6A6C78"    # 辅助与未激活文字

FONT_FAMILY = "Segoe UI"


def get_win_font(size: int = 12, weight: str = "normal") -> ctk.CTkFont:
    """统一字体获取（优先 Segoe UI，微软雅黑平滑适配）"""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


class WinBadge(ctk.CTkFrame):
    """现代药丸胶囊状态徽章 (Pill Badge)"""

    def __init__(self, master, text: str = "", state: str = "info", **kwargs):
        color_map = {
            "success": ("#163820", "#54D28C", "#1F5C34"),
            "warning": ("#3B2B11", "#F2CC60", "#664D1A"),
            "danger":  ("#3D1D1C", "#FF7B72", "#6E2B29"),
            "accent":  ("#112A45", "#58A6FF", "#1D4775"),
            "info":    ("#112A45", "#58A6FF", "#1D4775"),
            "neutral": ("#222329", "#8B949E", "#30363D"),
        }
        bg_col, fg_col, border_col = color_map.get(state, color_map["neutral"])

        super().__init__(
            master,
            fg_color=bg_col,
            border_color=border_col,
            border_width=1,
            corner_radius=12,
            height=26,
            **kwargs,
        )
        self._lbl = ctk.CTkLabel(
            self,
            text=text,
            text_color=fg_col,
            font=get_win_font(11, "bold"),
            padx=10,
            pady=2,
        )
        self._lbl.pack(expand=True, fill="both")

    def update_badge(self, text: str, state: str = "info"):
        color_map = {
            "success": ("#163820", "#54D28C", "#1F5C34"),
            "warning": ("#3B2B11", "#F2CC60", "#664D1A"),
            "danger":  ("#3D1D1C", "#FF7B72", "#6E2B29"),
            "accent":  ("#112A45", "#58A6FF", "#1D4775"),
            "info":    ("#112A45", "#58A6FF", "#1D4775"),
            "neutral": ("#222329", "#8B949E", "#30363D"),
        }
        bg_col, fg_col, border_col = color_map.get(state, color_map["neutral"])
        self.configure(fg_color=bg_col, border_color=border_col)
        self._lbl.configure(text=text, text_color=fg_col)
