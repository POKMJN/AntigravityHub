"""
components.py — Apple 风格 UI 组件库

所有组件基于 tkinter Canvas / Frame，实现精细视觉和 Spring 动画。
"""
from __future__ import annotations
import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, Optional

from ui.animations import Animator, spring_ease, ease_out_quad, ease_in_out_cubic, lerp_color

# ── 设计 Token ─────────────────────────────────────────────────────
BG_PRIMARY    = "#1C1C1E"   # 主背景
BG_CARD       = "#2C2C2E"   # 卡片背景
BG_CARD_HOVER = "#3A3A3C"   # 卡片 hover
ACCENT        = "#0A84FF"   # 蓝色强调
SUCCESS       = "#30D158"   # 绿色
WARNING       = "#FF9F0A"   # 橙色
DANGER        = "#FF453A"   # 红色
TEXT_PRIMARY  = "#FFFFFF"
TEXT_SECONDARY= "#8E8E93"
TEXT_TERTIARY = "#636366"
SEPARATOR     = "#38383A"
RADIUS        = 16           # 圆角半径
CARD_PAD      = 20           # 卡片内边距


# ── 圆角矩形 Canvas Helper ─────────────────────────────────────────

def _rounded_rect(canvas: tk.Canvas, x1, y1, x2, y2, r: int, **kw):
    """在 Canvas 上绘制圆角矩形"""
    pts = [
        x1+r, y1,  x2-r, y1,
        x2, y1,    x2, y1+r,
        x2, y2-r,  x2, y2,
        x2-r, y2,  x1+r, y2,
        x1, y2,    x1, y2-r,
        x1, y1+r,  x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


# ── ToggleSwitch ───────────────────────────────────────────────────

class ToggleSwitch(tk.Canvas):
    """iOS 风格圆形开关，带 Spring 滑动动画"""

    WIDTH = 51
    HEIGHT = 31
    KNOB_D = 25

    def __init__(self, master, initial: bool = False,
                 on_toggle: Optional[Callable[[bool], None]] = None,
                 **kw):
        super().__init__(master, width=self.WIDTH, height=self.HEIGHT,
                         bg=BG_PRIMARY, highlightthickness=0, **kw)
        self._state = initial
        self._on_toggle = on_toggle
        self._anim = Animator(self)
        self._knob_x = self._target_x(initial)
        self._draw()
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self._set_cursor("hand2"))
        self.bind("<Leave>", lambda e: self._set_cursor(""))

    def _set_cursor(self, c: str):
        self.configure(cursor=c)

    def _target_x(self, state: bool) -> float:
        margin = (self.HEIGHT - self.KNOB_D) / 2
        if state:
            return self.WIDTH - margin - self.KNOB_D
        return margin

    def _draw(self):
        self.delete("all")
        track_color = SUCCESS if self._state else "#39393D"
        # 轨道
        _rounded_rect(self, 0, 0, self.WIDTH, self.HEIGHT, self.HEIGHT // 2,
                      fill=track_color, outline="")
        # 旋钮阴影（tkinter 不支持 alpha，使用深灰近似投影效果）
        sx = self._knob_x
        sy = (self.HEIGHT - self.KNOB_D) / 2
        self.create_oval(sx+1, sy+2, sx+self.KNOB_D+1, sy+self.KNOB_D+2,
                         fill="#1a1a1a", outline="")
        # 旋钮
        self.create_oval(sx, sy, sx+self.KNOB_D, sy+self.KNOB_D,
                         fill="white", outline="")

    def _click(self, _event=None):
        self._state = not self._state
        from_x = self._knob_x
        to_x = self._target_x(self._state)

        self._anim.animate(
            duration=280,
            easing=spring_ease,
            start_value=from_x,
            end_value=to_x,
            on_update=self._update_knob,
        )
        if self._on_toggle:
            self._on_toggle(self._state)

    def _update_knob(self, x: float):
        self._knob_x = x
        self._draw()

    def set_state(self, state: bool, animate: bool = True):
        if self._state == state:
            return
        self._state = state
        from_x = self._knob_x
        to_x = self._target_x(state)
        if animate:
            self._anim.animate(
                duration=280, easing=spring_ease,
                start_value=from_x, end_value=to_x,
                on_update=self._update_knob,
            )
        else:
            self._knob_x = to_x
            self._draw()

    @property
    def state(self) -> bool:
        return self._state


# ── StatusDot ─────────────────────────────────────────────────────

class StatusDot(tk.Canvas):
    """带脉冲动画的状态点"""

    SIZE = 12

    def __init__(self, master, color: str = SUCCESS, pulse: bool = True, **kw):
        super().__init__(master, width=self.SIZE + 4, height=self.SIZE + 4,
                         bg=BG_CARD, highlightthickness=0, **kw)
        self._color = color
        self._pulse = pulse
        self._pulse_r = 0.0
        self._draw()
        if pulse:
            self._start_pulse()

    def _draw(self):
        self.delete("all")
        cx, cy = (self.SIZE + 4) / 2, (self.SIZE + 4) / 2
        r = self.SIZE / 2
        # 脉冲圆环（tkinter 不支持 alpha，用逐渐变细的线宽模拟衰减）
        if self._pulse_r > 0:
            pr = r + self._pulse_r * r
            line_w = max(1, int((1 - self._pulse_r) * 3))
            self.create_oval(cx - pr, cy - pr, cx + pr, cy + pr,
                             fill="", outline=self._color,
                             width=line_w)
        # 核心点
        self.create_oval(cx - r, cy - r, cx + r, cy + r,
                         fill=self._color, outline="")

    def _start_pulse(self):
        anim = Animator(self)
        def do_pulse():
            anim.animate(
                duration=1800,
                easing=ease_out_quad,
                start_value=0.0,
                end_value=1.0,
                on_update=self._on_pulse,
                on_done=lambda: self.after(800, do_pulse),
            )
        do_pulse()

    def _on_pulse(self, v: float):
        self._pulse_r = v
        self._draw()

    def set_color(self, color: str):
        self._color = color
        self._draw()


# ── StatusCard ────────────────────────────────────────────────────

class StatusCard(tk.Frame):
    """
    Apple 风格状态卡片，含：标题、副标题、状态点、右侧操作按钮。
    支持 hover 高亮动画。
    """

    def __init__(self, master,
                 title: str,
                 subtitle: str = "",
                 status: str = "offline",   # "online" | "warning" | "offline"
                 action_text: Optional[str] = None,
                 on_action: Optional[Callable] = None,
                 expandable: bool = False,
                 **kw):
        super().__init__(master, bg=BG_CARD, **kw)
        self._title = title
        self._subtitle = subtitle
        self._status = status
        self._action_text = action_text
        self._on_action = on_action
        self._hover = False
        self._anim = Animator(self)

        self._status_colors = {
            "online":  SUCCESS,
            "warning": WARNING,
            "offline": TEXT_TERTIARY,
        }

        self._build()
        self._apply_rounded()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _build(self):
        pad = CARD_PAD
        inner = tk.Frame(self, bg=BG_CARD)
        inner.pack(fill=tk.X, padx=pad, pady=pad)

        # 左侧：状态点 + 文字
        left = tk.Frame(inner, bg=BG_CARD)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        color = self._status_colors.get(self._status, TEXT_TERTIARY)
        pulse = self._status == "online"
        self._dot = StatusDot(left, color=color, pulse=pulse)
        self._dot.pack(side=tk.LEFT, padx=(0, 8), pady=2)

        text_col = tk.Frame(left, bg=BG_CARD)
        text_col.pack(side=tk.LEFT)

        self._title_lbl = tk.Label(
            text_col, text=self._title,
            font=("SF Pro Display", 15, "bold"),
            fg=TEXT_PRIMARY, bg=BG_CARD,
            anchor="w",
        )
        self._title_lbl.pack(anchor="w")

        if self._subtitle:
            self._sub_lbl = tk.Label(
                text_col, text=self._subtitle,
                font=("SF Pro Text", 12),
                fg=TEXT_SECONDARY, bg=BG_CARD,
                anchor="w",
            )
            self._sub_lbl.pack(anchor="w")
        else:
            self._sub_lbl = None

        # 右侧：操作按钮
        if self._action_text and self._on_action:
            self._btn = AppleButton(
                inner,
                text=self._action_text,
                on_click=self._on_action,
                style="secondary",
            )
            self._btn.pack(side=tk.RIGHT)

    def _apply_rounded(self):
        """通过配置 bg 实现视觉圆角（Canvas 方案太复杂，这里用 Frame + padding 代替）"""
        self.configure(relief="flat", bd=0)

    def _on_enter(self, _=None):
        self._hover = True
        self._set_bg_recursive(self, BG_CARD_HOVER)

    def _on_leave(self, _=None):
        self._hover = False
        self._set_bg_recursive(self, BG_CARD)

    def _set_bg_recursive(self, widget, color: str):
        try:
            widget.configure(bg=color)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._set_bg_recursive(child, color)

    def update_status(self, status: str, subtitle: str = ""):
        """更新状态和副标题"""
        self._status = status
        color = self._status_colors.get(status, TEXT_TERTIARY)
        self._dot.set_color(color)
        if subtitle and self._sub_lbl:
            self._sub_lbl.configure(text=subtitle)
        elif subtitle and not self._sub_lbl:
            self._sub_lbl = tk.Label(
                self._title_lbl.master, text=subtitle,
                font=("SF Pro Text", 12),
                fg=TEXT_SECONDARY, bg=BG_CARD,
            )
            self._sub_lbl.pack(anchor="w")


# ── AppleButton ───────────────────────────────────────────────────

class AppleButton(tk.Canvas):
    """iOS 风格圆角按钮，带按压缩放动画"""

    def __init__(self, master,
                 text: str,
                 on_click: Optional[Callable] = None,
                 style: str = "primary",  # "primary" | "secondary" | "danger"
                 width: int = 0,
                 height: int = 34,
                 **kw):
        self._text = text
        self._style = style
        self._on_click = on_click
        self._pressed = False

        # 计算宽度（避免在 tk 未完全就绪时调用 tkfont.Font）
        try:
            f = tkfont.Font(family="SF Pro Text", size=13, weight="bold")
            text_w = f.measure(text)
        except Exception:
            text_w = len(text) * 12  # fallback: 约 12px/字符
        w = max(width or text_w + 32, 80)

        super().__init__(master, width=w, height=height,
                         bg=BG_CARD, highlightthickness=0)

        self._btn_w, self._btn_h = w, height
        self._scale = 1.0
        self._anim = Animator(self)
        self._draw()

        self.bind("<Button-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Enter>", lambda e: self.configure(cursor="hand2"))
        self.bind("<Leave>", lambda e: self.configure(cursor=""))

    def _colors(self):
        if self._style == "primary":
            return ACCENT, TEXT_PRIMARY
        elif self._style == "danger":
            return DANGER, TEXT_PRIMARY
        else:
            return "#3A3A3C", TEXT_PRIMARY

    def _draw(self, scale: float = 1.0):
        self.delete("all")
        bg, fg = self._colors()
        s = scale
        cx, cy = self._btn_w / 2, self._btn_h / 2
        w = self._btn_w * s
        h = self._btn_h * s
        x1, y1 = cx - w/2, cy - h/2
        x2, y2 = cx + w/2, cy + h/2
        r = min(int(h / 2), 16)
        _rounded_rect(self, x1, y1, x2, y2, r, fill=bg, outline="")
        self.create_text(cx, cy, text=self._text,
                         font=("SF Pro Text", 13, "bold"),
                         fill=fg)

    def _press(self, _=None):
        self._pressed = True
        self._anim.animate(
            duration=120,
            easing=ease_out_quad,
            start_value=1.0,
            end_value=0.93,
            on_update=self._draw,
        )

    def _release(self, _=None):
        if self._pressed:
            self._pressed = False
            self._anim.animate(
                duration=200,
                easing=spring_ease,
                start_value=0.93,
                end_value=1.0,
                on_update=self._draw,
                on_done=self._fire,
            )

    def _fire(self):
        if self._on_click:
            self._on_click()


# ── LogPanel ──────────────────────────────────────────────────────

class LogPanel(tk.Frame):
    """滚动日志面板，Apple 深色风格"""

    def __init__(self, master, max_lines: int = 200, **kw):
        super().__init__(master, bg=BG_PRIMARY, **kw)
        self._max = max_lines

        self._text = tk.Text(
            self,
            bg="#111113",
            fg=TEXT_SECONDARY,
            font=("SF Mono", 11) if _font_exists("SF Mono") else ("Consolas", 11),
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
            wrap=tk.WORD,
            state=tk.DISABLED,
            selectbackground=ACCENT,
        )
        scroll = tk.Scrollbar(self, command=self._text.yview,
                              bg=BG_PRIMARY, troughcolor=BG_PRIMARY,
                              width=6)
        self._text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 颜色标签
        self._text.tag_configure("success", foreground=SUCCESS)
        self._text.tag_configure("warning", foreground=WARNING)
        self._text.tag_configure("error",   foreground=DANGER)
        self._text.tag_configure("info",    foreground=TEXT_SECONDARY)
        self._text.tag_configure("accent",  foreground=ACCENT)

    def append(self, msg: str, level: str = "info"):
        """level: success | warning | error | info | accent"""
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self._text.configure(state=tk.NORMAL)
        self._text.insert(tk.END, line, level)
        lines = int(self._text.index(tk.END).split(".")[0])
        if lines > self._max:
            self._text.delete("1.0", f"{lines - self._max}.0")
        self._text.see(tk.END)
        self._text.configure(state=tk.DISABLED)

    def clear(self):
        self._text.configure(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.configure(state=tk.DISABLED)


# ── WindowControlButton ───────────────────────────────────────────

class WindowControlButton(tk.Canvas):
    """
    Windows/macOS 双兼容右上角控制按钮（关闭/最小化）
    悬停高亮，关闭按钮悬停变为鲜艳警示红 #E81123，极度清晰醒目
    """
    def __init__(self, master, btn_type: str = "close", on_click: Optional[Callable] = None, width: int = 46, height: int = 44, **kw):
        super().__init__(master, width=width, height=height, bg=BG_PRIMARY, highlightthickness=0, **kw)
        self._type = btn_type  # 'close' | 'minimize'
        self._on_click = on_click
        self._ctrl_w = width
        self._ctrl_h = height
        self._hover = False
        self._draw()

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)

    def _draw(self):
        self.delete("all")
        bg_col = BG_PRIMARY
        icon_col = TEXT_SECONDARY
        if self._hover:
            if self._type == "close":
                bg_col = "#E81123"
                icon_col = "#FFFFFF"
            else:
                bg_col = "#3A3A3C"
                icon_col = "#FFFFFF"

        self.create_rectangle(0, 0, self._ctrl_w, self._ctrl_h, fill=bg_col, outline="")
        cx, cy = self._ctrl_w / 2, self._ctrl_h / 2

        if self._type == "close":
            # 绘制 ✕
            s = 5.5
            self.create_line(cx - s, cy - s, cx + s, cy + s, fill=icon_col, width=1.5, capstyle=tk.ROUND)
            self.create_line(cx + s, cy - s, cx - s, cy + s, fill=icon_col, width=1.5, capstyle=tk.ROUND)
        elif self._type == "minimize":
            # 绘制 —
            s = 6
            self.create_line(cx - s, cy, cx + s, cy, fill=icon_col, width=1.5, capstyle=tk.ROUND)

    def _on_enter(self, _e):
        self._hover = True
        self._draw()

    def _on_leave(self, _e):
        self._hover = False
        self._draw()

    def _on_press(self, _e):
        if self._on_click:
            self._on_click()


# ── UpdateBadge ───────────────────────────────────────────────────

class UpdateBadge(tk.Frame):
    """版本状态胶囊徽章（最新✓ / 有更新↑ / 检查中…）"""

    def __init__(self, master, **kw):
        super().__init__(master, bg=BG_CARD, **kw)
        self._lbl = tk.Label(
            self, text="…", font=("SF Pro Text", 12, "bold") if _font_exists("SF Pro Text") else ("Segoe UI", 12, "bold"),
            fg=TEXT_SECONDARY, bg="#242426", padx=10, pady=3,
        )
        self._lbl.pack(anchor="w")

    def set_ok(self, local_ver: str = ""):
        self._lbl.configure(
            text=f"✓  {local_ver} (最新)" if local_ver else "✓ 已是最新",
            fg=SUCCESS, bg="#1E3324",
        )

    def set_update_available(self, remote_ver: str = ""):
        self._lbl.configure(
            text=f"↑  {remote_ver} 可更新" if remote_ver else "↑ 有更新",
            fg=WARNING, bg="#3D2D14",
        )

    def set_checking(self):
        self._lbl.configure(text="检查中…", fg=TEXT_SECONDARY, bg="#242426")

    def set_error(self, msg: str = ""):
        self._lbl.configure(
            text=f"✗  {msg}" if msg else "✗ 检查失败",
            fg=DANGER, bg="#381D1D",
        )


# ── SectionLabel ─────────────────────────────────────────────────

class SectionLabel(tk.Label):
    """分节标题（精美大字号，带呼吸感间距）"""

    def __init__(self, master, text: str, **kw):
        super().__init__(
            master,
            text=text.upper(),
            font=("SF Pro Display", 12, "bold") if _font_exists("SF Pro Display") else ("Segoe UI", 12, "bold"),
            fg=TEXT_SECONDARY,
            bg=BG_PRIMARY,
            anchor="w",
            **kw,
        )


# ── Divider ───────────────────────────────────────────────────────

class Divider(tk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, bg=SEPARATOR, height=1, **kw)


# ── ProgressBar ───────────────────────────────────────────────────

class ProgressBar(tk.Canvas):
    """带动画的下载进度条"""

    def __init__(self, master, width: int = 300, height: int = 4, **kw):
        super().__init__(master, width=width, height=height,
                         bg=BG_CARD, highlightthickness=0, **kw)
        self._bar_w = width
        self._bar_h = height
        self._progress = 0.0
        self._draw()

    def _draw(self):
        self.delete("all")
        # 轨道
        _rounded_rect(self, 0, 0, self._bar_w, self._bar_h, 2,
                      fill=SEPARATOR, outline="")
        # 填充
        w = int(self._bar_w * self._progress)
        if w > 2:
            _rounded_rect(self, 0, 0, w, self._bar_h, 2,
                          fill=ACCENT, outline="")

    def set_progress(self, value: float):
        """value: 0.0 ~ 1.0"""
        self._progress = max(0.0, min(1.0, value))
        self._draw()


# ── Helper ────────────────────────────────────────────────────────

def _font_exists(name: str) -> bool:
    return name in tkfont.families()
