#!/bin/bash

ORGANS_DIR="/opt/veil_os/organs"
OUTPUT="/opt/veil_os/supervisor/organs.json"

# --- EPIC‑grade glyph assignment ---
assign_glyph() {
    case "$1" in
        sentinel|guardian|insider_threat|auto_lockdown) echo "🛡️" ;;
        zero_trust|rbac|keystore|session) echo "🔐" ;;
        firewall) echo "🧱" ;;
        telemetry|monitor|signal) echo "📡" ;;
        analytics|dashboard|weaver|flux) echo "📊" ;;
        audit|logger|journal) echo "📜" ;;
        forensic) echo "🧪" ;;
        gateway|relay|socket) echo "🔌" ;;
        router|switch|dispatcher) echo "🧭" ;;
        harbor|spooler) echo "🗄️" ;;
        hospital|station|portal) echo "🏥" ;;
        daemon|daemonizer|driver|loader|patcher|synth|cortex|hatchery) echo "⚙️" ;;
        quarantine) echo "🚫" ;;
        rollback) echo "↩️" ;;
        scheduler) echo "⏱️" ;;
        mirror) echo "🪞" ;;
        matrix|fabric) echo "🌐" ;;
        *) echo "🫀" ;; # fallback organ glyph
    esac
}

# --- Clinical summary assignment ---
assign_summary() {
    case "$1" in
        sentinel) echo "Primary real-time security enforcement organ responsible for blocking threats and maintaining system integrity." ;;
        guardian) echo "Core identity and access enforcement organ providing continuous protection of authentication and authorization flows." ;;
        zero_trust) echo "Zero Trust enforcement organ ensuring least-privilege access, continuous verification, and boundaryless security posture." ;;
        rbac) echo "Role-based access control organ defining identity lineage, privilege boundaries, and clinical-grade authorization rules." ;;
        insider_threat) echo "Behavioral monitoring organ detecting anomalous internal activity and preventing privilege misuse." ;;
        auto_lockdown) echo "Automated lockdown organ that isolates or restricts system components during high-risk events." ;;
        firewall) echo "Network boundary protection organ responsible for filtering, blocking, and inspecting traffic." ;;
        telemetry) echo "Collects, streams, and forwards real-time system metrics for monitoring and performance oversight." ;;
        analytics) echo "Aggregates and analyzes operational and clinical data for decision support." ;;
        audit) echo "Maintains immutable audit trails for compliance and forensic review." ;;
        forensic) echo "Performs deep inspection and evidence preservation for post-incident analysis." ;;
        dispatcher) echo "Routes internal events and operational messages between organs." ;;
        gateway) echo "Provides controlled ingress and egress points for data exchange with external systems." ;;
        router) echo "Directs internal traffic flows between organs." ;;
        weaver) echo "Correlates multi-organ data streams into unified operational insights." ;;
        hospital) echo "Provides clinical context integration for hospital workflows." ;;
        dashboard) echo "Renders operational dashboards for real-time visibility into organ health." ;;
        cortex) echo "Coordinates multi-organ logic, decision routing, and internal orchestration." ;;
        daemon|daemonizer) echo "Background service organ responsible for continuous internal tasks." ;;
        entropy) echo "Generates cryptographically safe entropy for secure operations." ;;
        fabric) echo "Internal communication fabric enabling structured data exchange." ;;
        flux) echo "Manages dynamic system state transitions and ensures consistent behavior." ;;
        harbor) echo "Secure storage organ for sensitive operational artifacts." ;;
        hatchery) echo "Initializes and prepares new organ processes for safe startup." ;;
        journal) echo "Maintains structured logs of internal events." ;;
        keystore) echo "Stores and manages cryptographic keys for secure communication." ;;
        loader) echo "Loads organ modules and configurations into the runtime environment." ;;
        logger) echo "Captures structured logs from organs and forwards them to audit systems." ;;
        matrix) echo "Provides multidimensional data structures for complex operations." ;;
        mirror) echo "Maintains synchronized replicas of critical data for resilience." ;;
        monitor) echo "Observes organ health and forwards alerts to sentinel and telemetry." ;;
        patcher) echo "Applies updates and configuration changes safely." ;;
        portal) echo "Provides clinical-facing interfaces for hospital workflows." ;;
        quarantine) echo "Isolates compromised components to prevent harmful propagation." ;;
        relay) echo "Transfers messages and data between organs and external systems." ;;
        rollback) echo "Restores previous system states after failed updates." ;;
        scheduler) echo "Schedules recurring tasks and maintenance routines." ;;
        session) echo "Manages user and system sessions securely." ;;
        signal) echo "Handles internal signaling and event propagation." ;;
        socket) echo "Provides communication channels for organ interaction." ;;
        spooler) echo "Queues and processes deferred tasks." ;;
        station) echo "Provides clinical station logic for operational endpoints." ;;
        switch) echo "Handles routing decisions between organ communication paths." ;;
        synth) echo "Synthesizes multi-source data into structured outputs." ;;
        *) echo "Core operational organ supporting Veil OS functionality." ;;
    esac
}

# --- Tier assignment ---
assign_tier() {
    case "$1" in
        sentinel|guardian|zero_trust|rbac|insider_threat|auto_lockdown|firewall)
            echo "P0"
            ;;
        analytics|telemetry|audit|forensic|dispatcher|gateway|router|weaver|hospital|dashboard)
            echo "P1"
            ;;
        *)
            echo "P2"
            ;;
    esac
}

# --- Begin JSON output ---
echo "{" > "$OUTPUT"
echo '  "organs": [' >> "$OUTPUT"

FIRST=1

for organ in "$ORGANS_DIR"/*; do
    [ -d "$organ" ] || continue
    name=$(basename "$organ")

    glyph=$(assign_glyph "$name")
    summary=$(assign_summary "$name")
    tier=$(assign_tier "$name")

    unit_file="/etc/systemd/system/veil-$name.service"
    if [ -f "$unit_file" ]; then
        unit="veil-$name.service"
    else
        unit="null"
    fi

    if [ -f "$organ/run.sh" ]; then
        runnable="true"
    else
        runnable="false"
    fi

    if [ $FIRST -eq 0 ]; then
        echo "," >> "$OUTPUT"
    fi
    FIRST=0

    echo "    {" >> "$OUTPUT"
    echo "      \"name\": \"$name\"," >> "$OUTPUT"
    echo "      \"tier\": \"$tier\"," >> "$OUTPUT"
    echo "      \"glyph\": \"$glyph\"," >> "$OUTPUT"
    echo "      \"summary\": \"$summary\"," >> "$OUTPUT"
    echo "      \"path\": \"$organ\"," >> "$OUTPUT"
    echo "      \"unit\": $([ "$unit" = "null" ] && echo null || echo "\"$unit\"")," >> "$OUTPUT"
    echo "      \"runnable\": $runnable" >> "$OUTPUT"
    echo "    }" >> "$OUTPUT"
done

echo "" >> "$OUTPUT"
echo "  ]" >> "$OUTPUT"
echo "}" >> "$OUTPUT"

echo "Organ manifest generated at $OUTPUT"
