$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

$cmd = $args[0]
$targetApp = 'Spotify'
if ($args.Count -gt 1) { $targetApp = $args[1] }

$mgr = Await ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
$sessions = $mgr.GetSessions()
$count = $sessions.Size

if ($cmd -eq 'list') {
    for ($i = 0; $i -lt $count; $i++) {
        $s = $sessions.GetAt($i)
        $title = ''
        try {
            $props = Await ($s.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.MediaProperties])
            $title = $props.Title
        } catch {}
        Write-Output "SESSION $i | APP=$($s.SourceAppUserModelId) | STATUS=$($s.GetPlaybackInfo().PlaybackStatus) | TITLE=$title"
    }
    exit 0
}

$chosen = $null
for ($i = 0; $i -lt $count; $i++) {
    $s = $sessions.GetAt($i)
    if ($s.SourceAppUserModelId -like "*$targetApp*") { $chosen = $s; break }
}
if (-not $chosen -and $count -gt 0) { $chosen = $sessions.GetAt(0) }
if (-not $chosen) { Write-Output "NO SESSION"; exit 1 }

switch ($cmd) {
    'status' {
        Write-Output "APP=$($chosen.SourceAppUserModelId)"
        Write-Output "STATUS=$($chosen.GetPlaybackInfo().PlaybackStatus)"
        exit 0
    }
    'toggle' { Await ($chosen.TryTogglePlayPauseAsync()) ([bool]) | Out-Null }
    'play'   { Await ($chosen.TryPlayAsync()) ([bool]) | Out-Null }
    'pause'  { Await ($chosen.TryPauseAsync()) ([bool]) | Out-Null }
    'next'   { Await ($chosen.TrySkipNextAsync()) ([bool]) | Out-Null }
    'prev'   { Await ($chosen.TrySkipPreviousAsync()) ([bool]) | Out-Null }
}
Write-Output "OK"