# --- Config ---
$sshKey   = "$env:USERPROFILE\.ssh\id_ed25519"
$podIP    = "213.173.107.140"    # update if RunPod gives a new IP
$podPort  = 29705                # update if RunPod gives a new port
$localPort  = 8000
$remotePort = 8000

# --- Step 1: Start SSH tunnel in background ---
Write-Host "Starting SSH tunnel to $podIP:$podPort..."
Start-Process -NoNewWindow -FilePath "ssh.exe" -ArgumentList @(
    "-i", $sshKey,
    "-p", $podPort,
    "-L", "$($localPort):127.0.0.1:$($remotePort)",
    "root@$podIP",
    "-N"
)

Start-Sleep -Seconds 2  # give tunnel time to connect

# --- Step 2: Test health endpoint ---
Write-Host "Testing pod health..."
try {
    $response = Invoke-RestMethod "http://localhost:$localPort/health"
    if ($response.ok -eq $true) {
        Write-Host "✅ Pod is healthy! Whisper model: $($response.whisper_model) Device: $($response.device)"
        
        # --- Step 3: Run tiny_client ---
        Set-Location "C:\Users\mrart\time-travel-phone\tiny_client"
        Write-Host "Launching tiny_client..."
        py -3.8 client.py
    }
    else {
        Write-Host "❌ Pod health check failed: $response"
    }
}
catch {
    Write-Host "❌ Could not reach pod health endpoint."
}
