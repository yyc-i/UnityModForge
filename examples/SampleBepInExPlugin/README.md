# SampleGame 示例 Mod（BepInEx 5）

这是一个**最小可编译**的 BepInEx 插件示例，演示工具生成的工程长什么样。
它只依赖 `BepInEx.dll`（已放在 `lib/` 下），不引用 UnityEngine，因此任何 Unity 游戏都能编译。

## 编译

```bash
cd SampleBepInExPlugin
dotnet build -c Release
```

产物：`bin/Release/SampleGameMod.dll`

## 安装

把 `bin/Release/SampleGameMod.dll` 复制到游戏的 `BepInEx/plugins/` 文件夹，启动游戏即可在日志看到：

```
[SampleMod] 已加载！
```

## 说明

- 真实使用中，由 AI 按你的需求生成更复杂的代码（挂按键、补丁游戏内部类型、加物品等）。
- 若游戏是 IL2CPP 且你没有 DummyDll，AI 生成的代码会避免直接引用 UnityEngine 类型，改用反射。
