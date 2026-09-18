Set WshShell = CreateObject("WScript.Shell")
' Ejecuta iniciar_faro.bat en segundo plano sin ventana negra (0 = oculto)
WshShell.Run chr(34) & "iniciar_faro.bat" & Chr(34), 0
Set WshShell = Nothing
