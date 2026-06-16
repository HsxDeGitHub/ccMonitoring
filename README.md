# CC Monitor

Claude Code 进程桌面监控工具 — 在 macOS 桌面上以悬浮窗口实时显示所有 Claude Code 实例的运行状态，让你在其它界面也能一眼看到任务是否还在继续执行。

## 功能特性

- **实时进程监控** — 自动扫描系统中所有正在运行的 Claude Code 进程，定时刷新状态
- **状态指示灯** — 通过颜色区分四种状态：运行中（绿）、等待确认（黄）、已完成（灰）、出错（红）
- **悬浮窗口** — 始终置顶的迷你窗口，可拖拽到屏幕任意位置，不干扰正常工作
- **折叠模式** — 将窗口折叠为屏幕边缘的小巧标签，仅显示彩色圆点，鼠标悬停展开
- **系统托盘** — 菜单栏图标，右键弹出实例列表和快捷操作
- **深浅色主题** — 一键切换深色/浅色主题，适配 macOS 外观

## 下载安装

### 方式一：下载安装包（推荐）

从 [GitHub Releases](../../releases) 下载最新的 `CC-Monitor.app`，拖入 `Applications` 文件夹即可。

首次打开时，由于应用未经过 Apple 公证，需要手动允许：

```bash
# 移除隔离属性
sudo xattr -rd com.apple.quarantine /Applications/CC-Monitor.app
```

### 方式二：源码安装

```bash
git clone https://github.com/HsxDeGitHub/ccMonitoring.git
cd ccMonitoring
pip install -r requirements.txt
python run.py
```

**依赖：**
- Python >= 3.10
- PyQt6 >= 6.5.0
- psutil >= 5.9.0

## 使用说明

### 启动

```bash
python run.py
```

启动后，屏幕右上角会出现悬浮窗口，同时菜单栏出现 CC Monitor 托盘图标。

### 窗口操作

| 操作 | 方式 |
|------|------|
| 拖拽窗口 | 按住标题栏拖动 |
| 折叠窗口 | 点击标题栏黄色按钮，或按 `Esc` |
| 展开窗口 | 点击折叠标签，或通过托盘菜单「显示窗口」 |
| 关闭程序 | 点击标题栏红色按钮，或通过托盘菜单「退出」 |
| 切换主题 | 通过托盘菜单「切换主题」 |

### 状态颜色

| 颜色 | 状态 | 含义 |
|------|------|------|
| 🟢 绿色 | 运行中 | Claude Code 正在执行任务 |
| 🟡 黄色 | 等待确认 | 任务暂停，等待用户确认操作 |
| ⚫ 灰色 | 已完成 | 任务正常结束（30 秒后自动消失） |
| 🔴 红色 | 出错 | 任务异常退出 |

等待确认状态的圆点会闪烁，提醒你及时切回终端查看。

## 开机自启（macOS）

```bash
# 安装 LaunchAgent，登录后自动启动
python scripts/install_autostart.py

# 移除自启
python scripts/install_autostart.py --uninstall
```

## 项目结构

```
ccMonitoring/
├── run.py                 # 入口脚本
├── requirements.txt       # Python 依赖
├── scripts/
│   ├── com.ccmonitor.plist       # LaunchAgent 配置模板
│   └── install_autostart.py      # 开机自启安装脚本
└── src/ccmonitor/
    ├── monitor.py          # 主控制器
    ├── process_scanner.py  # 进程扫描
    ├── state_engine.py     # 状态判定
    ├── overlay_window.py   # 悬浮窗口 UI
    ├── tray_icon.py        # 系统托盘图标
    └── settings.py         # 持久化设置
```

## License

MIT
