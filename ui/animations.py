"""
animations.py — Spring/Easing 非线性动画引擎（基于 tkinter.after）

参考 iOS UISpringTimingParameters 实现物理弹簧动画。
"""
from __future__ import annotations
import math
import time
import tkinter as tk
from typing import Callable, Optional


# ────────────────────────────────────────────────────────────────
# 缓动函数（全部接受 t ∈ [0, 1] → 返回 0~1）
# ────────────────────────────────────────────────────────────────

def ease_out_quad(t: float) -> float:
    return 1 - (1 - t) ** 2


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t ** 3
    return 1 - (-2 * t + 2) ** 3 / 2


def ease_out_expo(t: float) -> float:
    return 0 if t == 0 else 1 if t == 1 else 1 - 2 ** (-10 * t)


def ease_out_back(t: float, overshoot: float = 1.70158) -> float:
    c1 = overshoot
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def spring_ease(t: float, stiffness: float = 300, damping: float = 30) -> float:
    """
    模拟 iOS UISpringTimingParameters 的弹簧位移。
    stiffness: 弹簧刚度（越大越快）
    damping:   阻尼系数（越大越无弹跳）
    返回归一化位移 (0→1)，可能略超 1 再回弹。
    """
    # 临界阻尼比 ζ
    mass = 1.0
    omega0 = math.sqrt(stiffness / mass)
    zeta = damping / (2 * math.sqrt(stiffness * mass))

    if zeta >= 1:  # 过阻尼
        return ease_out_expo(t)

    omega_d = omega0 * math.sqrt(1 - zeta ** 2)
    # 无限持续弹簧响应，归一化到有限时间
    duration_scale = 6 / (zeta * omega0 + 1e-9)
    tau = t * duration_scale
    envelope = 1 - math.exp(-zeta * omega0 * tau)
    osc = math.cos(omega_d * tau)
    # 最终公式：1 - exp(-ζω₀τ)·(cos(ωdτ) + ζω₀/ωd·sin(ωdτ))
    sin_term = (zeta * omega0 / omega_d) * math.sin(omega_d * tau)
    return 1 - math.exp(-zeta * omega0 * tau) * (osc + sin_term)


# ────────────────────────────────────────────────────────────────
# 动画调度器
# ────────────────────────────────────────────────────────────────

class Animator:
    """
    用法：
        anim = Animator(root)
        anim.animate(
            duration=300,           # ms
            easing=spring_ease,
            on_update=lambda v: widget.configure(height=int(v * 200)),
            on_done=lambda: print("done"),
        )
    """

    def __init__(self, widget: tk.Widget):
        self.widget = widget
        self._after_id: Optional[str] = None

    def animate(
        self,
        duration: int,
        easing: Callable[[float], float],
        on_update: Callable[[float], None],
        on_done: Optional[Callable] = None,
        fps: int = 60,
        start_value: float = 0.0,
        end_value: float = 1.0,
        cancel_previous: bool = True,
    ):
        """
        在 duration(ms) 内，从 start_value 到 end_value，
        使用 easing 函数插值，每帧调用 on_update(current_value)。
        """
        if cancel_previous and self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

        interval = max(1, 1000 // fps)
        start_ms = _now_ms()
        span = end_value - start_value

        def tick():
            elapsed = _now_ms() - start_ms
            progress = min(elapsed / duration, 1.0)
            eased = easing(progress)
            current = start_value + span * eased
            try:
                on_update(current)
            except Exception:
                pass
            if progress < 1.0:
                self._after_id = self.widget.after(interval, tick)
            else:
                self._after_id = None
                if on_done:
                    try:
                        on_done()
                    except Exception:
                        pass

        tick()

    def cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None


def _now_ms() -> float:
    return time.perf_counter() * 1000


# ────────────────────────────────────────────────────────────────
# 颜色插值工具
# ────────────────────────────────────────────────────────────────

def lerp_color(c1: str, c2: str, t: float) -> str:
    """在两个十六进制颜色之间线性插值，返回 #RRGGBB"""
    def parse(c: str) -> tuple[int, int, int]:
        c = c.lstrip("#")
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

    r1, g1, b1 = parse(c1)
    r2, g2, b2 = parse(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


# ────────────────────────────────────────────────────────────────
# 便捷包装函数
# ────────────────────────────────────────────────────────────────

def fade_in(widget: tk.Widget, duration: int = 250):
    """将 widget 从 alpha=0 淡入到 1（仅顶层窗口支持 attributes('-alpha')）"""
    try:
        top = widget.winfo_toplevel()
        top.attributes("-alpha", 0.0)

        anim = Animator(widget)
        anim.animate(
            duration=duration,
            easing=ease_out_quad,
            on_update=lambda v: top.attributes("-alpha", v),
        )
    except Exception:
        pass


def slide_y(widget: tk.Widget, from_y: int, to_y: int,
            duration: int = 350,
            easing: Callable = ease_out_back,
            on_done: Optional[Callable] = None):
    """沿 Y 轴滑动 widget（使用 place 布局）"""
    anim = Animator(widget)
    anim.animate(
        duration=duration,
        easing=easing,
        start_value=float(from_y),
        end_value=float(to_y),
        on_update=lambda v: widget.place_configure(y=int(v)),
        on_done=on_done,
    )


def animate_int(widget: tk.Widget, from_v: int, to_v: int,
                duration: int, easing: Callable,
                setter: Callable[[int], None],
                on_done: Optional[Callable] = None):
    """通用整数值动画"""
    anim = Animator(widget)
    anim.animate(
        duration=duration,
        easing=easing,
        start_value=float(from_v),
        end_value=float(to_v),
        on_update=lambda v: setter(int(v)),
        on_done=on_done,
    )
