<div align="center">

<img src="assets/icon.png" width="128" height="128" alt="AntigravityHub Logo" />

# AntigravityHub (反重力补丁注入与汉化中心)

**专为 Google Antigravity IDE 打造的现代化、开箱即用桌面级一键补丁注入与中文汉化管理工具**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](#)
[![UI: CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter%20Fluent-107C41.svg)](#)

</div>

---

## 🌟 核心特性与功能

### 1. ⚡ 内置离线补丁一键全自动热注入
* **完全离线保底**：软件内部直接集成了经过验证的 `version.dll` 核心补丁与完整 `app.asar` 简体中文汉化包，无需联网即可随时一键注入！
* **热注入与安全检测**：智能检测 Antigravity IDE 运行状态与文件占用，安全注入补丁并自动对齐可用代理端口。
* **一键原版还原**：支持随时彻底卸载代理劫持与汉化包，100% 无损还原官方纯净原生英文状态。

### 2. 🌐 独立改中文（汉化包注入）
* 提供独立的「改中文」按钮，一键将官方纯英文界面替换为完整汉化包。
* 自动备份官方原版 `app.asar.bak`，安全无风险。

### 3. 🛡️ 智能状态检测与决策横幅 (Fluent InfoBar)
* **开机自检与智能提示**：软件启动后自动探测反重力 IDE 的安装路径、版本号、补丁完整性与语言状态。
* **决策横幅**：若检测到处于官方原生或补丁缺失状态，顶部智能横幅将主动提示是否一键注入，免去繁琐的人工排查。

### 4. 🎨 现代极简设计 (Windows 11 Fluent / Mica 质感)
* **全新 3D 悬浮水晶图标**：精心设计的反重力量子悬浮环与高光上升晶体 Logo。
* **矢量高 DPI 适配**：基于 CustomTkinter 构建，文字自适应排版，任意屏幕缩放下绝对不截断。
* **抽屉式极简日志**：平时收起保持主界面极简通透，需要时一键展开查看实时运行日志。

---

## 🖥️ 快速开始

### 方式 A：直接运行打包好的单 EXE（推荐）
在项目 [Releases](../../releases) 页面下载单文件免安装版 `AntigravityHub.exe`，双击即可直接运行！

### 方式 B：源码运行与开发环境
```bash
# 1. 克隆仓库
git clone https://github.com/POKMJN/AntigravityHub.git
cd AntigravityHub

# 2. 安装依赖
pip install customtkinter pillow psutil pyyaml requests pywin32 pytest

# 3. 运行管理中心
python main.py
```

### 单文件构建打包 (PyInstaller)
```bash
pyinstaller AntigravityHub.spec --noconfirm
```
打包生成的可执行文件位于 `dist/AntigravityHub.exe`。

---

## 📄 开源许可证
本项目遵循 [MIT License](LICENSE) 开源协议。
