Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d C:\Vision && docker compose up -d", 0, False
