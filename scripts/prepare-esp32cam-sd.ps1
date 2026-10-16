param(
    [Parameter(Mandatory = $false)]
    [int]$DiskNumber = 6,

    [Parameter(Mandatory = $false)]
    [string]$Label = '135erGC-Cam'
)

$ErrorActionPreference = 'Stop'

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Administratorrechte erforderlich. PowerShell als Administrator starten.'
    }
}

Assert-Administrator
$disk = Get-Disk -Number $DiskNumber

if ($disk.BusType -ne 'USB') {
    throw "Abbruch: Disk $DiskNumber ist kein USB-Datentraeger ($($disk.BusType))."
}
if ($disk.FriendlyName -notmatch 'SD|MMC|Card|Generic') {
    throw "Abbruch: Disk $DiskNumber sieht nicht wie eine SD-Karte aus ($($disk.FriendlyName))."
}
if ($disk.Size -lt 8GB -or $disk.Size -gt 128GB) {
    throw "Abbruch: unerwartete Kartengroesse $([math]::Round($disk.Size / 1GB, 2)) GiB."
}
if ($disk.IsReadOnly) {
    throw 'Abbruch: SD-Karte ist schreibgeschuetzt.'
}

Write-Host "Ziel: Disk $DiskNumber / $($disk.FriendlyName) / $([math]::Round($disk.Size / 1GB, 2)) GiB" -ForegroundColor Cyan
Write-Host 'Alle vorhandenen Partitionen auf genau diesem Datentraeger werden geloescht.' -ForegroundColor Yellow

$existingPartitions = @(Get-Partition -DiskNumber $DiskNumber -ErrorAction SilentlyContinue)
if ($existingPartitions.Count -gt 0) {
    Clear-Disk -Number $DiskNumber -RemoveData -RemoveOEM -Confirm:$false
}

$disk = Get-Disk -Number $DiskNumber
if ($disk.PartitionStyle -eq 'RAW') {
    Initialize-Disk -Number $DiskNumber -PartitionStyle MBR | Out-Null
} elseif ($disk.PartitionStyle -ne 'MBR') {
    Set-Disk -Number $DiskNumber -PartitionStyle MBR
}

$partition = New-Partition -DiskNumber $DiskNumber -UseMaximumSize -AssignDriveLetter
$volume = Format-Volume -Partition $partition -FileSystem FAT32 -NewFileSystemLabel $Label -Confirm:$false -Force
$root = "$($volume.DriveLetter):\"

$folders = @(
    'gc',
    'gc\snapshots',
    'gc\timelapse',
    'gc\logs',
    'gc\recovery'
)
foreach ($folder in $folders) {
    New-Item -ItemType Directory -Path (Join-Path $root $folder) -Force | Out-Null
}

$metadata = [ordered]@{
    schema = 'gc-camera-storage-v1'
    name = '135er-GC-Cam'
    hostname = '135er-gc-cam'
    purpose = 'Grow Central ESP32-CAM local media storage'
    secrets_on_sd = $false
    created_utc = [DateTime]::UtcNow.ToString('o')
}
$metadata | ConvertTo-Json | Set-Content -Path (Join-Path $root 'gc\storage.json') -Encoding UTF8

@'
135er-GC-Cam SD storage

This card stores local camera media only.
ESP32 firmware is flashed into the ESP32 itself, not copied to this card.
No Wi-Fi password, MQTT password, private identity key or camera access token belongs on this SD card.

Folders:
  /gc/snapshots
  /gc/timelapse
  /gc/logs
  /gc/recovery
'@ | Set-Content -Path (Join-Path $root 'README.txt') -Encoding UTF8

Write-Host "Fertig: $root  Label=$Label  FAT32" -ForegroundColor Green
Get-Volume -DriveLetter $volume.DriveLetter | Format-List DriveLetter,FileSystemLabel,FileSystem,HealthStatus,Size,SizeRemaining
