// 编译用 UnityEngine 桩（仅用于让依赖 MonoBehaviour 的 BepInEx 插件可编译；
// 运行时由游戏真实的 UnityEngine 程序集提供实现，桩本身不参与运行）。
namespace UnityEngine
{
    public class Object { }
    public class Component : Object { }
    public class Behaviour : Component { }
    public class MonoBehaviour : Behaviour { }
    public class GameObject : Object { }
    public class Transform : Component { }
    public struct Vector2 { public float x; public float y; }
    public struct Vector3 { public float x; public float y; public float z; }
    public struct Quaternion { public float x; public float y; public float z; public float w; }
    public struct Color { public float r; public float g; public float b; public float a; }
    public enum KeyCode
    {
        None = 0, Escape = 27, Return = 13, Space = 32, LeftShift = 304, RightShift = 303,
        LeftControl = 306, RightControl = 305, LeftAlt = 308, RightAlt = 307,
        UpArrow = 273, DownArrow = 274, LeftArrow = 276, RightArrow = 275,
        A = 97, B = 98, C = 99, D = 100, E = 101, F = 102, G = 103, H = 104, I = 105,
        J = 106, K = 107, L = 108, M = 109, N = 110, O = 111, P = 112, Q = 113, R = 114,
        S = 115, T = 116, U = 117, V = 118, W = 119, X = 120, Y = 121, Z = 122,
        F1 = 282, F2 = 283, F3 = 284, F4 = 285, F5 = 286, F6 = 287, F7 = 288,
        F8 = 289, F9 = 290, F10 = 291, F11 = 292, F12 = 293
    }
    public static class Debug
    {
        public static void Log(object message) { }
        public static void LogWarning(object message) { }
        public static void LogError(object message) { }
    }
    public static class Time
    {
        public static float deltaTime => 0f;
        public static float time => 0f;
    }
    public static class Input
    {
        public static bool GetKeyDown(KeyCode key) => false;
        public static bool GetKey(KeyCode key) => false;
    }
}
