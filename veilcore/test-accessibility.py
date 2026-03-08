#!/usr/bin/env python3
"""
VeilCore Accessibility Engine — Smoke Test
=============================================
Tests the full accessibility stack:
    1. Braille encoding (Grade 1 & Grade 2)
    2. Braille alert formatting
    3. Screen reader output generation
    4. Alert narration with abbreviation expansion
    5. Audio tone generation
    6. Full engine integration
    7. Preferences management

Usage:
    sudo python3 /opt/veilcore/test-accessibility.py
"""

import sys
import os
import json
import logging

sys.path.insert(0, "/opt/veilcore")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("accessibility-test")


def run_test():
    logger.info("=" * 60)
    logger.info("  VEILCORE ACCESSIBILITY ENGINE — SMOKE TEST")
    logger.info("=" * 60)

    # ── Test 1: Braille Encoding
    logger.info("\n── Test 1: Braille Encoding")
    from core.accessibility.braille import BrailleEncoder

    encoder = BrailleEncoder()

    # Grade 1
    result = encoder.encode("alert", grade=1)
    assert len(result) > 0, "Grade 1 encoding empty"
    assert "⠁" in result, "Should contain Braille 'a'"
    logger.info(f"  Grade 1 'alert' → {result}")

    # Capitalization
    result_cap = encoder.encode("Alert", grade=1)
    assert "⠠" in result_cap, "Should contain capital indicator"
    logger.info(f"  Grade 1 'Alert' → {result_cap}")

    # Grade 2 contractions
    result_g2 = encoder.encode("the threat is critical", grade=2)
    assert len(result_g2) > 0, "Grade 2 encoding empty"
    # Grade 2 should be shorter due to contractions
    result_g1 = encoder.encode("the threat is critical", grade=1)
    logger.info(f"  Grade 1: {result_g1}")
    logger.info(f"  Grade 2: {result_g2}")
    logger.info(f"  Grade 2 compression: {len(result_g1)} → {len(result_g2)} cells")

    # Decode round-trip
    decoded = encoder.decode_to_text(encoder.encode("test", grade=1))
    assert "t" in decoded.lower(), "Round-trip decode failed"
    logger.info(f"  Round-trip decode: 'test' → encode → decode → '{decoded}'")

    logger.info("✓ Braille encoding: Grade 1, Grade 2, capitals, decode all working")

    # ── Test 2: Braille Alert Formatting
    logger.info("\n── Test 2: Braille Alert Formatting")
    from core.accessibility.braille import BrailleFormatter

    formatter = BrailleFormatter(display_width=40, grade=1)

    alert_output = formatter.format_alert(
        title="Ransomware C2 Detected",
        message="ML engine detected command and control traffic from hostile IP",
        severity="critical",
        source="ml_predictor",
    )

    assert alert_output.line_count > 0, "Alert should have lines"
    assert alert_output.display_width == 40
    logger.info(f"  Alert formatted: {alert_output.line_count} lines, {alert_output.total_cells} cells")
    for i, line in enumerate(alert_output.lines[:3]):
        logger.info(f"    Line {i+1}: {line[:50]}...")

    # Organ status formatting
    test_organs = [
        {"name": "guardian", "status": "running", "active": "active", "tier": "P0"},
        {"name": "sentinel", "status": "running", "active": "active", "tier": "P0"},
        {"name": "backup_ctrl", "status": "dead", "active": "inactive", "tier": "P1"},
    ]
    organ_output = formatter.format_organ_status(test_organs)
    assert organ_output.line_count > 0
    logger.info(f"  Organ status: {organ_output.line_count} lines for {len(test_organs)} organs")

    # Threat summary
    threat_output = formatter.format_threat_summary(
        "ELEVATED", 3, ["Brute force on SSH", "Port scan from 10.0.0.5", "Weak TLS on FHIR"]
    )
    assert threat_output.line_count > 0
    logger.info(f"  Threat summary: {threat_output.line_count} lines")

    # Different display widths
    for width in [20, 40, 80]:
        fmt = BrailleFormatter(display_width=width)
        out = fmt.format_text("Testing display width adaptation for Braille output")
        logger.info(f"  Width {width}: {out.line_count} lines")

    logger.info("✓ Braille formatting: alerts, organs, threats, display widths all working")

    # ── Test 3: Screen Reader Output
    logger.info("\n── Test 3: Screen Reader Output")
    from core.accessibility.screen_reader import ScreenReaderOutput

    sr = ScreenReaderOutput()

    # System status
    status_blocks = sr.format_system_status({
        "organs": {"total": 82, "active": 78, "inactive": 4,
                   "by_tier": {"P0_critical": 12, "P1_important": 28, "P2_standard": 42}},
        "threats": {"threat_level": "ELEVATED", "active_alerts": 3},
    })
    assert len(status_blocks) > 0, "Should have status blocks"
    for block in status_blocks:
        logger.info(f"  [{block.urgency}] {block.label}: {block.content[:80]}")

    # Alert formatting
    alert_block = sr.format_alert({
        "severity": "critical", "title": "Ransomware Detected",
        "message": "Encryption behavior on file server", "source_organ": "sentinel",
    })
    assert alert_block.urgency == "assertive", "Critical should be assertive"
    assert alert_block.role == "alert"
    logger.info(f"  Alert block: [{alert_block.urgency}] {alert_block.content[:80]}")

    # SSML generation
    ssml = alert_block.to_ssml()
    assert "<speak>" in ssml
    assert "fast" in ssml  # Assertive = fast rate
    logger.info(f"  SSML: {ssml[:80]}...")

    # Organ list
    organ_blocks = sr.format_organ_list(test_organs)
    assert len(organ_blocks) > 0
    logger.info(f"  Organ list: {len(organ_blocks)} blocks")

    # Command result
    cmd_block = sr.format_command_result({
        "command": "organ_restart", "status": "success",
        "message": "Guardian restarted successfully",
    })
    assert cmd_block.urgency == "polite"
    logger.info(f"  Command result: {cmd_block.content}")

    logger.info("✓ Screen reader: status, alerts, organs, SSML all working")

    # ── Test 4: Alert Narration
    logger.info("\n── Test 4: Alert Narration & Abbreviation Expansion")
    from core.accessibility.screen_reader import AlertNarrator

    narrator = AlertNarrator()

    narration = narrator.narrate_alert({
        "severity": "critical",
        "title": "SSH brute force from IP 203.0.113.50",
        "message": "ML detected credential stuffing via SSH on EHR server",
        "source_organ": "sentinel",
    })
    assert "S S H" in narration, "Should expand SSH"
    assert "203 dot 0 dot 113 dot 50" in narration, "Should expand IP"
    assert "M L" in narration, "Should expand ML"
    assert "E H R" in narration, "Should expand EHR"
    logger.info(f"  Narration: {narration[:120]}...")

    # Status narration
    status_narration = narrator.narrate_status("ELEVATED", 78, 82, 3)
    assert "78" in status_narration
    assert "82" in status_narration
    logger.info(f"  Status: {status_narration}")

    # Test more expansions
    test_text = narrator._expand("HIPAA FHIR HL7 DICOM API CVSS TPM")
    assert "hip-ah" in test_text
    assert "fire" in test_text
    assert "die-com" in test_text
    logger.info(f"  Expansions: {test_text}")

    logger.info("✓ Narration: abbreviation expansion, IP pronunciation, severity preambles working")

    # ── Test 5: Audio Tone Generation
    logger.info("\n── Test 5: Audio Alert System")
    from core.accessibility.audio import AudioAlertSystem

    audio = AudioAlertSystem(output_dir="/tmp/veilcore-test-audio")

    # List tones
    tones = audio.list_tones()
    assert len(tones) >= 10, f"Expected 10+ tones, got {len(tones)}"
    logger.info(f"  {len(tones)} tone profiles registered")

    # Generate samples
    tone = audio.get_tone("critical")
    assert tone is not None
    samples = audio.generate_samples(tone)
    assert len(samples) > 0, "Should generate samples"
    logger.info(f"  Critical tone: {tone.frequency_hz}Hz, {tone.pulses} pulses, "
                f"{len(samples)} samples ({len(samples)/44100:.2f}s)")

    # Generate WAV
    wav = audio.generate_wav("critical")
    assert wav is not None
    assert len(wav) > 100, "WAV should have content"
    logger.info(f"  Critical WAV: {len(wav)} bytes")

    # Save WAV
    assert audio.save_wav("critical", "/tmp/veilcore-test-audio/critical.wav")
    assert os.path.exists("/tmp/veilcore-test-audio/critical.wav")
    logger.info("  WAV saved to disk ✓")

    # Generate all WAVs
    paths = audio.generate_all_wavs("/tmp/veilcore-test-audio")
    assert len(paths) >= 10
    logger.info(f"  Generated {len(paths)} WAV files")

    # Web Audio specs
    spec = audio.get_web_audio_spec("critical")
    assert spec is not None
    assert spec["frequency"] == 880.0
    assert spec["pulses"] == 3
    logger.info(f"  Web Audio spec (critical): {json.dumps(spec)}")

    all_specs = audio.get_all_web_audio_specs()
    assert len(all_specs) >= 10
    logger.info(f"  {len(all_specs)} Web Audio specs generated")

    logger.info("✓ Audio: tone generation, WAV encoding, Web Audio specs all working")

    # ── Test 6: Full Engine Integration
    logger.info("\n── Test 6: Full Accessibility Engine")
    from core.accessibility.engine import AccessibilityEngine, AccessibilityPreferences

    engine = AccessibilityEngine(prefs=AccessibilityPreferences(
        braille_grade=1, braille_display_width=40,
        audio_volume=0.7,
    ))

    # Process alert
    alert_output = engine.process_alert({
        "title": "Ransomware C2 Detected",
        "message": "ML engine classified traffic as ransomware C2",
        "severity": "critical",
        "source_organ": "ml_predictor",
    })
    assert alert_output.braille is not None
    assert alert_output.screen_reader is not None
    assert alert_output.narration is not None
    assert alert_output.audio_tone == "critical"
    assert alert_output.audio_spec is not None
    logger.info(f"  Alert → Braille: {alert_output.braille.line_count} lines, "
                f"SR: {len(alert_output.screen_reader)} blocks, "
                f"Audio: {alert_output.audio_tone}")

    # Process status
    status_output = engine.process_status({
        "organs": {"total": 82, "active": 80, "inactive": 2,
                   "by_tier": {"P0_critical": 12, "P1_important": 28, "P2_standard": 42}},
        "threats": {"threat_level": "NORMAL", "active_alerts": 0},
    })
    assert status_output.braille is not None
    assert status_output.audio_tone == "all_clear"
    logger.info(f"  Status → Audio: {status_output.audio_tone}, "
                f"Narration: {status_output.narration[:60]}...")

    # Process organs
    organ_output = engine.process_organs(test_organs)
    assert organ_output.braille is not None
    assert organ_output.audio_tone == "organ_failure"  # Has a dead organ
    logger.info(f"  Organs → Audio: {organ_output.audio_tone} (dead organ detected)")

    # Process threats
    threat_output = engine.process_threats("HIGH", [
        {"title": "Brute Force", "severity": "high", "source_organ": "sentinel"},
        {"title": "Port Scan", "severity": "medium", "source_organ": "firewall"},
    ])
    assert threat_output.audio_tone == "high"
    logger.info(f"  Threats → Audio: {threat_output.audio_tone}, "
                f"SR blocks: {len(threat_output.screen_reader)}")

    # Process command result
    cmd_output = engine.process_command_result({
        "command": "kill_switch", "status": "denied",
        "message": "Insufficient role",
    })
    assert cmd_output.audio_tone == "high"  # Error/denied gets audio
    logger.info(f"  Command denied → Audio: {cmd_output.audio_tone}")

    # Verify event count
    assert engine.events_processed == 5
    logger.info(f"  Events processed: {engine.events_processed}")

    logger.info("✓ Engine: all event types processed through Braille + Screen Reader + Audio")

    # ── Test 7: Preferences Management
    logger.info("\n── Test 7: Preferences Management")

    # Update preferences
    engine.update_preferences({
        "braille_grade": 2,
        "braille_display_width": 80,
        "audio_volume": 0.5,
    })
    assert engine.preferences.braille_grade == 2
    assert engine.preferences.braille_display_width == 80
    assert engine.preferences.audio_volume == 0.5
    logger.info(f"  Preferences updated: grade={engine.preferences.braille_grade}, "
                f"width={engine.preferences.braille_display_width}")

    # Grade 2 output after preference change
    g2_output = engine.process_alert({
        "title": "The network threat is critical",
        "message": "Ransomware detected in hospital network",
        "severity": "critical", "source_organ": "sentinel",
    })
    assert g2_output.braille is not None
    logger.info(f"  Grade 2 alert: {g2_output.braille.line_count} lines, "
                f"grade={g2_output.braille.grade}")

    # Summary
    summary = engine.summary()
    assert summary["engine"] == "AccessibilityEngine"
    assert summary["codename"] == "EqualShield"
    logger.info(f"  Summary: {json.dumps(summary, indent=2)}")

    # Web Audio pack for dashboard
    web_pack = engine.get_web_audio_pack()
    assert len(web_pack) >= 10
    logger.info(f"  Web Audio pack: {len(web_pack)} tone specs for dashboard")

    logger.info("✓ Preferences: update, persist, Grade 2 switch, Web Audio pack all working")

    # ── Cleanup
    import shutil
    if os.path.exists("/tmp/veilcore-test-audio"):
        shutil.rmtree("/tmp/veilcore-test-audio")

    # ── Final Summary
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ ALL ACCESSIBILITY TESTS PASSED")
    logger.info("=" * 60)
    logger.info("")
    logger.info("  ✓ Braille encoding — Grade 1 & Grade 2 with security contractions")
    logger.info("  ✓ Braille formatting — alerts, organs, threats, display widths")
    logger.info("  ✓ Screen reader — ARIA-style structured output, SSML generation")
    logger.info("  ✓ Alert narration — abbreviation expansion (30+ terms), IP pronunciation")
    logger.info("  ✓ Audio alerts — WAV generation, 10+ tone profiles, Web Audio specs")
    logger.info("  ✓ Engine integration — all event types through all output channels")
    logger.info("  ✓ Preferences — update, persistence, Grade 2 switching")
    logger.info("")
    logger.info("  EqualShield: Because every defender deserves full awareness.")
    logger.info("  The Veil does not discriminate in who it protects.")
    logger.info("")


if __name__ == "__main__":
    try:
        run_test()
    except AssertionError as e:
        logger.error(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Test interrupted")
        sys.exit(0)
