"""提示词模板：把用户一句话 + 游戏扫描信息 组织成 BepInEx 插件代码生成请求。"""
from .game_scanner import GameInfo

SYSTEM_PROMPT = """你是一名资深的 Unity 单机游戏 Mod 开发者，擅长使用 BepInEx 5 + Harmony 编写 C# 注入式 Mod。

编写要求：
1. 只输出能直接编译的代码，使用 BepInEx 5.x API：BepInPlugin、BaseUnityPlugin、ManualLogSource、Awake/Start/Update、Harmony（HarmonyLib）补丁。
2. 目标框架 net461；如果游戏信息里没有 UnityEngine 程序集可引用，禁止直接使用 UnityEngine 类型，改为只用 BepInEx/Harmony API 或反射实现，并注释说明。
3. 代码必须健壮：所有可能为 null 的引用都要判空，关键操作包 try/catch，日志统一用 Logger.LogInfo / Logger.LogError。
4. 涉及游戏内部类型/方法时，优先使用“游戏 API 索引”里给出的真实名称；索引缺失时用反射或通用 Unity API 实现，并在注释里说明。
5. 注释全部用简体中文，让不懂代码的玩家也能看懂每段在做什么。
6. 命名空间统一为 <GameName>Mod（用扫描到的游戏名），类名有意义。
7. 键盘快捷键用 BepInEx 的 ConfigEntry 配置（KeyboardShortcut），并输出到控制台提示按键。
8. 输出格式严格固定为：
   - 第一行：# 方案（一句话说明你的实现思路）
   - 然后依次给出三个代码块：
     ```csharp
     // 这里是 Plugin.cs 完整代码
     ```
     ```xml
     // 这里是 MyMod.csproj 完整内容
     ```
     ```text
     // 这里是安装说明（怎么放进游戏 BepInEx/plugins 文件夹）
     ```
不要输出代码块以外的解释性长文。"""


def build_user_prompt(info: GameInfo, request: str, api_index: str,
                      has_unityengine: bool) -> str:
    lines = []
    lines.append("【游戏信息】")
    lines.append(f"- 游戏名：{info.game_name}")
    lines.append(f"- 引擎类型：{info.engine_desc}")
    lines.append(f"- 数据目录：{info.data_dir}")
    lines.append(f"- 已安装 BepInEx：{'是（' + info.bepinex_dir + '）' if info.bepinex_dir else '否（生成后需要先安装 BepInEx）'}")
    if info.dummy_dll_dir:
        lines.append(f"- IL2CPP DummyDll 目录：{info.dummy_dll_dir}")
    if has_unityengine:
        lines.append("- 可引用 UnityEngine.dll：是（可正常使用 MonoBehaviour/GameObject/Input 等 Unity 类型）")
    else:
        lines.append("- 可引用 UnityEngine.dll：否（请避免直接引用 UnityEngine 类型，改为只用 BepInEx/Harmony API 或反射实现）")
    if api_index:
        lines.append("\n【游戏 API 索引】（写挂钩代码时优先使用其中的类型/方法名，只做参考，不要照抄全部）")
        lines.append(api_index)
    for note in info.notes:
        lines.append(f"\n【注意】{note}")
    lines.append("\n【用户的 Mod 需求】")
    lines.append(request)
    lines.append("\n请按系统要求输出方案和三个代码块。")
    return "\n".join(lines)
