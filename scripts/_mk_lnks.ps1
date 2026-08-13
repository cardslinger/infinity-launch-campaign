
$W = New-Object -ComObject WScript.Shell
function Make-Lnk($path, $target, $icon) {
  $l = $W.CreateShortcut($path)
  $l.TargetPath = $target
  $l.WorkingDirectory = Split-Path $target
  $l.WindowStyle = 7
  if (Test-Path $icon) { $l.IconLocation = $icon }
  $l.Description = 'Infinity Launch Campaign — Reality. Your Way.'
  $l.Save()
}

Make-Lnk -path "C:\\Users\\omega\\OneDrive - Roguedecker Games\\Desktop\\Infinity Launch.lnk" -target "C:\\Users\\omega\\OneDrive - Roguedecker Games\\Desktop\\Grok Projects\\InfinityLaunchCampaign\\Launch.bat" -icon "C:\\Users\\omega\\OneDrive - Roguedecker Games\\Desktop\\Grok Projects\\InfinityLaunchCampaign\\assets\\image.png"
Make-Lnk -path "C:\\Users\\omega\\OneDrive - Roguedecker Games\\Desktop\\Grok Projects\\Apps\\InfinityLaunchCampaign.lnk" -target "C:\\Users\\omega\\OneDrive - Roguedecker Games\\Desktop\\Grok Projects\\InfinityLaunchCampaign\\Launch.bat" -icon "C:\\Users\\omega\\OneDrive - Roguedecker Games\\Desktop\\Grok Projects\\InfinityLaunchCampaign\\assets\\image.png"