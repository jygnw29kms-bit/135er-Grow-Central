$ErrorActionPreference = 'Stop'

$kitDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$compressedImage = Get-ChildItem -LiteralPath $kitDirectory -Filter '135er_Grow_Central_RPi3B_Test.img.xz' | Select-Object -First 1
$rawImage = Join-Path $kitDirectory '135er_Grow_Central_RPi3B_Test.img'
$kernel = Join-Path $kitDirectory 'kernel8.img'
$initramfs = Join-Path $kitDirectory 'initramfs8'

if (-not (Test-Path -LiteralPath $rawImage)) {
    if (-not $compressedImage) {
        throw 'Die Datei 135er_Grow_Central_RPi3B_Test.img.xz muss im selben Ordner liegen.'
    }

    $xz = Get-Command xz.exe -ErrorAction SilentlyContinue
    $sevenZip = Get-Command 7z.exe -ErrorAction SilentlyContinue
    if ($xz) {
        & $xz.Source -dk $compressedImage.FullName
    } elseif ($sevenZip) {
        & $sevenZip.Source x '-y' "-o$kitDirectory" $compressedImage.FullName
    } else {
        throw 'Zum Entpacken wird xz.exe oder 7z.exe im Windows-PATH benötigt.'
    }
}

$qemu = Get-Command qemu-system-aarch64.exe -ErrorAction SilentlyContinue
if (-not $qemu) {
    throw 'qemu-system-aarch64.exe wurde nicht gefunden. Installiere QEMU und ergänze den Installationsordner im Windows-PATH.'
}

Write-Host '135er-Grow Central startet in QEMU.' -ForegroundColor Green
Write-Host 'Weboberfläche: http://localhost:8080'
Write-Host 'SSH: ssh -p 2222 test@localhost (Passwort: test)'
Write-Host 'QEMU beenden: Strg+A, danach X'

& $qemu.Source `
    -M virt -cpu cortex-a72 -smp 4 -m 1536 `
    -nographic -no-reboot `
    -kernel $kernel -initrd $initramfs `
    -append 'root=/dev/vda2 rootfstype=ext4 rw rootwait console=ttyAMA0,115200 fsck.repair=yes net.ifnames=0' `
    -drive "file=$rawImage,format=raw,if=none,id=system" `
    -device 'virtio-blk-device,drive=system' `
    -netdev 'user,id=network,hostfwd=tcp::8080-:8080,hostfwd=tcp::2222-:22' `
    -device 'virtio-net-device,netdev=network'
