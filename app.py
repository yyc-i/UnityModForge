#!/usr/bin/env python3
"""UnityModForge —— 一句话生成 Unity 单机游戏 Mod 的本地桌面工具。

用法：
  python3 app.py                    启动图形界面
  python3 app.py --cli --game <游戏目录> --request "想改什么" --api-key xxx [--install]
"""
import argparse
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, scrolledtext, ttk

from unitymodforge.config import (API_PRESETS, BEPINEX_PLATFORMS, OLLAMA_BASE,
                                  OLLAMA_DEFAULT_MODEL, AppConfig, load_config,
                                  save_config)
from unitymodforge.game_scanner import (dump_api_index, find_unity_game,
                                        find_unityengine_dll)
from unitymodforge.llm_client import (LLMError, call_chat_completion,
                                      detect_ollama_models,
                                      extract_csharp_blocks, extract_xml_block)
from unitymodforge.mod_builder import (build_mod, ensure_bepinex_dll,
                                       install_mod, install_instructions,
                                       scaffold_project)
from unitymodforge.prompts import SYSTEM_PROMPT, build_user_prompt

# ---------------- 主题色 ----------------
COLOR_BG = "#f2f4f8"        # 页面背景
COLOR_CARD = "#ffffff"      # 卡片
COLOR_HEADER = "#2b3a67"    # 顶栏
COLOR_PRIMARY = "#4f6ef7"   # 主色
COLOR_PRIMARY_DARK = "#3d5bf0"
COLOR_TEXT = "#1f2329"
COLOR_MUTED = "#8a919f"
COLOR_OK = "#22a06b"
COLOR_ERR = "#e5484d"
COLOR_WARN = "#d97706"


def _pick_font(root, candidates, size: int) -> tuple:
    fams = set(tkfont.families(root))
    for c in candidates:
        if c in fams:
            return (c, size)
    return ("TkDefaultFont", size)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UnityModForge · 一句话生成 Unity 游戏 Mod")
        self.geometry("920x780")
        self.minsize(860, 700)
        self.cfg = load_config()
        self.game_info = None
        self.api_index = ""
        self.last_project_dir = ""
        self.log_queue = queue.Queue()
        self.working = False

        self.ui_font = _pick_font(self, ["Microsoft YaHei", "PingFang SC",
                                         "Noto Sans CJK SC", "WenQuanYi Micro Hei"], 10)
        self.ui_font_bold = (self.ui_font[0], 10, "bold")
        self._setup_style()
        self._build_header()
        self._build_body()
        self.after(100, self._drain_log)

    # ---------- 样式 ----------
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=self.ui_font, background=COLOR_BG, foreground=COLOR_TEXT)
        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=self.ui_font, padding=(18, 8))
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_CARD)],
                  foreground=[("selected", COLOR_PRIMARY)])
        style.configure("Card.TFrame", background=COLOR_CARD)
        style.configure("CardTitle.TLabel", background=COLOR_CARD, foreground=COLOR_HEADER,
                        font=self.ui_font_bold)
        style.configure("Muted.TLabel", background=COLOR_CARD, foreground=COLOR_MUTED,
                        font=self.ui_font)
        style.configure("Primary.TButton", background=COLOR_PRIMARY, foreground="#ffffff",
                        font=self.ui_font_bold, padding=(14, 7), borderwidth=0)
        style.map("Primary.TButton",
                  background=[("active", COLOR_PRIMARY_DARK), ("disabled", "#a9b4e8")],
                  foreground=[("disabled", "#eef1ff")])
        style.configure("Secondary.TButton", background="#e6ebff", foreground=COLOR_PRIMARY,
                        font=self.ui_font, padding=(12, 6), borderwidth=0)
        style.map("Secondary.TButton",
                  background=[("active", "#d8e0ff"), ("disabled", "#eef1fa")],
                  foreground=[("disabled", COLOR_MUTED)])
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor="#c9d1e5",
                        padding=6, insertcolor=COLOR_TEXT)
        style.configure("TCombobox", fieldbackground="#ffffff", bordercolor="#c9d1e5",
                        arrowcolor=COLOR_PRIMARY, padding=5)
        style.configure("TCheckbutton", background=COLOR_CARD, foreground=COLOR_TEXT,
                        font=self.ui_font)
        style.map("TCheckbutton", background=[("active", COLOR_CARD)])

    # ---------- 顶栏 ----------
    def _build_header(self):
        header = tk.Frame(self, bg=COLOR_HEADER, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="UnityModForge", bg=COLOR_HEADER, fg="#ffffff",
                 font=(self.ui_font[0], 18, "bold")).pack(side="left", padx=20)
        tk.Label(header, text="选择游戏 → 说一句话 → 自动生成并安装 Mod",
                 bg=COLOR_HEADER, fg="#c6d2f5",
                 font=self.ui_font).pack(side="left", padx=(4, 0), pady=(5, 0))

    # ---------- 主体 ----------
    def _build_body(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=14, pady=(12, 4))
        self.tab_gen = ttk.Frame(nb, padding=8)
        self.tab_set = ttk.Frame(nb, padding=8)
        nb.add(self.tab_gen, text="  生成 Mod  ")
        nb.add(self.tab_set, text="  设置  ")
        self._build_gen_tab()
        self._build_settings_tab()

    def _card(self, parent, title):
        box = ttk.Frame(parent, style="Card.TFrame")
        box.pack(fill="x", pady=(0, 10))
        ttk.Label(box, text=title, style="CardTitle.TLabel").pack(anchor="w", padx=14, pady=(10, 2))
        return box

    # ---------- 生成页 ----------
    def _build_gen_tab(self):
        # ① 选择游戏
        card1 = self._card(self.tab_gen, "①  选择游戏（Unity 单机游戏目录）")
        row = ttk.Frame(card1, style="Card.TFrame")
        row.pack(fill="x", padx=14, pady=(2, 4))
        self.game_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.game_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(row, text="浏览…", style="Secondary.TButton",
                   command=self._pick_game).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="扫描游戏", style="Primary.TButton",
                   command=self._scan_game).pack(side="left")
        self.scan_box = tk.Frame(card1, bg=COLOR_CARD)
        self.scan_box.pack(fill="x", padx=14, pady=(2, 10))
        self.scan_text = tk.Text(self.scan_box, height=5, wrap="word", relief="flat",
                                 bg=COLOR_CARD, fg=COLOR_TEXT, font=self.ui_font,
                                 highlightthickness=0, state="disabled")
        self.scan_text.pack(fill="x")
        self._scan_write("尚未扫描游戏。点击「扫描游戏」读取游戏结构。", COLOR_MUTED)

        # ② 需求
        card2 = self._card(self.tab_gen, "②  用一句话说出你想改什么")
        self.request_text = tk.Text(card2, height=4, wrap="word", relief="flat",
                                    bg="#fbfcff", fg=COLOR_TEXT, font=self.ui_font,
                                    insertbackground=COLOR_TEXT,
                                    highlightthickness=1, highlightbackground="#c9d1e5",
                                    highlightcolor=COLOR_PRIMARY, padx=10, pady=8)
        self.request_text.pack(fill="x", padx=14, pady=(2, 10))
        self.request_text.insert("1.0", "例如：给游戏加一个按键 F9，按下后打开商店面板，可以购买一把伤害为 100 的剑，按 H 键回血 50 点")

        # ③ 生成
        card3 = self._card(self.tab_gen, "③  生成并安装")
        row3 = ttk.Frame(card3, style="Card.TFrame")
        row3.pack(fill="x", padx=14, pady=(2, 10))
        ttk.Button(row3, text="准备编译环境", style="Secondary.TButton",
                   command=self._prep_env).pack(side="left")
        self.gen_btn = ttk.Button(row3, text="生成并编译 Mod", style="Primary.TButton",
                                  command=self._generate)
        self.gen_btn.pack(side="left", padx=10)
        self.install_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3, text="编译成功后自动安装到游戏", variable=self.install_var,
                        style="TCheckbutton").pack(side="left", padx=(6, 0))
        ttk.Button(row3, text="打开游戏目录", style="Secondary.TButton",
                   command=self._open_game_dir).pack(side="right")
        ttk.Button(row3, text="打开输出目录", style="Secondary.TButton",
                   command=self._open_output_dir).pack(side="right", padx=(0, 6))
        self.open_proj_btn = ttk.Button(row3, text="打开工程目录", style="Secondary.TButton",
                                        command=self._open_project_dir, state="disabled")
        self.open_proj_btn.pack(side="right", padx=(0, 6))
        self.outdir_label_var = tk.StringVar(value="输出目录：" + self.cfg.output_dir)
        ttk.Label(card3, textvariable=self.outdir_label_var,
                  style="Muted.TLabel").pack(anchor="w", padx=14, pady=(0, 10))

        # 日志
        log_card = self._card(self.tab_gen, "运行日志 / 结果")
        self.log_text = scrolledtext.ScrolledText(log_card, height=11, wrap="word",
                                                  relief="flat", bg="#fbfcff",
                                                  fg=COLOR_TEXT, font=("Consolas", 9),
                                                  highlightthickness=1,
                                                  highlightbackground="#e3e7f0",
                                                  padx=10, pady=8)
        self.log_text.pack(fill="both", expand=True, padx=14, pady=(2, 12))
        self.log_text.tag_configure("ok", foreground=COLOR_OK)
        self.log_text.tag_configure("err", foreground=COLOR_ERR)
        self.log_text.tag_configure("warn", foreground=COLOR_WARN)
        self.log_text.tag_configure("head", foreground=COLOR_PRIMARY,
                                    font=("Consolas", 9, "bold"))
        self.log_text.configure(state="disabled")

    def _scan_write(self, text, color=COLOR_TEXT):
        self.scan_text.configure(state="normal")
        self.scan_text.delete("1.0", "end")
        self.scan_text.insert("1.0", text)
        self.scan_text.configure(fg=color, state="disabled")

    # ---------- 设置页 ----------
    def _build_settings_tab(self):
        card1 = self._card(self.tab_set, "大模型 API（OpenAI 兼容）")
        ttk.Label(card1,
                  text="带「免费」的预设模型调用不收费（需免费注册获取 Key）；"
                       "本地 Ollama 完全免费、无需注册和 Key。",
                  style="Muted.TLabel").pack(anchor="w", padx=14)
        g = ttk.Frame(card1, style="Card.TFrame")
        g.pack(fill="x", padx=14, pady=(4, 10))
        g.columnconfigure(1, weight=1)

        ttk.Label(g, text="服务商预设", style="Muted.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        self.preset_var = tk.StringVar()
        cb = ttk.Combobox(g, textvariable=self.preset_var,
                          values=["自定义"] + list(API_PRESETS.keys()), state="readonly")
        cb.grid(row=0, column=1, sticky="we", pady=4)
        cb.current(0)
        cb.bind("<<ComboboxSelected>>", self._on_preset)

        ttk.Label(g, text="API 地址", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=4)
        self.base_var = tk.StringVar(value=self.cfg.api_base_url)
        ttk.Entry(g, textvariable=self.base_var).grid(row=1, column=1, sticky="we", pady=4)

        ttk.Label(g, text="API Key", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        self.key_var = tk.StringVar(value=self.cfg.api_key)
        ttk.Entry(g, textvariable=self.key_var, show="*").grid(row=2, column=1, sticky="we", pady=4)
        self.key_hint_var = tk.StringVar(value="")
        ttk.Label(g, textvariable=self.key_hint_var, style="Muted.TLabel",
                  foreground=COLOR_WARN).grid(row=3, column=1, sticky="w")

        ttk.Label(g, text="模型", style="Muted.TLabel").grid(row=4, column=0, sticky="w", pady=4)
        self.model_var = tk.StringVar(value=self.cfg.model)
        ttk.Entry(g, textvariable=self.model_var).grid(row=4, column=1, sticky="we", pady=4)

        # 本地 Ollama 检测行
        ollama_row = ttk.Frame(card1, style="Card.TFrame")
        ollama_row.pack(fill="x", padx=14, pady=(0, 10))
        ttk.Label(ollama_row, text="本地 Ollama（免费·无需Key）",
                  style="Muted.TLabel").pack(side="left")
        ttk.Button(ollama_row, text="检测并填入模型", style="Secondary.TButton",
                   command=self._detect_ollama).pack(side="left", padx=8)
        self.ollama_model_var = tk.StringVar()
        self.ollama_combo = ttk.Combobox(ollama_row, textvariable=self.ollama_model_var,
                                         values=[], width=28)
        self.ollama_combo.pack(side="left", padx=(0, 6))
        ttk.Button(ollama_row, text="用所选模型", style="Primary.TButton",
                   command=self._use_ollama_model).pack(side="left")

        card2 = self._card(self.tab_set, "BepInEx 与输出")
        g2 = ttk.Frame(card2, style="Card.TFrame")
        g2.pack(fill="x", padx=14, pady=(2, 10))
        g2.columnconfigure(1, weight=1)

        ttk.Label(g2, text="BepInEx 平台", style="Muted.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        self.plat_var = tk.StringVar(value=self.cfg.bepinex_platform)
        ttk.Combobox(g2, textvariable=self.plat_var, values=BEPINEX_PLATFORMS,
                     state="readonly").grid(row=0, column=1, sticky="w", pady=4)

        self.auto_var = tk.BooleanVar(value=self.cfg.bepinex_auto_download)
        ttk.Checkbutton(g2, text="自动下载 BepInEx 5.4.22（网络不通时改用本地安装包）",
                        variable=self.auto_var, style="TCheckbutton").grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(g2, text="本地安装包", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        r1 = ttk.Frame(g2, style="Card.TFrame")
        r1.grid(row=2, column=1, sticky="we", pady=4)
        self.zip_var = tk.StringVar(value=self.cfg.bepinex_zip_path)
        ttk.Entry(r1, textvariable=self.zip_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(r1, text="浏览…", style="Secondary.TButton", command=self._pick_zip).pack(side="left")

        ttk.Label(g2, text="输出目录", style="Muted.TLabel").grid(row=3, column=0, sticky="w", pady=4)
        r2 = ttk.Frame(g2, style="Card.TFrame")
        r2.grid(row=3, column=1, sticky="we", pady=4)
        self.out_var = tk.StringVar(value=self.cfg.output_dir)
        ttk.Entry(r2, textvariable=self.out_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(r2, text="浏览…", style="Secondary.TButton", command=self._pick_out).pack(side="left")

        ttk.Button(card2, text="保存设置", style="Primary.TButton",
                   command=self._save_settings).pack(anchor="w", padx=14, pady=(0, 12))

    # ---------- 动作 ----------
    def _pick_game(self):
        d = filedialog.askdirectory(title="选择 Unity 游戏根目录（包含 xxx_Data 文件夹的目录）")
        if d:
            self.game_var.set(d)

    def _open_game_dir(self):
        if not self.game_info:
            messagebox.showwarning("提示", "请先扫描游戏")
            return
        self._open_dir(self.game_info.game_dir)

    def _scan_game(self):
        d = self.game_var.get().strip()
        if not d:
            messagebox.showwarning("提示", "请先选择游戏目录")
            return
        self._set_working(True)
        self._run_async(self._do_scan, d)

    def _do_scan(self, d):
        info = find_unity_game(d)
        if info is None:
            self._scan_write("❌ 没有在目录里找到 Unity 游戏（缺少 xxx_Data 数据文件夹）", COLOR_ERR)
            return
        self.game_info = info
        self.api_index, tool = dump_api_index(info)
        ue = find_unityengine_dll(info)
        lines = [
            f"游戏名：{info.game_name}    引擎：{info.engine_desc}",
            f"数据目录：{info.data_dir}",
            f"主程序集：{info.assembly_csharp or info.global_metadata or '（IL2CPP，需要 DummyDll）'}",
            f"BepInEx：{'已安装' if info.bepinex_dir else '未安装（生成后将自动安装）'}    "
            f"API 索引：{'已生成（' + tool + '）' if self.api_index else '未生成'}    "
            f"UnityEngine：{'可用' if ue else '自动编译桩'}",
        ]
        for note in info.notes:
            lines.append("⚠ " + note)
        if info.is_il2cpp:
            lines.append("⚠ IL2CPP 版游戏：当前版本只支持 Mono(.NET) 版 Unity 游戏（BepInEx 5 管线），暂不支持一键生成。")
        self._scan_write("\n".join(lines), COLOR_TEXT)

    def _prep_env(self):
        self._set_working(True)
        self._run_async(self._do_prep_env)

    def _do_prep_env(self):
        try:
            p = ensure_bepinex_dll(self.cfg, self.game_info, on_log=self._log)
            self._log(f"✅ 编译环境就绪，BepInEx.dll：{p}", ok=True)
        except Exception as e:
            self._log(f"❌ {e}", err=True)

    def _generate(self):
        if not self.game_info:
            messagebox.showwarning("提示", "请先点击“扫描游戏”")
            return
        req = self.request_text.get("1.0", "end").strip()
        if not req:
            messagebox.showwarning("提示", "请填写你想做的 Mod 需求")
            return
        self._set_working(True)
        self._run_async(self._do_generate, req)

    def _do_generate(self, request):
        try:
            self._log("=" * 54, head=True)
            if self.game_info.is_il2cpp:
                self._log("❌ 该游戏是 IL2CPP 版。当前版本工具只支持 Mono(.NET) 版 Unity 游戏"
                          "（BepInEx 5 管线）；IL2CPP 需要 BepInEx 6 + Il2CppInterop，暂不支持。", err=True)
                return
            ensure_bepinex_dll(self.cfg, self.game_info, on_log=self._log)
            if not self.api_index:
                self.api_index, _tool = dump_api_index(self.game_info)
            ue = find_unityengine_dll(self.game_info)
            user_prompt = build_user_prompt(self.game_info, request, self.api_index,
                                            bool(ue) or not self.game_info.is_il2cpp)
            self._log("正在让 AI 编写 Mod 代码…")
            content = call_chat_completion(
                self.cfg,
                [{"role": "system", "content": SYSTEM_PROMPT},
                 {"role": "user", "content": user_prompt}],
                on_log=self._log)
            code_blocks = extract_csharp_blocks(content)
            if not code_blocks:
                raise RuntimeError("AI 返回内容里没有 C# 代码块，请换一种说法重试。返回内容片段：\n" + content[:300])
            plugin_code = code_blocks[0]
            csproj = extract_xml_block(content)

            stamp = time.strftime("%Y%m%d_%H%M%S")
            out_root = os.path.join(self.cfg.output_dir,
                                    f"{self.game_info.game_name}_Mod_{stamp}")
            self._log(f"正在生成工程：{out_root}")
            project_dir = scaffold_project(out_root, self.game_info, plugin_code,
                                           csproj, on_log=self._log)
            ok, dll_path, build_log = build_mod(project_dir, on_log=self._log)
            if not ok:
                self._log("❌ " + build_log, err=True)
                self._log("提示：编译失败多为代码用到游戏内部 API 但索引缺失。可安装 ilspycmd 后重扫，"
                          "或把错误发回修改。", warn=True)
                return
            self._log(f"✅ 编译成功！Mod DLL：{dll_path}", ok=True)

            if self.install_var.get():
                try:
                    dest = install_mod(self.cfg, self.game_info, dll_path, on_log=self._log)
                    self._log("启动游戏即可体验；再次生成会覆盖旧版本。", ok=True)
                except Exception as e:
                    self._log(f"❌ 自动安装失败：{e}\n   可手动按说明安装："
                              f"{install_instructions(self.game_info, os.path.basename(dll_path))}", err=True)
            else:
                self._log("未勾选自动安装，Mod 工程保留在：" + project_dir)
                self._log(install_instructions(self.game_info, os.path.basename(dll_path)))
            self._log(f"工程目录（可手动改代码后重新编译）：{project_dir}")
            self.last_project_dir = project_dir
            self.after(0, lambda: self.open_proj_btn.configure(state="normal"))
        except Exception as e:
            self._log("❌ " + str(e), err=True)
            if isinstance(e, LLMError):
                self._log("提示：检查“设置”页的 API 地址、Key、模型是否正确，余额是否充足。", warn=True)

    # ---------- 设置动作 ----------
    def _on_preset(self, _e=None):
        name = self.preset_var.get()
        if name in API_PRESETS:
            p = API_PRESETS[name]
            self.base_var.set(p["base"])
            self.model_var.set(p["model"])
            if not p.get("need_key", True):
                self.key_var.set("")
                self.key_hint_var.set("本地模型无需 API Key，可直接生成")
            elif p.get("free"):
                self.key_hint_var.set("免费模型：去对应平台免费注册获取 Key 后填入")
            else:
                self.key_hint_var.set("")

    def _detect_ollama(self):
        self._set_working(True)
        self._run_async(self._do_detect_ollama)

    def _do_detect_ollama(self):
        self._log("正在检测本地 Ollama（127.0.0.1:11434）…")
        models = detect_ollama_models(OLLAMA_BASE)
        if not models:
            self._log("未检测到本地 Ollama。", warn=True)
            self._log("安装方法：1) 官网 https://ollama.com 下载安装并启动；"
                      "2) 打开终端执行：ollama pull qwen2.5-coder:7b "
                      "（首次自动下载约 5GB，之后离线可用、完全免费）；"
                      "3) 回到本页再点「检测并填入模型」。", warn=True)
            return
        self.ollama_combo.configure(values=models)
        pick = next((m for m in models if "coder" in m.lower() or "qwen" in m.lower()), models[0])
        self.ollama_model_var.set(pick)
        self._log("✅ 检测到本地 Ollama 模型：\n   " + "\n   ".join(models))
        self._log("点「用所选模型」即可切换到本地免费模型（无需 Key）。", ok=True)

    def _use_ollama_model(self):
        model = self.ollama_model_var.get().strip()
        if not model:
            messagebox.showwarning("提示", "请先在列表里选择模型（或点「检测并填入模型」）")
            return
        self.base_var.set(OLLAMA_BASE)
        self.model_var.set(model)
        self.key_var.set("")
        self.key_hint_var.set("本地模型无需 API Key，可直接生成")
        self.preset_var.set("自定义")
        self._log(f"已切换到本地 Ollama 模型：{model}（无需 Key）", ok=True)

    def _open_output_dir(self):
        self._open_dir(self.cfg.output_dir)

    def _open_project_dir(self):
        if getattr(self, "last_project_dir", None):
            self._open_dir(self.last_project_dir)
        else:
            messagebox.showwarning("提示", "还没有生成过 Mod")

    def _open_dir(self, path):
        if not os.path.isdir(path):
            messagebox.showwarning("提示", f"目录不存在：{path}")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self._log(f"无法打开目录：{e}")

    def _pick_zip(self):
        p = filedialog.askopenfilename(title="选择 BepInEx 安装包（zip）",
                                       filetypes=[("zip", "*.zip")])
        if p:
            self.zip_var.set(p)

    def _pick_out(self):
        d = filedialog.askdirectory(title="选择 Mod 输出目录")
        if d:
            self.out_var.set(d)

    def _save_settings(self):
        self.cfg.api_base_url = self.base_var.get().strip()
        self.cfg.api_key = self.key_var.get().strip()
        self.cfg.model = self.model_var.get().strip()
        self.cfg.bepinex_platform = self.plat_var.get()
        self.cfg.bepinex_auto_download = self.auto_var.get()
        self.cfg.bepinex_zip_path = self.zip_var.get().strip()
        self.cfg.output_dir = self.out_var.get().strip() or os.path.expanduser("~")
        save_config(self.cfg)
        self.outdir_label_var.set("输出目录：" + self.cfg.output_dir)
        messagebox.showinfo("已保存", "设置已保存到 ~/.unitymodforge/config.json")

    # ---------- 通用 ----------
    def _log(self, msg, ok=False, err=False, warn=False, head=False):
        self.log_queue.put((str(msg), ok, err, warn, head))

    def _drain_log(self):
        try:
            while True:
                msg, ok, err, warn, head = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                tag = "ok" if ok else "err" if err else "warn" if warn else "head" if head else None
                self.log_text.insert("end", msg + "\n", tag)
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._drain_log)

    def _set_working(self, flag):
        self.working = flag
        state = "disabled" if flag else "normal"
        self.gen_btn.configure(state=state)

    def _run_async(self, fn, *args):
        def wrap():
            try:
                fn(*args)
            except Exception:
                self._log("❌ 发生异常：\n" + traceback.format_exc(), err=True)
            finally:
                self.after(0, lambda: self._set_working(False))
        threading.Thread(target=wrap, daemon=True).start()


# ---------------- CLI ----------------
def run_cli(args) -> int:
    cfg = AppConfig(api_base_url=args.base_url, api_key=args.api_key, model=args.model,
                    output_dir=args.output_dir, bepinex_platform=args.bepinex_platform,
                    bepinex_auto_download=not args.no_auto_download,
                    bepinex_zip_path=args.bepinex_zip or "")
    info = find_unity_game(args.game)
    if info is None:
        print("❌ 没有在目录里找到 Unity 游戏（缺少 xxx_Data 数据文件夹）", file=sys.stderr)
        return 2
    print(f"✅ 扫描成功：{info.game_name}（{info.engine_desc}）")
    if info.is_il2cpp:
        print("❌ 该游戏是 IL2CPP 版。当前版本工具只支持 Mono(.NET) 版 Unity 游戏（BepInEx 5 管线）；"
              "IL2CPP 需要 BepInEx 6 + Il2CppInterop，暂不支持。", file=sys.stderr)
        return 6
    api_index, tool = dump_api_index(info)
    print(f"   API 索引：{'已生成（' + tool + '）' if api_index else '未生成（' + tool + '）'}")
    try:
        ensure_bepinex_dll(cfg, info, on_log=lambda m: print("  " + m))
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        return 3
    ue = find_unityengine_dll(info)
    user_prompt = build_user_prompt(info, args.request, api_index, bool(ue) or not info.is_il2cpp)
    print("正在让 AI 编写 Mod 代码…")
    content = call_chat_completion(
        cfg,
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": user_prompt}],
        on_log=lambda m: print("  " + m))
    blocks = extract_csharp_blocks(content)
    if not blocks:
        print("❌ AI 返回内容里没有 C# 代码块", file=sys.stderr)
        return 4
    csproj = extract_xml_block(content)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_root = os.path.join(cfg.output_dir, f"{info.game_name}_Mod_{stamp}")
    print(f"正在生成工程：{out_root}")
    project_dir = scaffold_project(out_root, info, blocks[0], csproj)
    ok, dll_path, build_log = build_mod(project_dir, on_log=lambda m: print("  " + m))
    if not ok:
        print("❌ " + build_log, file=sys.stderr)
        return 5
    print(f"✅ 编译成功！Mod DLL：{dll_path}")
    if args.install:
        try:
            dest = install_mod(cfg, info, dll_path, on_log=lambda m: print("  " + m))
            print(f"✅ 已一键安装到游戏：{dest}")
        except Exception as e:
            print(f"❌ 自动安装失败：{e}", file=sys.stderr)
            return 7
    else:
        print(install_instructions(info, os.path.basename(dll_path)))
    return 0


def main():
    parser = argparse.ArgumentParser(description="UnityModForge —— 一句话生成 Unity 游戏 Mod")
    parser.add_argument("--cli", action="store_true", help="命令行模式（不需要图形界面）")
    parser.add_argument("--game", help="游戏根目录（含 xxx_Data 文件夹）")
    parser.add_argument("--request", help="用一句话描述想做的 Mod")
    parser.add_argument("--api-key", default="", help="LLM API Key")
    parser.add_argument("--base-url", default="https://api.deepseek.com/v1", help="OpenAI 兼容 API 地址")
    parser.add_argument("--model", default="deepseek-chat", help="模型名")
    parser.add_argument("--output-dir", default=os.path.join(os.path.expanduser("~"), "UnityModForgeOutput"))
    parser.add_argument("--bepinex-platform", default="x64", choices=BEPINEX_PLATFORMS)
    parser.add_argument("--no-auto-download", action="store_true", help="不自动下载 BepInEx")
    parser.add_argument("--bepinex-zip", default="", help="本地 BepInEx 安装包路径")
    parser.add_argument("--install", action="store_true", help="编译成功后自动安装到游戏 BepInEx/plugins")
    args = parser.parse_args()

    if args.cli:
        if not args.game or not args.request:
            parser.error("CLI 模式需要 --game 和 --request")
        sys.exit(run_cli(args))

    try:
        App().mainloop()
    except Exception as e:
        print("启动图形界面失败：", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
