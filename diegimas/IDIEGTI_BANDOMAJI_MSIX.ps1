# Brėžly bandomasis MSIX paketas (toks pat, koks bus Microsoft Store'e, tik pasirašytas bandomuoju sertifikatu).
# Paleidimas: dešiniu pelės mygtuku -> „Run with PowerShell“. Paprašys administratoriaus teisių - jų reikia
# tik bandomajam sertifikatui įrašyti (Store versijai jų nereikės).
# Pašalinti: Parametrai -> Programos -> Brėžly -> Šalinti.

$ErrorActionPreference = "Stop"
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Start-Process powershell "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}
Set-Location $PSScriptRoot
try {
    Import-Certificate -FilePath .\Brezly_bandomasis.cer -CertStoreLocation Cert:\LocalMachine\TrustedPeople | Out-Null
    Add-AppxPackage -Path .\Brezly_bandomasis.msix -ForceUpdateFromAnyVersion
    Write-Host "Įdiegta. Brėžly rasi meniu Pradžia." -ForegroundColor Green
} catch {
    Write-Host "Nepavyko: $($_.Exception.Message)" -ForegroundColor Red
}
Read-Host "Spausk Enter"
