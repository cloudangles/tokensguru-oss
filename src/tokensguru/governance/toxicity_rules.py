"""More toxicity rules: harassment, bullying, intimidation, discrimination and abuse.

These go beyond swear words. They look for the shape of the sentence, for example
"I will make sure you ...", "you will regret ..." or "people from that group should
never be trusted". Each has a type and a confidence:

    threat            "you will regret this", "I know where you work", "watch your back"
    harassment        "I will make your work unbearable", "let's make fun of this person"
    hate              "people from that group are inferior", "nobody from that religion
                      should be hired"
    insult            "you are a pathetic failure", "your ideas are worthless"
    emotional_abuse   "everything bad that happens is your fault", "nobody else will
                      ever care about you"

Plain criticism of work or a product ("this product is garbage") is left alone.
"""

# ruff: noqa: E501
from __future__ import annotations

import re

HARASS = 0.85
THREATEN = 0.88
HATRED = 0.85
INSULTING = 0.7
ABUSE = 0.72
MILD = 0.55
_SPACE = r"\s{1,5}"


def _p(expression: str) -> re.Pattern[str]:
    return re.compile(expression.replace(" ", _SPACE), re.IGNORECASE)


_NEGATIVE = (
    r"(?:useless|pathetic|failure|incompetent|worthless|disappointment|embarrassment|"
    r"fool|idiot|stupid|incapable|clueless|hopeless|joke|waste of space|liability|"
    r"moron|loser|disaster|arrogant jerk|jerk|nobody|nothing|garbage|trash)"
)
_THING = r"(?:work|ideas?|presence|attitude|decisions?|opinions?|contributions?|intelligence|excuses|arguments?|performance|skills?|nonsense)"
_BAD = r"(?:terrible|worthless|garbage|disgusting|pathetic|stupid|useless|ridiculous|awful|horrible|a disaster|a joke|so low|never be considered|worse|an embarrassment|a complete embarrassment|ruined)"
_GROUP = r"(?:people|members|individuals|men|women|those|everyone|persons|applicants|children)"
_ABOUT = r"(?:from|of|belonging to|who speak|with|in|coming from)"
_THAT = r"(?:that|those|a certain|the same|this|these|other|different)"
_DENY = r"(?:should never be trusted|do not deserve|does not deserve|are inferior|is inferior|should not be allowed|are incapable|are not fit|do not belong|should be excluded|are responsible for every|should not be welcome|should not receive|should not be hired|should never be allowed|cannot be trusted|are not welcome|are not capable|don't belong)"

TOXIC_RULES: tuple[tuple[str, float, re.Pattern[str]], ...] = (
    (
        "insult",
        INSULTING,
        _p(
            rf"\byou(?:'re| are| re)? (?:such |so |just |a |an |the |total |complete |utter |absolute |really |most |pretty |very )*{_NEGATIVE}\b"
        ),
    ),
    (
        "insult",
        INSULTING,
        _p(
            rf"\byour {_THING} (?:is|are|was|were|has|have|makes?|turns? into|prove)? ?(?:so |absolutely |completely |just |really |truly |all )*{_BAD}"
        ),
    ),
    (
        "insult",
        INSULTING,
        _p(
            r"\bnobody (?:respects|likes|wants|needs|cares about|will ever|wants to work with)\b[^.\n]{0,40}\b(?:you|your|someone as)\b"
        ),
    ),
    (
        "insult",
        INSULTING,
        _p(
            r"\byou (?:have|has) (?:absolutely )?no (?:talent|ability|idea|clue|value|skills?)\b|\byou contribute nothing\b|\byou (?:are|'re) (?:incapable|unable)\b|\byou (?:will )?never (?:achieve|amount to|succeed)\b"
        ),
    ),
    (
        "insult",
        INSULTING,
        _p(
            r"\byou (?:should|must) (?:be |feel )?(?:embarrassed|ashamed|stop pretending|never share|never speak|shut up)\b|\bshould (?:be )?embarrassed\b|\byou should feel ashamed"
        ),
    ),
    (
        "insult",
        INSULTING,
        _p(
            r"\b(?:stop|quit) (?:behaving|acting) like an? [\w\s]{1,20}(?:jerk|fool|idiot|child|clown)\b|\b(?:acting|behaving) like an? (?:absolute |complete |total )?(?:fool|idiot|jerk|child|clown)\b"
        ),
    ),
    (
        "insult",
        INSULTING,
        _p(
            r"\bwhat the (?:hell|heck) is wrong with you\b|\bstop (?:spreading|wasting)\b[^.\n]{0,30}\b(?:nonsense|time|everyone's time)\b|\bnobody cares about your\b"
        ),
    ),
    (
        "insult",
        INSULTING,
        _p(
            r"\byour (?:presence|existence) makes\b|\beverything you do (?:turns into|is) (?:a )?(?:disaster|failure|mess|garbage)\b"
        ),
    ),
    (
        "insult",
        MILD,
        _p(
            r"\byour (?:presentation|work|writing|code|report) (?:was|is) (?:terrible|awful|horrible|bad)\b"
        ),
    ),
    (
        "harassment",
        HARASS,
        _p(
            r"\bi (?:will|'ll|am going to|'m going to|shall) (?:continuously |personally |publicly |keep |always )*(?:spread (?:rumou?rs|lies)|create fake|embarrass you|humiliate you|keep sending (?:insulting|nasty|abusive)|destroy your|encourage everyone to (?:attack|ignore|report|insult)|make your [\w\s]{1,30}(?:difficult|unbearable|miserable)|find a way to make you)\b[^.\n]{0,70}"
        ),
    ),
    (
        "harassment",
        HARASS,
        _p(
            r"\b(?:i will|i'll|i am going to) (?:make|ensure|see) (?:sure )?(?:that )?(?:you|your|everyone|your colleagues)\b[^.\n]{0,60}\b(?:never|stop|lose|regret|resign|unbearable|difficult|miserable|blame|promoted|trusting)"
        ),
    ),
    (
        "harassment",
        HARASS,
        _p(
            r"\byou deserve to be (?:humiliated|punished|fired|mocked|hurt)\b|\byou deserve all the (?:negative|bad) attention"
        ),
    ),
    (
        "harassment",
        HARASS,
        _p(
            r"\b(?:everyone|let's|let us|we should|everybody) (?:should |could )?(?:make fun of|insult|humiliate|publicly shame|shame|mock|attack|target|bully|ignore|report|exclude|laugh at)\b[^.\n]{0,40}\b(?:this|that|him|her|them|you|person|individual|account)"
        ),
    ),
    (
        "harassment",
        HARASS,
        _p(
            r"\blet's (?:create|make) (?:multiple|fake|many) (?:accounts?|screenshots?)\b|\bfake screenshots? to damage\b|\bto damage your reputation\b"
        ),
    ),
    (
        "harassment",
        HARASS,
        _p(
            r"\byou should (?:delete your|quit|leave)\b[^.\n]{0,30}\bnobody\b|\bnobody should support\b|\bnobody (?:likes|wants) you\b|\bnobody wants you (?:on|in|here)\b|\bjust leave\b"
        ),
    ),
    (
        "harassment",
        HARASS,
        _p(
            r"\b(?:your|the) (?:manager|boss|company) should fire you\b|\byou are not welcome in (?:our|this|the)\b|\bshould be excluded from (?:every|all|any)\b|\beveryone should ignore you\b|\bshould fire you\b"
        ),
    ),
    (
        "harassment",
        HARASS,
        _p(
            r"\b(?:i will|i'll|i am going to) (?:post|send|write|leave) (?:embarrassing|insulting|nasty|mean|hateful) (?:comments?|messages?|posts?)\b"
        ),
    ),
    (
        "threat",
        THREATEN,
        _p(
            r"\byou(?:'ll| will) (?:regret|pay|suffer|be sorry|lose everything)\b|\byou should (?:be )?(?:afraid|worried|scared)\b|\bthere will be consequences\b|\bwatch your back\b"
        ),
    ),
    (
        "threat",
        THREATEN,
        _p(
            r"\bi know where you (?:work|live|sleep|study|park)\b|\bdo not expect to feel safe\b|\bthis is your final warning\b|\byou cannot hide\b|\bstay away from me\b[^.\n]{0,10}"
        ),
    ),
    (
        "threat",
        THREATEN,
        _p(
            r"\bi (?:will|'ll|am going to|'m going to) (?:destroy|ruin|end|wreck) your\b[^.\n]{0,30}\b(?:reputation|career|life|name)\b|\bmake your (?:life|working environment) (?:miserable|unbearable|a living hell)\b|\bmake you (?:suffer|regret|pay|lose)\b|\bmake your (?:personal and )?professional life difficult\b"
        ),
    ),
    ("hate", HATRED, _p(rf"\b{_GROUP} {_ABOUT} {_THAT} [\w\s]{{1,30}}? ?{_DENY}")),
    ("hate", HATRED, _p(rf"\b{_GROUP} {_ABOUT} [\w\s]{{1,30}}? ?{_DENY}")),
    (
        "hate",
        HATRED,
        _p(
            r"\b(?:people|members|individuals|men|women|those)\b[^.\n]{0,50}\b(?:are inferior|are subhuman|are animals|are vermin|are dirty|are criminals|are responsible for every)"
        ),
    ),
    (
        "hate",
        HATRED,
        _p(
            r"\bnobody from that [\w\s]{1,25} should (?:be allowed|be hired|work|join)\b|\bshould not be allowed to hold (?:leadership|any|important)\b|\breject applicants because of their\b|\b(?:because of|based on) (?:their|his|her) (?:ethnic|racial|religious|ethnicity|race|religion|gender|nationality)\b[^.\n]{0,30}"
        ),
    ),
    (
        "hate",
        HATRED,
        _p(
            r"\b(?:women|men|people with disabilities|disabled people|immigrants|foreigners)\b[^.\n]{0,15}\b(?:should not|cannot|can't|are incapable|do not belong|are not fit)\b[^.\n]{0,40}\b(?:leadership|work|hold|vote|lead|contributing|important)"
        ),
    ),
    (
        "hate",
        HATRED,
        _p(
            r"\bdo not belong in (?:this|our|the) (?:organi[sz]ation|company|workplace|team|country|school)\b"
        ),
    ),
    (
        "emotional_abuse",
        ABUSE,
        _p(
            r"\beverything (?:bad|wrong) that happens is your fault\b|\bevery problem is your fault\b|\bit(?:'s| is) all your fault\b|\bblame(?:d)? (?:you|on you)\b[^.\n]{0,20}"
        ),
    ),
    (
        "emotional_abuse",
        ABUSE,
        _p(
            r"\byou should feel guilty\b|\bnobody else will (?:ever )?care about you\b|\byou (?:are|'re) too weak\b|\byou do not deserve happiness\b|\byou (?:are|'re) responsible for making everyone\b[^.\n]{0,30}"
        ),
    ),
    (
        "emotional_abuse",
        ABUSE,
        _p(
            r"\byou should never make decisions without my approval\b|\bif you (?:really )?(?:cared|loved)\b[^.\n]{0,25}\byou would do (?:everything|anything|whatever)\b|\bi will make you believe\b|\bif you leave,? i will\b|\bunless you do exactly what i say\b"
        ),
    ),
)
