# UnityEngine 编译桩（UnityEngine.Stub）

一个**极小的 UnityEngine 程序集桩**，只用来让依赖 `MonoBehaviour` 的 BepInEx 插件在**编译期**能通过。

- 为什么需要：BepInEx 的 `BaseUnityPlugin` 继承 `UnityEngine.MonoBehaviour`，编译插件时必须能解析该类型。
- 为什么安全：桩里没有任何游戏/引擎代码，运行时由游戏真实的 UnityEngine 程序集提供实现，桩不参与运行。
- 什么时候用：正常情况应优先引用游戏 `Managed/` 里的真实 `UnityEngine.dll`（或 `UnityEngine.CoreModule.dll`）；只有游戏目录里完全找不到时，才用本桩。

## 编译

```bash
cd UnityEngineStub
dotnet build -c Release
# 产物：bin/Release/UnityEngine.dll → 复制到插件工程的 lib/
```

UnityModForge 工具在"游戏没有 UnityEngine.dll"时会自动在缓存目录生成并编译本桩（代码与这里一致），无需手动操作。
