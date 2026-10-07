$ErrorActionPreference = 'Stop'
$listeners = @(Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -gt 0) {
    $matching = @($listeners | Where-Object {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)"
        $process.Name -eq 'ssh.exe' -and $process.CommandLine -like '*germanmallo@mallocenter*' -and $process.CommandLine -like '*127.0.0.1:8080:127.0.0.1:8090*'
    })
    if ($matching.Count -ne $listeners.Count) {
        throw 'El puerto 8080 ya esta ocupado por otro proceso. Cierra el estudio Docker del PC antes de abrir el tunel.'
    }
    Write-Host 'El tunel ya esta abierto: http://localhost:8080'
    exit 0
}
Write-Host 'Abre http://localhost:8080 y manten esta ventana abierta. Ctrl+C cierra el tunel.'
& ssh -N -L 127.0.0.1:8080:127.0.0.1:8090 -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 germanmallo@mallocenter
exit $LASTEXITCODE
