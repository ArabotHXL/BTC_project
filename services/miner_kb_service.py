# -*- coding: utf-8 -*-

"""
miner_kb_service.py

MinerKnowledgeBaseService:
- Loads KB (JSON) from an unpacked directory OR from a KB zip (auto-unpack).
- Provides:
    - explain_error_code()
    - diagnose(snapshot) -> top matches + playbook/prevention/tuning
- Matching engine:
    - log code/keyword/regex hits + metric rule DSL evaluation (safe eval)
"""

from __future__ import annotations

import ast
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# -----------------------------
# Data models (runtime)
# -----------------------------

@dataclass(frozen=True)
class SignatureHit:
    signature_id: str
    title: str
    category: str
    severity: str
    priority: int
    score: float
    reasons: List[str]
    playbook_id: str
    prevention_id: str
    tuning_id: str

@dataclass
class DiagnosisResult:
    miner_id: str
    model_id: str
    brand: str
    timestamp: str
    top_hits: List[SignatureHit]
    selected: Optional[SignatureHit]
    playbook: Optional[Dict[str, Any]]
    prevention: Optional[Dict[str, Any]]
    tuning: Optional[Dict[str, Any]]
    error_code_explanations: List[Dict[str, Any]]
    confidence: float
    notes: List[str]

# -----------------------------
# Safe metric rule evaluation
# -----------------------------

_ALLOWED_FUNCS = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
}

_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Mod: lambda a, b: a % b,
}

_CMP_OPS = {
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
}

def _safe_eval_expr(expr: str, vars_map: Dict[str, Any]) -> bool:
    """
    Evaluates a very small DSL used in KB metric_rules.
    Supported:
      - AND/OR/NOT (case-insensitive)
      - comparisons, arithmetic + - * / %
      - abs/min/max/round
      - parentheses

    Missing variables -> rule=False (not a match).
    """
    expr = expr.strip()
    if not expr:
        return False

    # Normalize operators
    expr = re.sub(r"\bAND\b", "and", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bOR\b", "or", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bNOT\b", "not", expr, flags=re.IGNORECASE)

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return False

    def ev(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return ev(node.body)

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            if node.id not in vars_map:
                raise KeyError(node.id)
            return vars_map[node.id]

        if isinstance(node, ast.UnaryOp):
            val = ev(node.operand)
            if isinstance(node.op, ast.Not):
                return not bool(val)
            if isinstance(node.op, ast.USub):
                return -val
            if isinstance(node.op, ast.UAdd):
                return +val
            raise ValueError("Unary op not allowed")

        if isinstance(node, ast.BinOp):
            left = ev(node.left)
            right = ev(node.right)
            op = _BIN_OPS.get(type(node.op))
            if op is None:
                raise ValueError("Bin op not allowed")
            return op(left, right)

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.Or):
                for v in node.values:
                    try:
                        if bool(ev(v)):
                            return True
                    except (KeyError, ValueError, TypeError):
                        continue
                return False
            if isinstance(node.op, ast.And):
                for v in node.values:
                    try:
                        if not bool(ev(v)):
                            return False
                    except (KeyError, ValueError, TypeError):
                        return False
                return True
            raise ValueError("Bool op not allowed")

        if isinstance(node, ast.Compare):
            left = ev(node.left)
            for op_node, right_node in zip(node.ops, node.comparators):
                right = ev(right_node)
                op = _CMP_OPS.get(type(op_node))
                if op is None:
                    raise ValueError("Compare op not allowed")
                if not op(left, right):
                    return False
                left = right
            return True

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only simple func calls allowed")
            fn = _ALLOWED_FUNCS.get(node.func.id)
            if fn is None:
                raise ValueError("Function not allowed")
            args = [ev(a) for a in node.args]
            return fn(*args)

        raise ValueError(f"Node not allowed: {type(node).__name__}")

    try:
        return bool(ev(tree))
    except Exception:
        return False


# -----------------------------
# Service
# -----------------------------

class MinerKnowledgeBaseService:
    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.schema = self._load_json("schema.json")
        self.sources = self._load_json("sources.json")
        self.models = self._load_json("models.json")
        self.taxonomy = self._load_json("taxonomy.json")
        self.signatures = self._load_json("signatures.json")
        self.playbooks = {p["playbook_id"]: p for p in self._load_json("playbooks.json")}
        self.preventions = {p["prevention_id"]: p for p in self._load_json("preventions.json")}
        self.tunings = {t["tuning_id"]: t for t in self._load_json("tunings.json")}

        # Load error code dictionaries
        self.error_code_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
        err_dir = self.kb_dir / "error_codes"
        if err_dir.exists():
            for p in err_dir.glob("*.json"):
                data = json.loads(p.read_text(encoding="utf-8"))
                brand = (data.get("brand") or "Unknown").strip().lower()
                self.error_code_map.setdefault(brand, {})
                for e in data.get("entries", []):
                    code_key = str(e.get("code", "")).strip().lower()
                    if code_key:
                        self.error_code_map[brand][code_key] = e

        # Pre-compile regex for signatures
        for s in self.signatures:
            regs = s.get("evidence", {}).get("log_regex", []) or []
            s["_compiled_regex"] = [re.compile(rgx) for rgx in regs if rgx]

    @staticmethod
    def from_zip(kb_zip_path: Path, cache_dir: Path) -> "MinerKnowledgeBaseService":
        """
        Auto-unpack KB zip to cache_dir/<sha256_prefix>/ and load from there.
        """
        cache_dir.mkdir(parents=True, exist_ok=True)
        sha = MinerKnowledgeBaseService._sha256_file(kb_zip_path)[:12]
        target = cache_dir / sha
        if not (target / "schema.json").exists():
            target.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(kb_zip_path, "r") as z:
                z.extractall(target)
        return MinerKnowledgeBaseService(target)

    @staticmethod
    def _sha256_file(p: Path) -> str:
        import hashlib
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _load_json(self, name: str) -> Any:
        p = self.kb_dir / name
        return json.loads(p.read_text(encoding="utf-8"))

    # -------- error code helpers --------

    def explain_error_code(self, brand: str, code: str) -> Optional[Dict[str, Any]]:
        b = (brand or "unknown").strip().lower()
        c = str(code or "").strip().lower()
        if not c:
            return None
        # brand-specific
        if b in self.error_code_map and c in self.error_code_map[b]:
            return self.error_code_map[b][c]
        # fallback: try all brands (helpful if brand unknown)
        for bm in self.error_code_map.values():
            if c in bm:
                return bm[c]
        return None

    # -------- log parsing helpers --------

    _RE_ERROR_TOKEN = re.compile(r"\bERROR_[A-Z0-9_]+\b")
    _RE_SWEEP_CODE = re.compile(r"Sweep\s*error\s*string\s*=\s*([A-Z]:\d+)", re.IGNORECASE)

    def extract_codes_from_logs(self, logs: List[str]) -> List[str]:
        codes: List[str] = []
        for line in logs or []:
            for m in self._RE_ERROR_TOKEN.findall(line or ""):
                codes.append(m.strip())
            for m in self._RE_SWEEP_CODE.findall(line or ""):
                codes.append(m.strip())
            # also treat some known phrases as "codes"
            if re.search(r"Read\s*Temp\s*Sensor\s*Failed", line or "", re.IGNORECASE):
                codes.append("Read Temp Sensor Failed")
            if re.search(r"fail\s*to\s*read\s*pic\s*temp", line or "", re.IGNORECASE):
                codes.append("fail to read pic temp")
        # de-dup preserving order
        seen = set()
        out = []
        for c in codes:
            ck = c.lower()
            if ck not in seen:
                seen.add(ck)
                out.append(c)
        return out

    # -------- matching engine --------

    @staticmethod
    def _localize(obj: Dict[str, Any], fields: List[str], lang: str) -> Dict[str, Any]:
        if lang != 'en':
            return obj
        out = dict(obj)
        for f in fields:
            en_key = f"{f}_en"
            if en_key in out and out[en_key]:
                out[f] = out[en_key]
        return out

    def localize_result(self, diag: "DiagnosisResult", lang: str) -> "DiagnosisResult":
        if lang != 'en':
            return diag

        loc_selected = None
        if diag.selected:
            sig_data = None
            for s in self.signatures:
                if s.get("signature_id") == diag.selected.signature_id:
                    sig_data = s
                    break
            en_title = (sig_data or {}).get("title_en", diag.selected.title) if sig_data else diag.selected.title
            loc_selected = SignatureHit(
                signature_id=diag.selected.signature_id,
                title=en_title,
                category=diag.selected.category,
                severity=diag.selected.severity,
                priority=diag.selected.priority,
                score=diag.selected.score,
                reasons=diag.selected.reasons,
                playbook_id=diag.selected.playbook_id,
                prevention_id=diag.selected.prevention_id,
                tuning_id=diag.selected.tuning_id,
            )

        loc_top_hits = []
        for hit in diag.top_hits:
            sig_data = None
            for s in self.signatures:
                if s.get("signature_id") == hit.signature_id:
                    sig_data = s
                    break
            en_title = (sig_data or {}).get("title_en", hit.title) if sig_data else hit.title
            loc_top_hits.append(SignatureHit(
                signature_id=hit.signature_id,
                title=en_title,
                category=hit.category,
                severity=hit.severity,
                priority=hit.priority,
                score=hit.score,
                reasons=hit.reasons,
                playbook_id=hit.playbook_id,
                prevention_id=hit.prevention_id,
                tuning_id=hit.tuning_id,
            ))

        pb_fields = ["title", "goal", "safety", "steps", "escalation", "verification", "artifacts"]
        prev_fields = ["title", "checks", "maintenance_schedule"]

        loc_playbook = self._localize(diag.playbook, pb_fields, lang) if diag.playbook else None
        loc_prevention = self._localize(diag.prevention, prev_fields, lang) if diag.prevention else None
        loc_tuning = diag.tuning

        return DiagnosisResult(
            miner_id=diag.miner_id,
            model_id=diag.model_id,
            brand=diag.brand,
            timestamp=diag.timestamp,
            top_hits=loc_top_hits,
            selected=loc_selected,
            playbook=loc_playbook,
            prevention=loc_prevention,
            tuning=loc_tuning,
            error_code_explanations=diag.error_code_explanations,
            confidence=diag.confidence,
            notes=diag.notes,
        )

    def diagnose(self, snapshot: Dict[str, Any]) -> DiagnosisResult:
        """
        snapshot schema (suggested):
          {
            "miner_id": "MINER-0001",
            "model_id": "bitmain_s19_xp" | "bitmain_antminer_generic" | ...,
            "brand": "Bitmain",
            "timestamp": "2026-02-04T12:34:56Z",
            "logs": ["..."],
            "metrics": {"avg_hashrate_12h": 0, "uptime_sec": 120, ...}
          }
        """
        miner_id = snapshot.get("miner_id", "")
        model_id = snapshot.get("model_id", "generic_asic_miner")
        brand = snapshot.get("brand", "Unknown")
        ts = snapshot.get("timestamp", "")

        logs = snapshot.get("logs") or []
        metrics = snapshot.get("metrics") or {}

        extracted_codes = self.extract_codes_from_logs(logs)
        brand_lower = (brand or "unknown").strip().lower()

        # Explain any extracted codes (best-effort)
        explanations = []
        for c in extracted_codes:
            e = self.explain_error_code(brand, c) or self.explain_error_code(brand, c.split(":")[0])
            if e:
                explanations.append({"code": c, **e})

        hits: List[SignatureHit] = []
        log_joined = "\n".join(logs).lower()

        for sig in self.signatures:
            # model applicability
            applies = sig.get("applies_to", []) or ["generic_asic_miner"]
            if model_id not in applies and "generic_asic_miner" not in applies and brand_lower not in [a.lower() for a in applies]:
                # allow brand generic model ids like bitmain_antminer_generic
                if not any(a.endswith("_generic") and a.split("_")[0] in brand_lower for a in applies):
                    continue

            ev = sig.get("evidence", {}) or {}
            reasons: List[str] = []
            score = 0.0

            # codes
            sig_codes = [str(x) for x in (ev.get("codes") or [])]
            code_hit = False
            for c in extracted_codes:
                if any(c.lower() == sc.lower() for sc in sig_codes):
                    code_hit = True
                    reasons.append(f"code hit: {c}")
                    score += 4.0
            # also allow substring match in raw logs (for cases not extracted)
            for sc in sig_codes:
                if sc and sc.lower() in log_joined and f"code hit: {sc}" not in reasons:
                    reasons.append(f"code hit: {sc}")
                    score += 2.0

            # keywords
            for kw in (ev.get("log_keywords") or []):
                if kw and kw.lower() in log_joined:
                    reasons.append(f"keyword: {kw}")
                    score += 1.5

            # regex
            for rgx in sig.get("_compiled_regex", []):
                if rgx.search("\n".join(logs)):
                    reasons.append(f"regex: {rgx.pattern}")
                    score += 2.5

            # metric rules
            for rule in (ev.get("metric_rules") or []):
                ok = _safe_eval_expr(rule, metrics)
                if ok:
                    reasons.append(f"metric: {rule}")
                    score += 3.0

            if score <= 0:
                continue

            # priority boost (lower priority number = more important)
            priority = int(sig.get("priority", 999))
            score = score * (1.0 + max(0.0, (20 - min(priority, 20))) / 50.0)

            hits.append(SignatureHit(
                signature_id=sig["signature_id"],
                title=sig.get("title",""),
                category=sig.get("category","unknown"),
                severity=sig.get("severity","warn"),
                priority=priority,
                score=round(score, 3),
                reasons=reasons[:12],
                playbook_id=sig.get("playbook_id",""),
                prevention_id=sig.get("prevention_id",""),
                tuning_id=sig.get("tuning_id",""),
            ))

        hits.sort(key=lambda h: -h.score)

        selected = hits[0] if hits else None
        confidence = 0.0
        if selected:
            # Simple confidence heuristic; replace with calibrated model later
            confidence = min(0.95, 0.35 + selected.score / 20.0)

        playbook = self.playbooks.get(selected.playbook_id) if selected and selected.playbook_id else None
        prevention = self.preventions.get(selected.prevention_id) if selected and selected.prevention_id else None
        tuning = self.tunings.get(selected.tuning_id) if selected and selected.tuning_id else None

        notes = []
        if selected and confidence < 0.65:
            notes.append("Low confidence: consider LLM fallback or request more telemetry/logs.")
        if not selected:
            notes.append("No signature matched: consider adding new signature or check telemetry completeness.")

        return DiagnosisResult(
            miner_id=miner_id,
            model_id=model_id,
            brand=brand,
            timestamp=ts,
            top_hits=hits[:3],
            selected=selected,
            playbook=playbook,
            prevention=prevention,
            tuning=tuning,
            error_code_explanations=explanations[:6],
            confidence=round(confidence, 3),
            notes=notes,
        )

    # -------- ticket draft helper --------

    def build_ticket_draft(self, diag: DiagnosisResult) -> Dict[str, Any]:
        sel = diag.selected
        title = f"[{diag.brand}] {diag.miner_id} - " + (sel.title if sel else "Needs investigation")
        return {
            "title": title,
            "miner_id": diag.miner_id,
            "brand": diag.brand,
            "model_id": diag.model_id,
            "severity": sel.severity if sel else "warn",
            "category": sel.category if sel else "unknown",
            "confidence": diag.confidence,
            "signature_id": sel.signature_id if sel else None,
            "reasons": sel.reasons if sel else [],
            "playbook": diag.playbook,
            "prevention": diag.prevention,
            "tuning": diag.tuning,
            "evidence_pack": {
                "error_code_explanations": diag.error_code_explanations,
            },
            "verification": (diag.playbook or {}).get("verification", []),
        }
