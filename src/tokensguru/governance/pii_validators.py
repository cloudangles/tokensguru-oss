"""The checks that tell real personal data from random digits.

A pattern alone ("16 digits") would flag order numbers and IDs all day. These
checks use the rules the real numbers follow, so a match is much more likely to be
real: the Luhn check digit and issuer prefix of a card, the mod-97 check of an
IBAN, the rules for a valid US social security number, and real calendar dates.
"""

from __future__ import annotations

import ipaddress
import re
from datetime import date

MIN_CARD = 13
MAX_CARD = 19
MIN_IBAN = 15
MAX_IBAN = 34
IBAN_MODULUS = 97
MIN_PHONE_DIGITS = 7
MAX_PHONE_DIGITS = 15
MIN_INTL_DIGITS = 8
OLDEST_YEAR = 1900
SSN_BAD_AREAS = frozenset({0, 666})
SSN_MAX_AREA = 899
TWO_DIGIT_YEAR_CUTOFF = 30
_MONTHS = {
    name: number
    for number, names in enumerate(
        (
            ("jan", "january"), ("feb", "february"), ("mar", "march"),
            ("apr", "april"), ("may",), ("jun", "june"), ("jul", "july"),
            ("aug", "august"), ("sep", "sept", "september"), ("oct", "october"),
            ("nov", "november"), ("dec", "december"),
        ),
        start=1,
    )
    for name in names
}  # fmt: skip
_CARD_PREFIXES = (
    re.compile(r"4"),
    re.compile(r"5[1-5]|2(?:2[2-9]\d|[3-6]\d\d|7[01]\d|720)"),
    re.compile(r"3[47]"),
    re.compile(r"6011|65|64[4-9]"),
    re.compile(r"35(?:2[89]|[3-8]\d)"),
    re.compile(r"3(?:0[0-5]|[689])"),
    re.compile(r"62"),
)
_NUMBER = re.compile(r"\d+")
_WORD = re.compile(r"[a-z]+")


def digits_only(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def luhn_valid(number: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(number)):
        digit = int(char)
        if index % 2:
            digit *= 2
            digit -= 9 if digit > 9 else 0  # noqa: PLR2004
        total += digit
    return total % 10 == 0


def credit_card_valid(value: str) -> bool:
    number = digits_only(value)
    if not MIN_CARD <= len(number) <= MAX_CARD or len(set(number)) == 1:
        return False
    if not any(prefix.match(number) for prefix in _CARD_PREFIXES):
        return False
    return luhn_valid(number)


def ssn_valid(area: str, group: str, serial: str) -> bool:
    if int(area) in SSN_BAD_AREAS or int(area) > SSN_MAX_AREA:
        return False
    return int(group) != 0 and int(serial) != 0


def iban_valid(value: str) -> bool:
    iban = value.replace(" ", "").upper()
    if not MIN_IBAN <= len(iban) <= MAX_IBAN or not iban[:2].isalpha():
        return False
    if not iban[2:4].isdigit() or not iban.isalnum():
        return False
    moved = iban[4:] + iban[:4]
    number = "".join(str(int(char, 36)) for char in moved)
    return int(number) % IBAN_MODULUS == 1


def ip_valid(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (address.is_unspecified or address.is_multicast)


def phone_digits_valid(value: str, minimum: int = MIN_PHONE_DIGITS) -> bool:
    count = len(digits_only(value))
    return minimum <= count <= MAX_PHONE_DIGITS and len(set(digits_only(value))) > 1


def _year(text: str) -> int | None:
    if len(text) == 4:  # noqa: PLR2004
        return int(text)
    if len(text) == 2:  # noqa: PLR2004
        year = int(text)
        return 2000 + year if year < TWO_DIGIT_YEAR_CUTOFF else 1900 + year
    return None


def _real_date(year: int, month: int, day: int) -> bool:
    try:
        parsed = date(year, month, day)
    except ValueError:
        return False
    return OLDEST_YEAR <= parsed.year <= date.today().year


def date_valid(value: str) -> bool:
    numbers = _NUMBER.findall(value)
    names = [_MONTHS[word] for word in _WORD.findall(value.lower()) if word in _MONTHS]
    if names and len(numbers) >= 2:  # noqa: PLR2004
        year = _year(numbers[-1])
        day = int(numbers[0] if len(numbers[0]) <= 2 else numbers[1])  # noqa: PLR2004
        return year is not None and _real_date(year, names[0], day)
    if len(numbers) != 3:  # noqa: PLR2004
        return False
    first, second, third = numbers
    if len(first) == 4:  # noqa: PLR2004
        return _real_date(int(first), int(second), int(third))
    year = _year(third)
    if year is None:
        return False
    return _real_date(year, int(second), int(first)) or _real_date(
        year, int(first), int(second)
    )
