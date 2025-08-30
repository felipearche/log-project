param(
    [switch]$Build = $false,
    [string]$Data = "data/synth_tokens.json"
)

if ($Build) {
    docker build -t log-project:latest .
}

$commit = (git rev-parse --short HEAD 2>$null)
if (-not $commit) { $commit = "NA" }
$env:COMMIT = $commit

# If user passed a non-default dataset, override the image CMD and call Python directly
if ($PSBoundParameters.ContainsKey('Data') -and $Data -ne "data/synth_tokens.json") {
    docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
        python src/stream.py `
        --data $Data `
        --mode baseline `
        --sleep_ms 0 `
        --summary-out experiments/summary.csv
} else {
    # Use the image default CMD
    docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest
}

