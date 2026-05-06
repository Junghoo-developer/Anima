param(
    [string]$Database = "neo4j",
    [string]$BackupDir = "backups/r7_premigration",
    [switch]$RunMigration,
    [switch]$RunVerify
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

Write-Host "[R7] Creating Neo4j dump backup for database '$Database' in '$BackupDir'..."
neo4j-admin database dump $Database --to-path=$BackupDir

if ($RunMigration) {
    Write-Host "[R7] Backup completed. Running tools/r7_migration.cypher..."
    cypher-shell -d $Database -f tools/r7_migration.cypher
}
else {
    Write-Host "[R7] Backup completed. Migration not run. Re-run with -RunMigration after review."
}

if ($RunVerify) {
    Write-Host "[R7] Running tools/r7_verify.cypher..."
    cypher-shell -d $Database -f tools/r7_verify.cypher
}
