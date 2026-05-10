$task = '15f0d51c93872b9a_1776471348'
for ($i=0; $i -lt 60; $i++) {
    try {
        $s = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/analysis/$task" -Method Get -ErrorAction Stop
        Write-Output ("Poll {0}: {1}" -f $i, ($s | ConvertTo-Json -Depth 4))
        if ($s.status -eq 'completed') { break }
    } catch {
        Write-Output ("Poll {0}: request failed: {1}" -f $i, $_.Exception.Message)
    }
    Start-Sleep -Seconds 3
}
