$ErrorActionPreference = 'Stop'
$baseDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$qemuCommand = Get-Command qemu-system-aarch64.exe -ErrorAction SilentlyContinue
if ($qemuCommand) {
    $qemuPath = $qemuCommand.Path
} else {
    $standardPath = 'C:\Program Files\qemu\qemu-system-aarch64.exe'
    if (Test-Path -LiteralPath $standardPath) {
        $qemuPath = $standardPath
    } else {
        throw 'QEMU wurde nicht gefunden. Installiere QEMU fuer Windows unter C:\Program Files\qemu oder ergaenze QEMU im PATH.'
    }
}

$image = Join-Path $baseDirectory '135er_Grow_Central_QEMU_ARM64.qcow2'
$kernel = Join-Path $baseDirectory 'vmlinuz-qemu-arm64'
$initrd = Join-Path $baseDirectory 'initrd-qemu-arm64.img'
foreach ($requiredFile in @($image, $kernel, $initrd)) {
    if (-not (Test-Path -LiteralPath $requiredFile)) { throw "Datei fehlt: $requiredFile" }
}

Write-Host '135er-Grow Central QEMU ARM64 startet.' -ForegroundColor Green
Write-Host 'Weboberflaeche nach dem Boot: http://localhost:8080'
Write-Host 'SSH: ssh -p 2222 test@localhost  (Passwort: test)'
Write-Host 'Beenden: Strg+A, danach X'

& $qemuPath `
    -M virt -cpu cortex-a72 -smp 4 -m 2048 `
    -nographic -no-reboot `
    -kernel $kernel -initrd $initrd `
    -append 'root=/dev/vda1 rw rootwait console=ttyAMA0,115200 fsck.repair=yes net.ifnames=0' `
    -drive "file=$image,format=qcow2,if=none,id=system" `
    -device 'virtio-blk-pci,drive=system' `
    -netdev 'user,id=network,hostfwd=tcp:127.0.0.1:8080-:8080,hostfwd=tcp:127.0.0.1:2222-:22' `
    -device 'virtio-net-pci,netdev=network'
