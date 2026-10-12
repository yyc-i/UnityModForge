using BepInEx;

namespace SampleGameMod
{
    // 一个最小的 BepInEx 5 插件：
    // - 只依赖 BepInEx.dll，不引用 UnityEngine.dll，任何 Unity 游戏都能编译
    // - 在游戏启动时输出日志；Update 每帧回调（可在此轮询按键、调用游戏 API）
    [BepInPlugin("com.example.samplegame.samplemod", "SampleGame 示例 Mod", "1.0.0")]
    public class Plugin : BaseUnityPlugin
    {
        private int _tick;

        private void Awake()
        {
            Logger.LogInfo("[SampleMod] 已加载！这个插件仅依赖 BepInEx API，可直接编译。");
        }

        private void Update()
        {
            // 每帧调用一次。真实 Mod 在这里轮询输入、修改游戏状态。
            // 示例：每 1000 帧输出一次日志，方便验证插件确实在跑。
            _tick++;
            if (_tick % 1000 == 0)
            {
                Logger.LogInfo($"[SampleMod] 已运行 {_tick} 帧");
            }
        }
    }
}
