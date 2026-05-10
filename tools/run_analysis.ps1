# Run analysis (fast path) and poll status
$body = '{"file_id":"15f0d51c93872b9a","time_resolution":"hour","compute_communities":false}'
Write-Output "Starting analyze POST..."
$an = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/analyze' -Method Post -Body $body -ContentType 'application/json'
Write-Output "Analyze response:`n$($an | ConvertTo-Json -Depth 5)"
$taskId = $an.task_id
Write-Output "Task ID: $taskId"
for ($i=0; $i -lt 20; $i++) {
    try {
        $status = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/analysis/$taskId" -Method Get -ErrorAction Stop
        Write-Output ("Poll {0}: {1}" -f $i, ($status | ConvertTo-Json -Depth 5))
        if ($status.status -eq 'completed') { break }
    } catch {
        Write-Output ("Poll {0}: request failed: {1}" -f $i, $_.Exception.Message)
    }
    Start-Sleep -Seconds 2
}
Write-Output "Requesting communities endpoint..."
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/analysis/$taskId/communities" -Method Get -ErrorAction Stop
    Write-Output "Communities response (200):`n$($resp | ConvertTo-Json -Depth 5)"
} catch {
    # Try to extract the raw response status and content
    if ($_.Exception.Response -ne $null) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $body = $reader.ReadToEnd()
        Write-Output "Communities endpoint returned error or 202: $body"
    } else {
        Write-Output "Communities request failed: $_"
    }
}
