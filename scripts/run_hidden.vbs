Set sh = CreateObject("Wscript.Shell")
If WScript.Arguments.Count >= 1 Then
  sh.Run "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & WScript.Arguments(0) & """", 0, False
End If
