; UnityModForge 安装包脚本（可选，Inno Setup 用）
; 用法：先用 build_windows.bat 生成 dist\UnityModForge.exe，
;       再安装 Inno Setup 6（https://jrsoftware.org/isinfo.php），
;       双击本文件 → Compile，即得到 UnityModForge_Setup.exe 安装程序。
;
; 也可以不做这一步：dist\UnityModForge.exe 本身就是绿色单文件，双击即用。

[Setup]
AppName=UnityModForge
AppVersion=1.0.0
AppPublisher=UnityModForge
DefaultDirName={autopf}\UnityModForge
DefaultGroupName=UnityModForge
OutputBaseFilename=UnityModForge_Setup
OutputDir=installer
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\UnityModForge.exe

[Files]
Source: "dist\UnityModForge.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\UnityModForge"; Filename: "{app}\UnityModForge.exe"
Name: "{group}\卸载 UnityModForge"; Filename: "{uninstallexe}"
Name: "{autodesktop}\UnityModForge"; Filename: "{app}\UnityModForge.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标："

[Run]
Filename: "{app}\UnityModForge.exe"; Description: "立即运行 UnityModForge"; Flags: nowait postinstall skipifsilent
