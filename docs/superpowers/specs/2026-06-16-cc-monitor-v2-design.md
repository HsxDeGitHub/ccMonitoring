# CC Monitor V2 优化设计

## 背景

V1 使用 tkinter 实现，UI 粗糙，交互体验差（卡顿、拖拽不流畅、收缩标签体验不好）。用户需要全面优化：UI 美化、交互优化、流畅度提升、新功能（菜单栏图标、快捷键、开机自启）。

## 核心变更

- **UI 框架**：tkinter → PyQt6，获得原生 macOS 体验
- **进程扫描和状态引擎**：不变
- **新增**：菜单栏图标、键盘快捷键、位置记忆、开机自启

---

## 架构

```
ccMonitoring/
├── monitor.py            # 主入口（更新）
├── process_scanner.py    # 进程扫描（不变）
├── state_engine.py       # 状态引擎（不变）
├── overlay_window.py     # 悬浮窗口 → PyQt6 重写
├── tray_icon.py          # 新增：菜单栏图标
├── settings.py           # 新增：QSettings 配置持久化
└── requirements.txt      # 更新：psutil + PyQt6
```

## 展开窗口

- PyQt6 `QWidget` + `FramelessWindowHint | WindowStaysOnTopHint`
- CSS 样式表控制配色、字体、间距
- 自定义 macOS 风格标题栏（红/黄圆点按钮）
- QScrollArea 展示实例列表，每行：状态圆点 + 目录名 + 状态标签
- `setToolTip()` 显示完整路径和 PID
- `WA_ShowWithoutActivating` 不抢焦点

## 收缩标签

点击 `−` → 窗口隐藏，屏幕侧边显示 28×56 竖条（状态圆点 + 展开箭头）。点击任意位置展开回原位。

## 菜单栏图标

- `QSystemTrayIcon` 实现
- 图标：状态色圆点 + "CC" 文字
- 下拉菜单：实例列表（每项显示状态色+目录名）+ 分割线 + "显示窗口"/"退出"

## 键盘快捷键

| 快捷键 | 操作 |
|--------|------|
| ESC | 收缩/展开 |
| Cmd+Q | 退出 |

窗口聚焦时生效。

## 开机自启

- macOS LaunchAgent 方式：`~/Library/LaunchAgents/com.ccmonitor.plist`
- 首次运行提示确认
- `--no-autostart` 参数关闭

## 配置持久化

- `QSettings` 存储窗口位置、上次展开/收缩状态
- 启动时恢复上次状态

## 依赖

```
psutil>=5.9.0
PyQt6>=6.5.0
```
