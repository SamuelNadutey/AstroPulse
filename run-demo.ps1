param(
    [ValidateSet("calm_week", "drift_day6", "fever_blackout", "isolation_mood")]
    [string]$Scenario = "drift_day6",
    [string]$Address = "127.0.0.1:8000",
    [switch]$ResetDemo
)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    $python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
            throw "Python 3 is required. Install Python, then run this script again."
        }
        & py -3 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create the local Python environment." }
    }
    & $python -c "import django, numpy" *> $null
    if ($LASTEXITCODE -ne 0) {
        & $python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw "Could not install AstroPulse dependencies." }
    }

    & $python manage.py migrate
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }

    $demoExists = & $python manage.py shell -c "from core.models import CrewMember; print(CrewMember.objects.filter(name='Demo crew (SIMULATED)').exists())"
    if ($LASTEXITCODE -ne 0) { throw "Could not check for existing demo data." }
    if ($demoExists -notcontains "True" -or $ResetDemo) {
        $seedArgs = @("manage.py", "seed_demo", "--scenario", $Scenario)
        if ($demoExists -contains "True") { $seedArgs += "--reset" }
        & $python @seedArgs
        if ($LASTEXITCODE -ne 0) { throw "Could not load SIMULATED demo data." }
    }

    & $python manage.py runserver $Address
}
finally {
    Pop-Location
}
