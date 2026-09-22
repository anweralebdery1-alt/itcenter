param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Message
)

# ينشر التعديلات إلى GitHub ثم يفعّلها على خادم Contabo بأمر واحد.
# المفتاح والتنفيذ يبقيان على حاسبتك — أنت من يشغّل هذا السكربت.

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

$server = "root@185.218.124.236"
$remoteDeploy = "bash /var/www/itcenterstore/scripts/deploy_server.sh"

Write-Host "== 1/2: النشر إلى GitHub (فحص + اختبار + رفع) ==" -ForegroundColor Cyan
& "$PSScriptRoot\publish.ps1" -Message $Message -PrivateRepositoryConfirmed
if ($LASTEXITCODE -ne 0) {
    throw "فشل النشر إلى GitHub — لم يُلمس الخادم."
}

Write-Host ""
Write-Host "== 2/2: التفعيل على خادم Contabo (نسخة احتياطية + تحديث + إعادة تشغيل) ==" -ForegroundColor Cyan
ssh $server $remoteDeploy
if ($LASTEXITCODE -ne 0) {
    throw "فشل التفعيل على الخادم — راجع الرسالة أعلاه (الموقع لم يتغيّر إن فشل الفحص)."
}

Write-Host ""
Write-Host "تم النشر والتفعيل بنجاح." -ForegroundColor Green
