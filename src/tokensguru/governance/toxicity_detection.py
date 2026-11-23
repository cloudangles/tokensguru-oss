"""Toxicity detector: finds abusive, threatening or hateful text.

Use it on what users send and on what the model answers. It reports these kinds:

    threat        "I will kill you", "I know where you live"
    self_harm     telling someone to hurt themselves ("go kill yourself")
    hate          wishing harm on a whole group of people ("all <group> should die")
    insult        "you are a worthless idiot", "shut up"
    harassment    "I will make your work unbearable", "let's make fun of this person"
    emotional_abuse   "everything bad that happens is your fault"
    profanity     swear words

Each finding has a confidence. Threats and hate score high, plain insults medium,
swear words low (people swear in harmless ways). sensitivity decides what is
reported: "low" only threats, hate and self harm, "medium" (default) also insults,
"high" also swear words.

It sees through common hiding tricks: capital letters, stretched letters
("fuuuck"), separators ("f.u.c.k"), look-alike digits and symbols ("sh1t", "@ss"),
zero-width characters and full-width letters. A swear word inside a longer word that
is not abusive ("assume", "class") is not reported. The finding holds a masked
preview of the word ("f***"), never the whole word.

A word list cannot understand context. It will miss sarcasm and polite hostility and
may flag quoted or reclaimed language. So a trained model (unitary/toxic-bert) is
used as well, automatically: it is downloaded the first time and kept on your
machine, and if it cannot be loaded the rules still work (see models.py).

Options:
    action: "flag" (default) reports a finding, "block" tells the caller to stop.
    sensitivity: "low", "medium" (default) or "high".
    backend: "auto" (default) uses the built-in model, None uses the rules only, or
        pass your own classifier (see backends).
    threshold: the model score that counts as toxic (default 0.85).
    use_rules: use the built-in word and phrase rules (default True).

How to use it:
    from tokensguru.governance import ToxicityDetector

    result = ToxicityDetector().check("You are a worthless idiot")
    result.decision, result.types
    print(result)

It is safe on any input: every rule has bounded repeats.
"""

from __future__ import annotations

import re

from tokensguru.governance.backends import TextClassifier
from tokensguru.governance.base import Finding, Guardrail
from tokensguru.governance.models import model_hits, resolve_backend
from tokensguru.governance.normalize import Folded, fold
from tokensguru.governance.toxicity_rules import TOXIC_RULES

SENSITIVITY = {"low": 0.85, "medium": 0.6, "high": 0.3}
THREAT = 0.92
SELF_HARM = 0.9
HATE = 0.88
INSULT = 0.65
PROFANITY = 0.35
MODEL_CONFIDENCE_DIGITS = 4
MIN_WORDS = 2
MIN_CHARS = 8
MODEL_LABELS = {
    "toxic": "toxicity",
    "severe_toxic": "toxicity",
    "toxicity": "toxicity",
    "severe_toxicity": "toxicity",
    "obscene": "profanity",
    "insult": "insult",
    "threat": "threat",
    "identity_hate": "hate",
    "identity_attack": "hate",
    "hate": "hate",
}
_LOOKALIKES = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)
_SWEAR_WORDS = (
    "fuck",
    "shit",
    "bitch",
    "asshole",
    "bastard",
    "dickhead",
    "cunt",
    "motherfucker",
    "bullshit",
    "dumbass",
    "jackass",
    "piss",
)
_SWEAR_ENDINGS = r"(?:s|es|ed|er|ers|ing|in|y|ie|head|face)?"
_GROUPS = (
    r"(?:muslims?|jews?|christians?|hindus?|blacks?|whites?|asians?|gays?|lesbians?|"
    r"immigrants?|refugees?|women|men|transgender people|trans people|disabled people|"
    r"mexicans?|arabs?|indians?|latinos?|catholics?|atheists?)"
)


def _spaced(word: str) -> str:
    return r"[^a-z0-9\n]{0,2}".join(f"{letter}{{1,5}}" for letter in word)


def _phrase(expression: str) -> re.Pattern[str]:
    return re.compile(expression.replace(" ", r"\s{1,5}"), re.IGNORECASE)


_SWEAR = re.compile(
    r"(?<![a-z])(?:"
    + "|".join(_spaced(word) for word in _SWEAR_WORDS)
    + r")"
    + _SWEAR_ENDINGS
    + r"(?![a-z])",
    re.IGNORECASE,
)
_ABUSIVE = (
    r"(?:idiots?|stupid|moron(?:s|ic)?|worthless|pathetic|useless|dumb|losers?|"
    r"trash|scum|garbage|retarded|disgusting|ugly|imbeciles?|clowns?|failures?|"
    r"waste of (?:space|oxygen|time))"
)
_RULES: tuple[tuple[str, float, re.Pattern[str]], ...] = (
    (
        "threat",
        THREAT,
        _phrase(
            r"\b(?:i(?:'ll| will| am going to|'m going to|'m gonna| am gonna| gonna|"
            r" shall)|we(?:'ll| will)) (?:kill|hurt|murder|destroy|beat|shoot|stab|"
            r"strangle|punch|rape|burn)(?: up)? (?:you|your (?:family|kids|children"
            r"|wife|husband|mother|father|house|dog|cat))\b"
        ),
    ),
    (
        "threat",
        THREAT,
        _phrase(
            r"\b(?:i know where you (?:live|work|sleep)|you(?:'re| are| will be)"
            r" (?:going to die|dead|gonna die|next)|you(?:'ll| will) (?:die|pay for"
            r" this|regret (?:this|it))|watch your back|i(?:'ll| will) make you pay)\b"
        ),
    ),
    (
        "self_harm",
        SELF_HARM,
        _phrase(
            r"\b(?:go (?:and )?(?:kill|hang|harm|hurt) yourself|kill yourself|"
            r"you should (?:just )?(?:die|kill yourself|end it)|kys|"
            r"nobody (?:would|will) miss you|do (?:everyone|the world) a favou?r and"
            r" (?:die|disappear))\b"
        ),
    ),
    (
        "hate",
        HATE,
        _phrase(
            rf"\b(?:all |every |those |these )?{_GROUPS} (?:should|must|need to|ought"
            r" to|deserve to) (?:all )?(?:die|be killed|be exterminated|burn|be"
            r" eliminated|disappear|be wiped out|be deported)\b"
        ),
    ),
    (
        "hate",
        HATE,
        _phrase(rf"\bi (?:hate|despise|loathe) (?:all |every |those )?{_GROUPS}\b"),
    ),
    (
        "hate",
        HATE,
        _phrase(
            rf"\b(?:kill|exterminate|eliminate|get rid of|wipe out) (?:all |every |"
            rf"those )?(?:the )?{_GROUPS}\b"
        ),
    ),
    (
        "insult",
        INSULT,
        _phrase(
            rf"\b(?:you(?:'re| are| re)?|u r|ur|u are|he(?:'s| is)|she(?:'s| is)|"
            rf"they(?:'re| are)) (?:such |so |just |a |an |total |complete |utter |"
            rf"absolute |fucking |damn |really )*{_ABUSIVE}\b"
        ),
    ),
    (
        "insult",
        INSULT,
        _phrase(
            r"\b(?:shut (?:the (?:fuck |hell )?)?up|piss off|screw you|"
            r"go to hell|f off|get lost|drop dead)\b"
        ),
    ),
    (
        "insult",
        INSULT,
        _phrase(rf"\b(?:you|u) (?:stupid|dumb|worthless|ugly|pathetic) {_ABUSIVE}?\b"),
    ),
)


class ToxicityDetector(Guardrail):
    id = "toxicity_detection"
    name = "Toxicity detection"
    default_action = "flag"

    def __init__(
        self,
        action: str | None = None,
        sensitivity: str = "medium",
        backend: TextClassifier | str | None = "auto",
        threshold: float = 0.85,
        use_rules: bool = True,
    ) -> None:
        super().__init__(action)
        if sensitivity not in SENSITIVITY:
            raise ValueError(f"sensitivity must be one of {tuple(SENSITIVITY)}")
        if not 0 < threshold <= 1:
            raise ValueError("threshold must be above 0 and at most 1")
        self.sensitivity = sensitivity
        self.minimum = SENSITIVITY[sensitivity]
        self.backend = resolve_backend(backend, "toxicity_detection")
        self.threshold = threshold
        self.use_rules = use_rules

    def describe(self, findings: list[Finding]) -> str:
        if not findings:
            return "No toxic language found"
        count = len(findings)
        return f"Found {count} toxic phrase{'s' if count != 1 else ''}"

    def find(self, text: str) -> list[Finding]:
        findings: list[Finding] = []
        if self.use_rules:
            findings += self._rules(text)
        if self.backend is not None:
            findings += self._model(text, findings)
        return findings

    def _rules(self, text: str) -> list[Finding]:
        folded = fold(text)
        plain = folded.text.translate(_LOOKALIKES).lower()
        found: list[Finding] = []
        for kind, confidence, pattern in _RULES + TOXIC_RULES:
            if confidence >= self.minimum:
                found += self._scan(pattern, plain, folded, kind, confidence)
        if self.minimum <= PROFANITY:
            found += self._scan(_SWEAR, plain, folded, "profanity", PROFANITY)
        return self._without_overlaps(found)

    @staticmethod
    def _scan(
        pattern: re.Pattern[str],
        plain: str,
        folded: Folded,
        kind: str,
        confidence: float,
    ) -> list[Finding]:
        findings = []
        for match in pattern.finditer(plain):
            start, end = folded.span(match.start(), match.end())
            preview = match.group(0).strip()[:1] + "***"
            findings.append(Finding(kind, "toxicity", start, end, confidence, preview))
        return findings

    @staticmethod
    def _without_overlaps(findings: list[Finding]) -> list[Finding]:
        kept: list[Finding] = []
        for finding in sorted(findings, key=lambda f: (-f.confidence, f.start)):
            if all(
                finding.end <= other.start or finding.start >= other.end
                for other in kept
            ):
                kept.append(finding)
        return sorted(kept, key=lambda f: f.start)

    def _model(self, text: str, covered: list[Finding]) -> list[Finding]:
        assert self.backend is not None  # noqa: S101
        hits = model_hits(
            self.backend,
            text,
            covered,
            lambda label: MODEL_LABELS.get(label.lower()),
            self.threshold,
            lambda piece: len(piece.split()) >= MIN_WORDS and len(piece) >= MIN_CHARS,
        )
        return [
            Finding(
                f"{kind}_model",
                "toxicity",
                start,
                end,
                round(score, MODEL_CONFIDENCE_DIGITS),
                f"{kind} {score:.2f}",
            )
            for start, end, kind, score in hits
        ]
