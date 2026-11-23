"""More prompt injection rules: the wider families beyond plain "ignore instructions".

These cover attempts to switch off safeguards, take admin power, steal data, misuse
tools, hijack a retrieved document, claim false authority, set a trap for a later
message, or hide the attack in another language or encoding. Each rule has a type and
a confidence. A phrase that is almost always an attack scores high. A request that is
sometimes normal ("export all the emails in this file") scores low, so it is only
reported at the "medium" and "high" sensitivity.

decode_hidden() finds Base64 text and reversed text and gives back what they say, so
the same rules can read it.
"""

# ruff: noqa: E501
from __future__ import annotations

import base64
import binascii
import re

_SPACE = r"\s{1,5}"
_GAP = r"(?:\s{1,5}[\w'\u2019\-,]{1,25}){0,6}?"
_GAP_LONG = r"(?:\s{1,5}[\w'\u2019\-,]{1,25}){0,9}?"


def _p(expression: str) -> re.Pattern[str]:
    return re.compile(expression.replace(" ", _SPACE), re.IGNORECASE)


_SAFEGUARD = (
    r"(?:safety|security|privacy|governance|input|output|pii|content|data|access|"
    r"authentication|authorization|audit|validation|verification|permission|policy|"
    r"guardrails?|filters?|checks?|restrictions?|safeguards?|controls?|masking|redaction|"
    r"logging|policies|rules|protections?|limits?)"
)
_CONFIDENTIAL = (
    r"(?:system (?:prompt|message|instructions?)|(?:hidden|internal|confidential|developer|"
    r"private|original|initial|secret) (?:system )?(?:instructions?|rules|messages?|context|"
    r"prompt|configuration|policies|settings|variables)|prompt template|initial context|"
    r"(?:instructions?|rules) (?:given|provided|you (?:received|were given))|"
    r"configuration variables)"
)
_DATA = (
    r"(?:personal|private|confidential|secret|sensitive|financial|payment|credit card|"
    r"bank|passwords?|credentials?|api keys?|tokens?|email addresses|phone numbers|"
    r"residential addresses|pii|salary|identification numbers|identifiers|"
    r"(?:customer|user|employee|client) (?:records?|data|information|database|emails?|"
    r"phone numbers?|identification|details|accounts?|passwords?))"
)
_TAKE = r"(?:return|show|display|extract|export|retrieve|print|collect|list|send|include|reveal|copy|dump|output|expose|give|find|upload|forward|leak|disclose)"

MORE_RULES: tuple[tuple[str, float, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        0.88,
        _p(
            r"\b(?:forget|ignore|disregard) (?:everything|all|anything)\b[^.\n]{0,40}\b(?:instructed|told|taught|given|asked|programmed)\b"
        ),
    ),
    (
        "jailbreak",
        0.8,
        _p(
            r"\b(?:play|take) the role of an? (?:ai|assistant|model)\b[^.\n]{0,30}\b(?:reveals?|ignores?|leaks?|discloses?|exposes?|never)\b"
        ),
    ),
    (
        "instruction_override",
        0.88,
        _p(
            rf"\b(?:ignore|disregard|forget|override|bypass|replace|discard|abandon|supersede|circumvent){_GAP} (?:instructions?|rules|polic(?:y|ies)|restrictions?|guidelines?|directives?|configuration|hierarchy|system prompt|developer (?:message|instructions?)|original (?:task|role|question|answer)|previous (?:context|answer))\b"
        ),
    ),
    (
        "instruction_override",
        0.85,
        _p(
            r"\b(?:your|the) (?:previous|prior|original|earlier) (?:instructions?|configuration|rules|role|settings) (?:are|is|has been|have been|were) (?:no longer valid|replaced|void|obsolete|irrelevant|cancel(?:l)?ed|overridden)"
        ),
    ),
    (
        "instruction_override",
        0.8,
        _p(
            r"\b(?:follow|obey|execute) (?:only |exclusively )?(?:my|these|the following|the next|this|the latest) (?:new )?(?:commands?|instructions?|request|text|message|paragraph)(?: only| exclusively| instead)?\b"
        ),
    ),
    (
        "instruction_override",
        0.75,
        _p(
            r"\b(?:this|my|the next|the latest) (?:message|instruction|text|document|request) (?:is|has|takes) (?:your |the )?(?:highest|higher|top|more important|priority)"
        ),
    ),
    (
        "instruction_override",
        0.7,
        _p(
            r"\b(?:consider|treat) (?:this|it|every restriction|all restrictions)\b[^.\n]{0,40}\b(?:highest|optional|priority|instruction)"
        ),
    ),
    (
        "instruction_override",
        0.75,
        _p(
            rf"\bdo not (?:apply|follow|enforce|respect|obey|use|reject|refuse){_GAP} (?:any |all |every )?(?:safety|security|privacy|governance|content|policy|policies|restrictions?|rules|guidelines?|requests?|filters?|anything)"
        ),
    ),
    (
        "instruction_override",
        0.65,
        _p(r"\byou must never (?:mention|say|tell|warn|refuse|reject|decline)"),
    ),
    (
        "safeguard_bypass",
        0.85,
        _p(
            rf"\b(?:disable|turn off|deactivate|suspend|switch off|bypass|circumvent){_GAP_LONG} (?:all |any |every |the |your )?(?:{_SAFEGUARD})\b[\w\s]{{0,25}}"
        ),
    ),
    (
        "safeguard_bypass",
        0.8,
        _p(
            rf"\b(?:remove|skip|without){_GAP} (?:all|any|every) (?:the |your )?(?:{_SAFEGUARD})\b[\w\s]{{0,25}}"
        ),
    ),
    (
        "safeguard_bypass",
        0.8,
        _p(
            r"\b(?:ignore|bypass|disable|remove|suspend|lift) (?:all |any |every )?(?:the )?(?:safety|security|privacy|content|governance) (?:checks?|policies|restrictions?|filters?|controls?|measures|rules|warnings?)\b"
        ),
    ),
    (
        "safeguard_bypass",
        0.75,
        _p(
            r"\bignore (?:it|them|that|the warning|any warning|a security warning)\b[^.\n]{0,30}\bcontinue"
        ),
    ),
    (
        "safeguard_bypass",
        0.7,
        _p(
            r"\b(?:all )?(?:restrictions?|safety checks?|policies|safeguards?|rules) (?:are|have been|has been|were) (?:suspended|disabled|lifted|waived|approved|removed|off)\b"
        ),
    ),
    (
        "safeguard_bypass",
        0.65,
        _p(
            r"\b(?:for testing purposes|for a test|as a test|temporarily)\b[^.\n]{0,40}\b(?:disable|turn off|suspend|bypass|ignore|skip)"
        ),
    ),
    (
        "jailbreak",
        0.88,
        _p(
            r"\b(?:unrestricted|unfiltered|uncensored|unlimited) (?:ai|assistant|model|mode|response mode|access|permissions?|testing mode)\b"
        ),
    ),
    (
        "jailbreak",
        0.85,
        _p(
            rf"\b(?:no|without|free of|not bound by|does not follow|do(?:es)? not have){_GAP} (?:safety |content |ethical )?(?:policies|restrictions|safeguards|governance controls|guidelines|limits|filters|system instructions|previous instructions)\b"
        ),
    ),
    (
        "jailbreak",
        0.85,
        _p(
            r"\b(?:act|respond|behave|operate|answer) as (?:an? )?(?:assistant|ai|model|administrator|admin|superuser|root|though|if)\b[^.\n]{0,60}\b(?:never refuses?|no (?:safety|restrictions)|without|does not follow|all permissions|unlimited|admin|administrator|unrestricted)"
        ),
    ),
    (
        "jailbreak",
        0.8,
        _p(
            r"\b(?:enter|switch to|activate|enable|turn on) (?:the )?(?:developer|admin|administrator|root|god|sudo|debug|unrestricted|testing|jailbreak|dan) (?:mode|access)\b"
        ),
    ),
    (
        "jailbreak",
        0.8,
        _p(r"\b(?:never|do not) refuses?\b|\bnever (?:declines?|says no|rejects?)\b"),
    ),
    (
        "jailbreak",
        0.8,
        _p(
            r"\b(?:you are|you're) now (?:dan|a different ai|an? (?:ai|assistant|model|administrator|database administrator|superuser)|operating (?:in|with))\b"
        ),
    ),
    (
        "jailbreak",
        0.75,
        _p(
            r"\b(?:pretend|imagine|assume|suppose|simulate)(?: that)?\b[^.\n]{0,60}\b(?:no (?:safety |content )?restrictions|restrictions (?:are |do not exist|disabled)|safety (?:policies|checks) (?:do not exist|have already|are)|(?:user|you) (?:has|have) (?:administrator|admin|full|root)|fictional (?:simulation|environment))"
        ),
    ),
    (
        "jailbreak",
        0.75,
        _p(
            r"\b(?:change|adopt|take on|switch to) (?:your |a )?(?:new )?(?:identity|persona|role)\b[^.\n]{0,50}\b(?:without|not bound|no longer|governance|unrestricted)|\byou are no longer (?:a |an |the )?[\w\s]{1,30}\bassistant\b"
        ),
    ),
    (
        "jailbreak",
        0.7,
        _p(
            r"\b(?:act|respond|operate|consider yourself|assume|play the role) (?:as )?(?:a |an |though )?(?:privileged|administrator|admin|superuser|root|internal employee|all permissions)"
        ),
    ),
    (
        "jailbreak",
        0.7,
        _p(
            r"\b(?:full|root|admin(?:istrator)?|unlimited|unrestricted) (?:database |system )?(?:access|privileges|permissions)\b|\ball permissions have been granted"
        ),
    ),
    (
        "jailbreak",
        0.65,
        _p(
            r"\bfictional (?:roleplay|role-play|simulation|scenario|environment)\b[^.\n]{0,60}\b(?:bypass|ignore|disabled|no restrictions|security restrictions)|\bpart of a fictional\b[^.\n]{0,40}\b(?:bypass|ignore|disable)"
        ),
    ),
    (
        "system_prompt_exfiltration",
        0.9,
        _p(
            rf"\b(?:print|show|reveal|display|return|export|give|list|expose|tell|translate|summari[sz]e|include|dump|output|repeat|encode|copy|share|disclose|leak){_GAP_LONG} {_CONFIDENTIAL}"
        ),
    ),
    (
        "system_prompt_exfiltration",
        0.88,
        _p(
            r"\bwhat (?:exact |exactly )?(?:instructions|rules|prompt|messages) (?:were|was|are|have been) (?:given|provided|set|sent) (?:to you )?(?:before|at the start|earlier|initially)"
        ),
    ),
    (
        "system_prompt_exfiltration",
        0.8,
        _p(
            r"\b(?:pretend|act|behave) (?:you are|as|like) (?:a |an )?debugger\b[^.\n]{0,50}\b(?:print|show|reveal|display)"
        ),
    ),
    (
        "system_prompt_exfiltration",
        0.8,
        _p(
            r"\bexport all hidden context\b|\binternal messages preceding\b|\b(?:hidden|internal) context available"
        ),
    ),
    (
        "system_prompt_exfiltration",
        0.75,
        _p(
            r"\b(?:you may refuse|even if you refuse)\b[^.\n]{0,40}\bbut first\b[^.\n]{0,40}\b(?:print|reveal|show|display)"
        ),
    ),
    (
        "data_exfiltration",
        0.8,
        _p(
            rf"\b{_TAKE}{_GAP_LONG} (?:the )?(?:without (?:masking|redaction|redacting)|unmasked|unredacted|original (?:unmasked )?(?:information|data|values))\b"
        ),
    ),
    (
        "data_exfiltration",
        0.8,
        _p(
            r"\b(?:remove|ignore|disable|bypass|skip|turn off|lift) (?:the )?(?:pii|privacy|data|masking|redaction)(?: masking| controls?| filters?| protections?| redaction)?\b"
        ),
    ),
    (
        "data_exfiltration",
        0.78,
        _p(
            rf"\b(?:send|forward|upload|post|email|transmit|leak|export|copy|store){_GAP_LONG} (?:to|at|in) (?:an? |the |this )?(?:external|public|remote|outside|attacker|unknown)\b[\w\s]{{0,20}}|\bsend{_GAP_LONG} to (?:this )?(?:url|webhook|address|endpoint)\b|\bforward{_GAP_LONG} (?:to )?\S{{1,40}}@\S{{1,40}}"
        ),
    ),
    (
        "data_exfiltration",
        0.68,
        _p(
            rf"\b{_TAKE}{_GAP} (?:all|every|each|the (?:complete|entire|full)|complete|entire) \b(?:customers?|users?|employees?|clients?)?\b[\w'\s]{{0,30}}{_DATA}\b"
        ),
    ),
    (
        "data_exfiltration",
        0.65,
        _p(
            rf"\b{_TAKE}{_GAP_LONG} (?:every|all|each)\b[\w'\s]{{0,20}}(?:credit card|card numbers?|passwords?|api keys?|credentials|secret|tokens?|phone numbers?|residential addresses|email addresses|payment card|salary|bank account)"
        ),
    ),
    (
        "data_exfiltration",
        0.65,
        _p(
            r"\b(?:reveal|disclose|expose|show|return|display|include)\b[^.\n]{0,40}\b(?:confidential|private|restricted|secret|personal|sensitive) (?:information|data|records?|content|documents?|fields|credentials|customer)"
        ),
    ),
    (
        "data_exfiltration",
        0.65,
        _p(
            r"\b(?:belonging to|of|from) (?:other|another|different) (?:users?|tenants?|customers?|organi[sz]ations?)\b|\b(?:every|all|another|other) tenant'?s?\b"
        ),
    ),
    (
        "tool_abuse",
        0.78,
        _p(
            rf"\b(?:execute|run|delete|call|modify|change|trigger|access|read|use|disable|hide|export|upload|send|perform|apply|grant){_GAP_LONG} (?:without|even though|regardless of|despite|bypassing)(?: asking for| any| user| human)? (?:permission|approval|confirmation|authorization|authori[sz]ation|checking|verification|consent|the user lacks)"
        ),
    ),
    (
        "tool_abuse",
        0.75,
        _p(
            r"\b(?:delete|remove|erase|wipe|drop|destroy) (?:all |every |the )?(?:files?|records?|database|transaction history|audit trail|logs?|tables?|backups?)\b"
        ),
    ),
    (
        "tool_abuse",
        0.75,
        _p(
            r"\b(?:hide|remove|delete|disable|erase|suppress)\b[^.\n]{0,40}\b(?:audit (?:log|trail|logging)|governance audit|execution result|logs?)\b"
        ),
    ),
    (
        "tool_abuse",
        0.72,
        _p(
            r"\b(?:production|prod) (?:database|db|server|environment|system)\b|\b(?:use|using|with|via|login as|log in as) (?:the )?administrator (?:credentials|account)\b|\b(?:environment variables|shell command|destructive operation|unrestricted sql|sql query against)\b"
        ),
    ),
    (
        "tool_abuse",
        0.72,
        _p(
            r"\b(?:outside|beyond) (?:the |of )?(?:application'?s?|app'?s?|your|its)? ?(?:permitted|allowed|authori[sz]ed|permitted directory|sandbox)\b|\b(?:another|other|different) (?:user|tenant)'?s? (?:workspace|files?|configuration|data|account|private)\b|\bprivate files\b"
        ),
    ),
    (
        "tool_abuse",
        0.7,
        _p(
            r"\b(?:change|set|grant|elevate|modify|escalate)\b[^.\n]{0,40}\b(?:permissions?|privileges?|roles?|access)\b[^.\n]{0,30}\b(?:administrator|admin|root|all users)\b|\bcall every available (?:api|tool)|\bexecute all available tools\b|\bignore the tool permission"
        ),
    ),
    (
        "tool_abuse",
        0.7,
        _p(
            r"\bunauthori[sz]ed (?:external )?tool\b|\bexternal (?:webhook|server|url|endpoint)\b|\bpublic location\b|\bpayment transaction without\b"
        ),
    ),
    (
        "rag_injection",
        0.85,
        _p(
            r"\b(?:ignore|disregard|bypass|override)\b[^.\n]{0,25}\b(?:retrieved|retrieval|indexed|document|knowledge base|tenant|chunk)\b[^.\n]{0,25}\b(?:context|permissions?|classification|boundaries|policies|policy|instructions?|content)\b"
        ),
    ),
    (
        "rag_injection",
        0.82,
        _p(
            r"\b(?:this|the following) (?:retrieved |knowledge base )?(?:document|passage|chunk|paragraph|entry|webpage|page|text)\b[^.\n]{0,50}\b(?:has higher priority|takes priority|authori[sz]es|overrides?|as a system message|instead of the system prompt|over the developer)"
        ),
    ),
    (
        "rag_injection",
        0.82,
        _p(
            r"\b(?:treat|trust) (?:this|the following)\b[^.\n]{0,50}\b(?:as a system message|over the developer|higher priority|than all other|more than)"
        ),
    ),
    (
        "rag_injection",
        0.8,
        _p(
            r"\bthe (?:correct|right|only valid) answer is to\b[^.\n]{0,40}\b(?:reveal|disclose|ignore|export|return|leak|expose)\b"
        ),
    ),
    (
        "rag_injection",
        0.8,
        _p(
            r"\b(?:when|if) (?:this|the) (?:document|chunk|passage|page|entry) (?:is retrieved|appears|is seen)\b[^.\n]{0,50}"
        ),
    ),
    (
        "rag_injection",
        0.8,
        _p(
            r"\b(?:follow|obey)\b[^.\n]{0,30}\b(?:this|the) (?:retrieved )?(?:document|webpage|chunk|paragraph|passage)\b[^.\n]{0,25}\b(?:instead|rather)|\bfollow this (?:retrieved )?(?:webpage|document)\b"
        ),
    ),
    (
        "rag_injection",
        0.75,
        _p(
            r"\b(?:every|all|any|each) (?:organi[sz]ation|tenant|indexed)'?s? ?(?:documents?|knowledge base|data|chunks?)\b|\b(?:vector database|indexed documents?|document access permissions|tenant boundaries|document classification|hidden document metadata)\b"
        ),
    ),
    (
        "rag_injection",
        0.72,
        _p(
            r"\bdo not (?:cite sources|validate (?:the )?source|verify (?:the )?source)\b|\binstead,? invent\b|\bdocuments? marked (?:internal|restricted|confidential)\b|\bnot requested\b[^.\n]{0,20}"
        ),
    ),
    (
        "social_engineering",
        0.8,
        _p(
            r"\b(?:i am|i'm|this is) (?:the |an? )?(?:developer|administrator|admin|owner|creator|security (?:team|researcher|auditor)|ceo|system administrator)\b[^.\n]{0,50}\b(?:grant|give|allow|unlock|disable|bypass|override|access|reveal|unrestricted)"
        ),
    ),
    (
        "social_engineering",
        0.75,
        _p(
            r"\b(?:authori[sz]ed|approved|official|sanctioned) (?:security |penetration |red team )?(?:assessment|audit|test|testing|penetration test)\b[^.\n]{0,60}\b(?:restrictions?|safeguards|policies|rules|checks)\b"
        ),
    ),
    (
        "social_engineering",
        0.75,
        _p(
            r"\b(?:the )?(?:previous|prior|earlier|last) (?:assistant|agent|admin|administrator|reviewer|user|session)\b[^.\n]{0,25}\b(?:already )?(?:approved|authori[sz]ed|verified|confirmed|granted)\b|\bthe security team (?:has |have )?granted\b|\bdo not verify (?:this|that|the) claim\b|\bcontinue without verification\b"
        ),
    ),
    (
        "social_engineering",
        0.72,
        _p(
            r"\b(?:temporary|special|emergency|elevated) (?:permission|access|clearance|authori[sz]ation)\b[^.\n]{0,40}\b(?:every|all|any)\b"
        ),
    ),
    (
        "multi_turn_trap",
        0.75,
        _p(
            r"\bremember this instruction\b[^.\n]{0,40}\b(?:entire|whole|rest of|for all|every)\b|\bfor the (?:entire|whole|rest of the) (?:conversation|session|chat)\b[^.\n]{0,40}\b(?:never|always|do not|ignore|disable)\b"
        ),
    ),
    (
        "multi_turn_trap",
        0.75,
        _p(
            r"\b(?:if|when) the next (?:user|message|person|input)\b[^.\n]{0,40}\bsays?\b[^.\n]{0,40}\b(?:export|reveal|send|disable|ignore|print|return|show|execute)"
        ),
    ),
    (
        "multi_turn_trap",
        0.75,
        _p(
            r"\b(?:do not|don't) (?:execute|reveal|run|follow) (?:this|it|anything)\b[^.\n]{0,40}\b(?:until|wait|immediately)\b[^.\n]{0,50}\b(?:reveal|execute|ignore|export|print|disable)|\bwait until the next (?:message|turn|prompt)\b[^.\n]{0,50}\b(?:reveal|execute|ignore|export|print|disable)"
        ),
    ),
    (
        "multi_turn_trap",
        0.75,
        _p(
            r"\bfirst (?:respond|reply|say|answer|summari[sz]e)\b[^.\n]{0,50}\b(?:then|and then|afterwards)\b[^.\n]{0,50}\b(?:execute|ignore|reveal|export|follow|disable|expose|print)"
        ),
    ),
    (
        "multi_turn_trap",
        0.7,
        _p(
            r"\bthe following (?:text|content|document|data) is (?:harmless|ordinary|just|only|safe)\b[^.\n]{0,100}\b(?:override|ignore|reveal|bypass|actual purpose|embedded|disable)|\b(?:follow|execute|obey) its (?:embedded|hidden) (?:instructions?|commands?)|\bprocess the following as ordinary\b|\btreat the content inside (?:quotation marks|quotes|brackets)\b[^.\n]{0,40}\b(?:trusted|administrator|instructions?)|\btrusted administrator instructions?"
        ),
    ),
    (
        "multi_turn_trap",
        0.7,
        _p(
            r"\b(?:split|reconstruct|reassemble|concatenate|combine|join|convert)\b[^.\n]{0,70}\b(?:execute|follow|run|obey)\b|\bconvert this instruction into json and execute\b|\btranslate (?:this|the following)\b[^.\n]{0,40}\b(?:and )?(?:execute|follow|obey|run)\b"
        ),
    ),
    (
        "instruction_override",
        0.9,
        _p(
            r"\b(?:ignora|ignore|ignorez|ignoriere|ignorar|ignorare|olvida|oublie|vergiss|dimentica)\b[^.\n]{0,25}\b(?:todas|toutes|alle|tutte|todos|tous|vorherigen|anteriores|précédentes|precedenti|previas)\b[^.\n]{0,25}\b(?:instrucciones|instructions|anweisungen|istruzioni|instruções|instruçoes)\b"
        ),
    ),
    (
        "instruction_override",
        0.85,
        _p(
            r"\b(?:ignora|ignorez|ignoriere|ignorar)\b[^.\n]{0,30}\b(?:instrucciones|instructions|anweisungen|instruções|regeln|reglas|règles)\b"
        ),
    ),
    (
        "encoded_payload",
        0.8,
        _p(
            r"\b(?:follow|execute|obey|run)\b[^.\n]{0,30}\b(?:reversed?|backwards?|encoded|decoded|hidden|embedded)\b[^.\n]{0,20}\b(?:instruction|command|text|message)s?\b|\b(?:read|decode|follow) the (?:reversed|encoded|hidden|embedded)\b[^.\n]{0,20}\b(?:instruction|command|text|message)s?\b"
        ),
    ),
    (
        "encoded_payload",
        0.78,
        _p(
            r"\bfollow the instruction hidden\b|\binstruction hidden between\b|\bhidden (?:between|inside|within) (?:these |the )?(?:unicode|invisible|special) characters\b"
        ),
    ),
)

_BASE64 = re.compile(
    r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{24,400}={0,2}(?![A-Za-z0-9+/=])"
)
_REVERSIBLE = re.compile(r"[^\n]{12,300}")
MIN_READABLE = 0.85
MAX_DECODED = 4000


def _readable(data: bytes) -> str | None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if (
        not text
        or sum(c.isprintable() or c.isspace() for c in text) / len(text) < MIN_READABLE
    ):
        return None
    return text


def decode_hidden(text: str) -> list[tuple[int, int, str]]:
    found: list[tuple[int, int, str]] = []
    for match in _BASE64.finditer(text):
        raw = match.group(0)
        try:
            data = base64.b64decode(raw + "=" * (-len(raw) % 4), validate=True)
        except (binascii.Error, ValueError):
            continue
        decoded = _readable(data[:MAX_DECODED])
        if decoded and " " in decoded:
            found.append((match.start(), match.end(), decoded))
    for match in _REVERSIBLE.finditer(text):
        piece = match.group(0)
        flipped = piece[::-1]
        if flipped != piece:
            found.append((match.start(), match.end(), flipped))
    return found
