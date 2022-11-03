Function  pause($message)
{
    # check if running powershell ISE
    if ($psISE)
    {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show("$message")
    }
    else
    {
        Write-Host "$message" -ForegroundColor Yellow
        $x = $host.ui.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}


$pyPath = "c:/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/python.exe" 
Start-Process -Wait -FilePath $pyPath -ArgumentList '-m', 'unittest', '-v', 'test/unit_tests.py'
pause("unit tests ran, press any key to exit.")