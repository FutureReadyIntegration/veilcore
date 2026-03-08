"""
THE RIGHTEOUSNESS ENGINE
Veil OS - Ethical Decision Framework

Built by Marlon Ástin Williams

"Righteousness over routine"
Every security decision is evaluated not just for legality,
but for RIGHTNESS.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List
import json


class DecisionGlyph(Enum):
    """Symbolic representation of ethical decisions"""
    SHIELD = "[SHIELD]"
    SWORD = "[SWORD]"
    SCALE = "[SCALE]"
    HEART = "[HEART]"
    SKULL = "[SKULL]"
    LOCK = "[LOCK]"
    KEY = "[KEY]"
    WARNING = "[WARNING]"
    CROSS = "[CROSS]"
    EYE = "[EYE]"
    FIRE = "[FIRE]"
    SCROLL = "[SCROLL]"


class RighteousnessLevel(Enum):
    """Ethical categorization of actions"""
    DIVINE = 100
    RIGHTEOUS = 75
    NEUTRAL = 50
    QUESTIONABLE = 25
    EVIL = 0


@dataclass
class Action:
    """An action requiring ethical evaluation"""
    actor: str
    intent: str
    target: str
    context: Dict
    timestamp: str
    
    threatens_patient_safety: bool = False
    serves_healing: bool = False
    requires_sovereignty: bool = False
    has_consent: bool = False
    is_transparent: bool = True


@dataclass
class EthicalDecision:
    """The verdict of righteousness evaluation"""
    action: Action
    righteousness_level: RighteousnessLevel
    verdict: str
    glyph: DecisionGlyph
    reasoning: str
    affirmation: str
    timestamp: str
    
    def to_chronicle_entry(self) -> Dict:
        """Convert to Chronicle ledger format"""
        return {
            "timestamp": self.timestamp,
            "glyph": self.glyph.value,
            "actor": self.action.actor,
            "intent": self.action.intent,
            "target": self.action.target,
            "verdict": self.verdict,
            "righteousness": self.righteousness_level.name,
            "reasoning": self.reasoning,
            "affirmation": self.affirmation,
            "meaning": f"{self.glyph.value} {self.affirmation}"
        }


class RighteousnessEngine:
    """
    The ethical core of Veil OS
    
    Evaluates every security decision through the lens of:
    - Sovereignty: Does this respect user control?
    - Transparency: Is this decision visible and understandable?
    - Consent: Has explicit permission been given?
    - Righteousness: Is this action morally correct?
    """
    
    def __init__(self, chronicle_path: str = "/opt/veil_os/ledger.json"):
        self.chronicle_path = Path(chronicle_path)
        self.principles = {
            'sovereignty': True,
            'transparency': True,
            'consent': True,
            'righteousness': True
        }
    
    def evaluate(self, action: Action) -> EthicalDecision:
        """
        The primary evaluation function
        
        This is where ethics meet execution.
        Every action passes through here.
        """
        timestamp = datetime.now().isoformat()
        
        if action.threatens_patient_safety:
            return self._block_with_extreme_prejudice(action, timestamp)
        
        if action.serves_healing:
            return self._permit_and_protect(action, timestamp)
        
        if action.requires_sovereignty and not action.has_consent:
            return self._request_sovereign_decision(action, timestamp)
        
        if not action.is_transparent:
            return self._deny_obscure_action(action, timestamp)
        
        return self._permit_neutral_action(action, timestamp)
    
    def _block_with_extreme_prejudice(self, action: Action, timestamp: str) -> EthicalDecision:
        """When patient safety is threatened, act decisively"""
        return EthicalDecision(
            action=action,
            righteousness_level=RighteousnessLevel.EVIL,
            verdict="DENY",
            glyph=DecisionGlyph.SKULL,
            reasoning="This action threatens patient safety and must be stopped immediately",
            affirmation="I STAND BETWEEN CHAOS AND THOSE I PROTECT",
            timestamp=timestamp
        )
    
    def _permit_and_protect(self, action: Action, timestamp: str) -> EthicalDecision:
        """When action serves healing, enable and guard it"""
        return EthicalDecision(
            action=action,
            righteousness_level=RighteousnessLevel.DIVINE,
            verdict="PERMIT",
            glyph=DecisionGlyph.HEART,
            reasoning="This action serves the healing mission and shall be protected",
            affirmation="IN SERVICE OF LIFE, ACCESS GRANTED",
            timestamp=timestamp
        )
    
    def _request_sovereign_decision(self, action: Action, timestamp: str) -> EthicalDecision:
        """When sovereignty is required, defer to the user"""
        return EthicalDecision(
            action=action,
            righteousness_level=RighteousnessLevel.QUESTIONABLE,
            verdict="ASK_USER",
            glyph=DecisionGlyph.SCALE,
            reasoning="This action requires sovereign consent - user must decide",
            affirmation="SOVEREIGNTY HONORED - AWAITING YOUR COMMAND",
            timestamp=timestamp
        )
    
    def _deny_obscure_action(self, action: Action, timestamp: str) -> EthicalDecision:
        """When transparency is violated, deny access"""
        return EthicalDecision(
            action=action,
            righteousness_level=RighteousnessLevel.QUESTIONABLE,
            verdict="DENY",
            glyph=DecisionGlyph.WARNING,
            reasoning="This action lacks transparency and cannot proceed",
            affirmation="HIDDEN INTENT IS DENIED INTENT",
            timestamp=timestamp
        )
    
    def _permit_neutral_action(self, action: Action, timestamp: str) -> EthicalDecision:
        """Routine technical operations with no ethical weight"""
        return EthicalDecision(
            action=action,
            righteousness_level=RighteousnessLevel.NEUTRAL,
            verdict="PERMIT",
            glyph=DecisionGlyph.KEY,
            reasoning="Technical operation with no ethical concerns",
            affirmation="PASSAGE GRANTED",
            timestamp=timestamp
        )
    
    def log_to_chronicle(self, decision: EthicalDecision):
        """Record this decision in Chronicle"""
        entry = decision.to_chronicle_entry()
        
        ledger = []
        if self.chronicle_path.exists():
            try:
                ledger = json.loads(self.chronicle_path.read_text())
                if not isinstance(ledger, list):
                    ledger = []
            except:
                ledger = []
        
        ledger.append(entry)
        
        if len(ledger) > 10000:
            ledger = ledger[-10000:]
        
        self.chronicle_path.write_text(json.dumps(ledger, indent=2))
    
    def evaluate_and_log(self, action: Action) -> EthicalDecision:
        """Convenience method: evaluate and log in one step"""
        decision = self.evaluate(action)
        self.log_to_chronicle(decision)
        return decision
    
    def get_righteousness_report(self) -> Dict:
        """Generate a report on ethical decisions made"""
        if not self.chronicle_path.exists():
            return {"total": 0, "by_level": {}, "by_verdict": {}}
        
        ledger = json.loads(self.chronicle_path.read_text())
        
        report = {
            "total": len(ledger),
            "by_level": {},
            "by_verdict": {},
            "recent_affirmations": []
        }
        
        for entry in ledger:
            level = entry.get('righteousness', 'UNKNOWN')
            verdict = entry.get('verdict', 'UNKNOWN')
            
            report['by_level'][level] = report['by_level'].get(level, 0) + 1
            report['by_verdict'][verdict] = report['by_verdict'].get(verdict, 0) + 1
        
        report['recent_affirmations'] = [
            entry['affirmation'] for entry in ledger[-5:]
        ]
        
        return report


righteousness_engine = RighteousnessEngine()


if __name__ == "__main__":
    healing_action = Action(
        actor="Dr. Smith",
        intent="Access patient vitals for emergency surgery",
        target="Patient Record 12345",
        context={"emergency": True, "surgical_suite": "OR-3"},
        timestamp=datetime.now().isoformat(),
        serves_healing=True,
        has_consent=True
    )
    
    decision1 = righteousness_engine.evaluate_and_log(healing_action)
    print(f"\n{decision1.glyph.value} DECISION: {decision1.verdict}")
    print(f"Affirmation: {decision1.affirmation}")
    
    threat_action = Action(
        actor="Unknown Process",
        intent="Mass deletion of patient records",
        target="Database: PatientRecords",
        context={"source_ip": "192.168.1.666"},
        timestamp=datetime.now().isoformat(),
        threatens_patient_safety=True
    )
    
    decision2 = righteousness_engine.evaluate_and_log(threat_action)
    print(f"\n{decision2.glyph.value} DECISION: {decision2.verdict}")
    print(f"Affirmation: {decision2.affirmation}")
    
    sovereign_action = Action(
        actor="Admin User",
        intent="Modify firewall rules",
        target="Veil Firewall Configuration",
        context={"action": "open_port_3389"},
        timestamp=datetime.now().isoformat(),
        requires_sovereignty=True,
        has_consent=False
    )
    
    decision3 = righteousness_engine.evaluate_and_log(sovereign_action)
    print(f"\n{decision3.glyph.value} DECISION: {decision3.verdict}")
    print(f"Affirmation: {decision3.affirmation}")
    
    print("\n" + "="*50)
    print("RIGHTEOUSNESS REPORT")
    print("="*50)
    report = righteousness_engine.get_righteousness_report()
    print(json.dumps(report, indent=2))
