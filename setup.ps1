$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
python -c "import sys; assert sys.version_info[:2] == (3, 11), 'Please install Python 3.11 and run setup again'"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 is required.' }

# Export public Windows trust certificates locally; never commit this bundle.
python -c "import ssl,pathlib; certs=[ssl.DER_cert_to_PEM_cert(c) for store in ['ROOT','CA'] for c,e,t in ssl.enum_certificates(store) if e=='x509_asn']; pathlib.Path('windows-ca.pem').write_text(''.join(certs),encoding='ascii')"
if ($LASTEXITCODE -ne 0) { throw 'Could not create the local certificate bundle.' }
python -m pip install --cert windows-ca.pem --target tools -r requirements-tools.txt
if ($LASTEXITCODE -ne 0) { throw 'Video tool installation failed.' }
if (-not (Test-Path -LiteralPath '.venv-vieneu/Scripts/python.exe')) {
    python -m venv .venv-vieneu
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the VieNeu environment.' }
}
& ./.venv-vieneu/Scripts/python.exe -m pip install --cert windows-ca.pem -r requirements-vieneu.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'VieNeu installation failed.' }
Write-Host 'Ready. Open BAT-STUDIO.bat to start Hanzi Studio.'
