<div align="center">

<img src="assets/icon.png" width="128" height="128" alt="AntigravityHub Logo" />

# AntigravityHub (反重力综合管理中心)

**专为 Google Antigravity IDE 打造的现代化、开箱即用桌面级一键综合管理工具**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](#)
[![UI: CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter%20Fluent-107C41.svg)](#)

</div>

---

## 🌟 核心特性与功能

### 1. ⚡ 内置离线补丁一键全自动热注入
* **完全离线保底**：软件内部直接集成了经过验证的 `version.dll` 代理劫持补丁与完整 `app.asar` 简体中文汉化包，无需联网即可随时一键注入！
* **热注入与安全检测**：智能检测 Antigravity IDE 运行状态与文件占用，安全写入并智能对齐 `config.json` 专线端口 `7895`。
* **一键原版还原**：支持随时彻底卸载代理劫持与汉化包，100% 无损还原官方纯净原生状态。

### 2. 🛡️ 智能状态检测与决策横幅 (Fluent InfoBar)
* **开机自检与智能提示**：软件启动后自动探测反重力 IDE 的安装路径、版本号、补丁完整性与专线连通性。
* **决策横幅**：若检测到处于官方原生或补丁缺失状态，顶部智能横幅将主动提示是否一键注入，免去繁琐的人工排查。

### 3. 🚀 内置定向代理专线直连 (Mihomo 内核)
* **独立 7895 专线**：内置 Mihomo 独立核心服务，为反重力 IDE 建立独享通道。
* **多节点故障转移 (Failover)**：首选韩国专线高速节点，异常时秒级平滑切换至备用原生节点。
* **实时测速与节点切换**：支持界面一键发起延迟探测与节点快速轮换。

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
pyinstaller --noconfirm AntigravityHub.spec
```
编译产物将生成在 `dist/AntigravityHub.exe`。

---

## 📂 项目架构

```
AntigravityHub/
├── assets/                  # 高清图标资源 (icon.ico, icon.png)
├── builtin_assets/          # 内置离线补丁基线库 (version.dll, app.asar)
├── config/                  # 软件基础配置文件
├── core/                    # 核心业务逻辑
│   ├── antigravity_manager.py
│   ├── injector.py          # 离线热注入与还原核心
│   ├── mihomo_service.py    # 专线服务管理与控制
│   └── updater.py           # 云端更新检查
├── ui/                      # 现代化 CustomTkinter 界面
│   ├── win_app_window.py    # 主管理中心窗口
│   └── win_components.py    # 状态胶囊、主题色彩与组件
├── tests/                   # 自动化单元测试套件
├── AntigravityHub.spec      # PyInstaller 打包构建规范
└── main.py                  # 应用程序启动入口
```

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。仅供学习交流与个人开发效率提升使用。
