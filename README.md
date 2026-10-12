# UnityModForge —— 一句话生成 Unity 游戏 Mod（本地桌面工具）v1.0.0

> v1.0.0 整合版：合并「工具构建」与「Windows exe 打包交付」两个阶段的全部内容，
> 新增 Linux / macOS 一键打包脚本，并整理统一的打包与交付说明。

模仿抖音「阿铭」的"一句话生成游戏 Mod"软件做的本地版：选择 Unity 单机游戏 → 用中文说一句你想改什么 → AI 自动生成 BepInEx 插件代码并编译成可安装的 Mod。

```
用户一句话 ──▶ 扫描游戏结构 ──▶ AI 生成 C# 插件代码 ──▶ dotnet 编译 ──▶ 一键安装进游戏
（F9 打开商店面板…）   (Mono)         (BepInEx 5 + Harmony)     (Release)    (BepInEx/plugins/<Mod名>/)
```

## 功能一览

| 能力 | 说明 |
|---|---|
| 一句话生成 Mod | 中文描述需求，AI 现场生成 BepInEx 5 插件代码并自动编译 |
| 游戏结构扫描 | 识别 Mono / IL2CPP 版 Unity 游戏，定位主程序集并生成 API 索引供 AI 参考 |
| 一键安装 | 编译成功后自动装入游戏 `BepInEx/plugins/<Mod名>/`；没有 BepInEx 时自动安装 |
| 免费模型预设 | 内置 5 个免费方案（本地 Ollama 免注册免 Key）+ 常用付费模型，开箱即用 |
| GUI + CLI | 卡片式桌面界面；无界面服务器场景可用命令行模式 |
| 一键打包 | Windows `build_windows.bat` / Linux·macOS `build_unix.sh`，绿色可执行文件 |

## 快速开始

### 1. 准备环境（一次性）

- Python 3.9+，安装依赖：`pip install -r requirements.txt`
- .NET SDK 8：https://dotnet.microsoft.com/ （编译 Mod 必需，装完确保 `dotnet` 在 PATH）
- 选一个 **免费 AI 模型**（见下节，工具已内置免费预设）
- 可选：`dotnet tool install -g ilspycmd`（扫描游戏 API 更准确，装了会大幅提高生成成功率）

### 2. 免费模型怎么选（已内置预设，不用自己配地址）

| 方案 | 花费 | 要注册吗 | 说明 |
|---|---|---|---|
| **本地 Ollama（推荐）** | 0 | 不用 | 装 Ollama 后完全离线、无限量；`ollama pull qwen2.5-coder:7b` 首次下载约 5GB。设置页点「检测并填入模型」一键接入 |
| 智谱 GLM-4.7-Flash | 0 | 要（免费） | bigmodel.cn 注册送 Key；官方免费模型，输入输出缓存都不收费 |
| 硅基流动 Qwen2.5-7B | 0 | 要（免费） | siliconflow.cn 注册送 Key；Qwen2.5-7B-Instruct 免费 |
| OpenRouter `:free` | 0 | 要（免费） | openrouter.ai 注册送 Key；每日约 50 次免费调用，模型名带 `:free` 后缀 |
| Groq Llama3.3-70B | 0 | 要（免费） | groq.com 注册送 Key；有速率限制 |

在「设置」页预设下拉里选一个即可，地址和模型名自动填好；本地 Ollama 连 Key 都不用填。

### 3. 启动

```bash
python3 app.py
```

### 4. 使用流程

1. **设置页**：选免费模型预设 → 填 Key（本地 Ollama 跳过）→ 选 BepInEx 平台（Windows 游戏选 x64）→ 保存。
2. **生成页**：选择游戏根目录（包含 `游戏名_Data` 文件夹的目录）→ 点「扫描游戏」。
3. 用一句话描述想改什么，点「生成并编译 Mod」。
4. 默认**自动安装**：编译成功后 Mod 会被直接复制进游戏 `BepInEx/plugins/<Mod名>/`；
   游戏目录里还没有 BepInEx 时会自动装好 BepInEx（首次需先运行一次游戏再退出）。
   不想自动安装就取消勾选「编译成功后自动安装到游戏」。
5. 启动游戏，控制台/日志出现你的 Mod 名字即安装成功。

### 查看文件位置

- 「打开游戏目录」：跳到游戏根目录（Mod 最终装在它的 `BepInEx/plugins/` 下）
- 「打开输出目录」：跳到所有生成工程的存放目录（设置页可改）
- 「打开工程目录」：生成后点亮，直接跳到本次 Mod 的工程源码目录
- 扫描结果里显示数据目录/主程序集路径；日志里显示 DLL、安装、工程完整路径，均可选中复制

### 命令行模式（无图形界面 / 服务器）

```bash
# 用云端免费模型
python3 app.py --cli \
  --game "/path/to/Game" \
  --request "给游戏加一个按 F9 切换无敌的按键" \
  --api-key "sk-xxx" --base-url "https://open.bigmodel.cn/api/paas/v4" --model "glm-4.7-flash" \
  --install

# 用本地 Ollama（完全免费，无需 Key）
python3 app.py --cli \
  --game "/path/to/Game" --request "给游戏加一个商店面板" \
  --base-url "http://127.0.0.1:11434/v1" --model "qwen2.5-coder:7b" \
  --install
```

## 打包成可执行文件（Windows EXE / Linux / macOS）

**硬约束先说清楚**：PyInstaller 不支持跨平台交叉编译——exe 必须在 Windows 上生成，
Linux 版在 Linux 上生成，macOS 版在 macOS 上生成。
任何号称「远程直接给你 exe」的都是骗人的。所以工具做成了「一键」：你在目标系统上双击/运行一下脚本即可。

### Windows：三步拿到 exe

1. 在 Windows 上安装 Python 3.9+：https://www.python.org/downloads/（**勾选 "Add Python to PATH"**）
2. 把本目录整个复制到 Windows 电脑，双击 **`build_windows.bat`**
3. 等约 1-3 分钟，得到 **`dist\UnityModForge.exe`** —— 绿色单文件，双击即用，复制给任何人都能跑

> 首次运行时 Windows 可能提示"未知发布者"，点「更多信息 → 仍要运行」（未签名程序正常现象）。
> 生成 exe 的电脑需要装 .NET SDK 8（编译 Mod 必需）；但 exe 拷到别的电脑用时，
> 那台电脑不需要 Python 和 .NET SDK——只有需要编译新 Mod 时才要 dotnet，
> 看游戏 / 装 Ollama 都是纯操作。

### 可选：做成正规安装包（开始菜单 + 桌面快捷方式 + 卸载）

1. 按上面步骤先得到 `dist\UnityModForge.exe`
2. 安装 Inno Setup 6：https://jrsoftware.org/isinfo.php
3. 双击 `UnityModForge_installer.iss` → 编译，得到 `installer\UnityModForge_Setup.exe`

### Linux / macOS：一条命令打包

```bash
bash build_unix.sh
```

脚本会：检查 python3 → 安装依赖 + PyInstaller → 校验源码 → 打包，
产物在当前系统的 `dist/UnityModForge`（Linux 下是 ELF 可执行文件，macOS 下是 Mach-O 应用）。
Linux/macOS 版不内嵌图标（.ico 是 Windows 专用格式），打包配置已自动跳过。

### 打包相关文件

```
├── build_windows.bat           # Windows 一键打包脚本（装依赖 + 校验 + 打包）
├── build_unix.sh               # Linux / macOS 一键打包脚本（v1.0.0 新增）
├── UnityModForge.spec          # PyInstaller 配置（单文件、无控制台窗口、Windows 带图标）
├── UnityModForge_installer.iss # Inno Setup 安装包脚本（可选，仅 Windows）
└── assets/icon.ico             # 应用图标（深蓝底 + 白色闪电，16~256px 全尺寸）
```

### 打包常见问题

| 问题 | 处理 |
|---|---|
| 打包时红色报错 | 把窗口/终端里的红色报错复制出来发回，按提示修改 |
| 提示找不到 Python | 未勾选 "Add Python to PATH"，装完重开窗口再运行 |
| 运行 exe 提示"未知发布者" | 未签名程序正常现象：更多信息 → 仍要运行 |
| 想生成 Linux/macOS 版 | 在对应系统上运行 `build_unix.sh`（不能跨系统交叉编译） |

## 项目结构

```
UnityModForge/
├── app.py                    # 桌面 GUI（卡片式分步 UI）+ CLI 入口
├── build_windows.bat         # Windows 一键打包 EXE
├── build_unix.sh             # Linux / macOS 一键打包（v1.0.0 新增）
├── UnityModForge.spec        # PyInstaller 打包配置
├── UnityModForge_installer.iss  # Inno Setup 安装包脚本（可选）
├── assets/icon.ico           # 应用图标
├── unitymodforge/
│   ├── game_scanner.py       # Unity 游戏检测（Mono/IL2CPP）+ API 索引
│   ├── prompts.py            # AI 提示词模板
│   ├── llm_client.py         # OpenAI 兼容 API 客户端（含 Ollama 检测）
│   ├── mod_builder.py        # BepInEx 获取、工程脚手架、dotnet 编译、一键安装
│   └── config.py             # 设置持久化 + 免费模型预设
├── examples/SampleBepInExPlugin/   # 可直接编译的最小示例插件（含 BepInEx.dll）
├── examples/UnityEngineStub/       # 编译桩独立工程（一般不需要动）
└── tests/                    # 自动化测试（含端到端）
```

## 工作原理

| 环节 | 说明 |
|---|---|
| 游戏扫描 | 找 `xxx_Data/Managed/Assembly-CSharp.dll`（Mono）；用 ilspycmd/monodis 生成类型索引供 AI 参考 |
| AI 生成 | 提示词限定：BepInEx 5 API、net461、判空/try-catch、优先使用扫描到的真实类型名、中文注释；输出 Plugin.cs + csproj |
| 编译 | `dotnet build -c Release`，自动带上 BepInEx.dll（从游戏自带 / 本地 zip / 自动下载）与 UnityEngine.dll（游戏自带，缺失时自动生成编译桩） |
| 一键安装 | 复制 DLL 到游戏 `BepInEx/plugins/<Mod名>/`；游戏没有 BepInEx 时自动解压安装包装好 |

## UI 说明

- 顶栏 + 三步卡片式布局（①选择游戏 → ②一句话需求 → ③生成并安装），浅色现代配色。
- 运行日志按结果着色：✅ 绿色成功 / ❌ 红色错误 / ⚠ 橙色提示。
- 「打开游戏目录 / 输出目录 / 工程目录」三个按钮直接跳转到对应文件位置。
- 设置页内置 5 个免费模型预设 + 「检测本地 Ollama」一键接入，生成按钮在任务进行中自动禁用防重复点击。
- 设置与生成分两个标签页，设置即时保存到 `~/.unitymodforge/config.json`。

## 已知限制（重要）

1. **当前版本只支持 Mono（.NET）版 Unity 单机游戏**：这类游戏的 `Managed/` 里有 `Assembly-CSharp.dll` 可以直接挂钩。IL2CPP 版（`il2cpp_data` 目录）需要 BepInEx 6 + Il2CppInterop 另一条管线，本工具检测到会明确提示，暂不支持一键生成。
2. **模型需要自己准备**：工具本身不含模型。免费方案：本地 Ollama（无需注册/Key）或智谱 GLM-4.7-Flash 等免费 API（免费注册拿 Key，模型调用不收费）。
3. **代码可能编译失败**：游戏内部 API 千差万别，AI 生成的代码第一次不一定能编译通过。失败时把日志里的编译错误复制给 AI（或直接发给我）迭代修改即可；装了 ilspycmd 重扫后成功率明显更高。
4. **反作弊/加密游戏**：带反作弊、DRM 的游戏（多数网游、部分单机）无法注入，建议只对纯单机游戏使用。
5. **BepInEx 依赖下载**：自动下载走 GitHub，网络不通时手动下载安装包填到设置里：https://github.com/BepInEx/BepInEx/releases （5.4.22，选对应平台 zip）。

## 示例

`examples/SampleBepInExPlugin/` 是一个**已经验证可编译**的最小插件（`lib/` 里已带 BepInEx.dll 和 UnityEngine 编译桩）：

```bash
cd examples/SampleBepInExPlugin
dotnet build -c Release
# 产物：bin/Release/SampleGameMod.dll → 放进游戏 BepInEx/plugins/
```

`examples/UnityEngineStub/` 是编译桩的独立工程，正常情况下不需要动它。

## 测试

```bash
python3 tests/test_scanner.py && python3 tests/test_llm.py && python3 tests/test_builder.py
# 端到端演练（需要本机 dotnet）：假游戏 + mock API → 真实编译出 Mod DLL → 一键安装进游戏
python3 tests/test_e2e_cli.py
```

## 版本记录

| 版本 | 内容 |
|---|---|
| v1.0.0（当前） | 整合构建与打包交付：统一 README；新增 `build_unix.sh`（Linux/macOS 一键打包）；Windows 三步 exe 打包（`build_windows.bat` + spec + Inno Setup 安装包脚本） |

## 开源协议

MIT License（见 [LICENSE](LICENSE)）。仓库地址：https://github.com/yyc-i/UnityModForge
