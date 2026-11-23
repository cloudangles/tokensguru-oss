# ruff: noqa: S104
import json
import random
import string
import time

import pytest

from tokensguru.governance import Guardrail, GuardrailResult, PiiDetector
from tokensguru.governance.pii_validators import (
    credit_card_valid,
    date_valid,
    iban_valid,
    ip_valid,
    luhn_valid,
    phone_digits_valid,
    ssn_valid,
)

detector = PiiDetector()
ZWSP = chr(0x200B)


def kinds(text, **options):
    return [f.type for f in PiiDetector(**options).check(text).findings]


def values(text, **options):
    result = PiiDetector(**options).check(text)
    return [text[f.start : f.end] for f in result.findings]


VALID_CARDS = [
    "4111 1111 1111 1111",
    "4111-1111-1111-1111",
    "4111111111111111",
    "5555 5555 5555 4444",
    "2223 0031 2200 3222",
    "3782 822463 10005",
    "378282246310005",
    "6011 1111 1111 1117",
    "3530 1113 3330 0000",
    "3056 9309 0259 04",
    "6200 0000 0000 0005",
    "4012 8888 8888 1881",
    "4222 2222 2222 2",
]


@pytest.mark.parametrize("card", VALID_CARDS)
def test_finds_valid_cards(card):
    assert kinds(f"pay with {card} now") == ["credit_card"]
    assert values(f"pay with {card} now") == [card]


@pytest.mark.parametrize(
    "number",
    [
        "4111 1111 1111 1112",
        "1234 5678 9012 3456",
        "0000 0000 0000 0000",
        "1111 1111 1111 1111",
        "4111 1111 1111",
        "41111111111111111111",
        "1234567890123456",
        "9999999999999995",
    ],
)
def test_ignores_numbers_that_are_not_valid_cards(number):
    assert "credit_card" not in kinds(f"order {number} shipped")


@pytest.mark.parametrize(
    "iban",
    [
        "GB82 WEST 1234 5698 7654 32",
        "GB82WEST12345698765432",
        "DE89 3704 0044 0532 0130 00",
        "FR14 2004 1010 0505 0001 3M02 606",
        "ES91 2100 0418 4502 0005 1332",
        "NL91 ABNA 0417 1643 00",
        "IT60 X054 2811 1010 0000 0123 456",
        "CH93 0076 2011 6238 5295 7",
    ],
)
def test_finds_valid_ibans(iban):
    assert kinds(f"account {iban}.") == ["iban"]


@pytest.mark.parametrize(
    "text",
    ["GB82 WEST 1234 5698 7654 33", "XX00 1234 5678 9012", "GB82", "AB12 CD34"],
)
def test_ignores_invalid_ibans(text):
    assert "iban" not in kinds(text)


@pytest.mark.parametrize(
    "text",
    [
        "123-45-6789",
        "123 45 6789",
        "SSN 123456789",
        "social security number: 123456789",
    ],
)
def test_finds_social_security_numbers(text):
    assert "ssn" in kinds(text)


@pytest.mark.parametrize(
    "text",
    [
        "000-45-6789",
        "666-45-6789",
        "923-45-6789",
        "123-00-6789",
        "123-45-0000",
        "123456789",
        "12-345-6789",
    ],
)
def test_ignores_invalid_social_security_numbers(text):
    assert "ssn" not in kinds(text)


@pytest.mark.parametrize(
    "phone",
    [
        "+44 20 7946 0958",
        "+1 212 555 0147",
        "+1-212-555-0147",
        "+33 1 42 68 53 00",
        "+49 30 901820",
        "(212) 555-0147",
        "212-555-0147",
        "212.555.0147",
        "1-212-555-0147",
        "+91 98765 43210",
    ],
)
def test_finds_phone_numbers(phone):
    assert kinds(f"call {phone} today") == ["phone"]


@pytest.mark.parametrize(
    "label", ["phone", "Phone", "tel", "Mobile", "cell", "fax", "WhatsApp"]
)
def test_finds_unformatted_numbers_after_a_phone_word(label):
    assert kinds(f"{label}: 0123 456 789") == ["phone"]
    assert kinds(f"{label} 07700 900123") == ["phone"]


@pytest.mark.parametrize(
    "text",
    [
        "2125550147",
        "order 1234567",
        "ref 20240115",
        "version 3.10.4",
        "id 555-0147",
        "+1",
        "+123",
        "0123 456 789",
        "phone: 111111111",
        "call 1-1",
    ],
)
def test_ignores_digits_that_are_not_phone_numbers(text):
    assert "phone" not in kinds(text)


@pytest.mark.parametrize(
    "address",
    [
        "192.168.1.10",
        "8.8.8.8",
        "10.0.0.1",
        "127.0.0.1",
        "255.255.255.255",
        "2001:db8::1",
        "fe80::1",
        "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
    ],
)
def test_finds_ip_addresses(address):
    assert kinds(f"host {address} is up.") == ["ip_address"]


@pytest.mark.parametrize(
    "text",
    [
        "999.1.1.1",
        "1.2.3",
        "1.2.3.4.5",
        "01.02.03.04",
        "12:30:45",
        "::",
        "10:20",
        "0.0.0.0",
        "ab:cd",
        "v1.2.3.4.5",
    ],
)
def test_ignores_things_that_are_not_ip_addresses(text):
    assert "ip_address" not in kinds(text)


def test_private_addresses_can_be_left_out():
    text = "a 10.0.0.1 b 192.168.0.5 c 127.0.0.1 d 8.8.8.8 e fe80::1"
    assert len(values(text)) == 5
    assert values(text, include_private_ips=False) == ["8.8.8.8"]


@pytest.mark.parametrize(
    "text",
    [
        "DOB: 1990-03-12",
        "dob 12/03/1990",
        "D.O.B. 31/12/1985",
        "date of birth: 12 March 1990",
        "Date of Birth - March 12, 1990",
        "born on 3rd Feb 1988",
        "birthday: 12.03.90",
    ],
)
def test_finds_birth_dates_next_to_a_birth_word(text):
    assert "date_of_birth" in kinds(text)


@pytest.mark.parametrize(
    "text",
    [
        "1990-03-12",
        "meeting on 12/03/2026",
        "DOB: 32/13/1990",
        "DOB: 1850-01-01",
        "DOB: 2999-01-01",
        "born in 1990",
        "DOB: unknown",
    ],
)
def test_ignores_dates_that_are_not_birth_dates(text):
    assert "date_of_birth" not in kinds(text)


@pytest.mark.parametrize(
    "text",
    [
        "passport: X1234567",
        "Passport No. 123456789",
        "passport number A12345678",
        "passport #L898902C",
    ],
)
def test_finds_passport_numbers_after_the_word_passport(text):
    assert "passport" in kinds(text)


@pytest.mark.parametrize(
    "text", ["passport: ABCDEFGH", "passport control", "passport 123", "X1234567"]
)
def test_ignores_other_uses_of_passport(text):
    assert "passport" not in kinds(text)


def test_emails_are_included_and_masked():
    result = detector.check("mail jane.doe@example.com")
    (finding,) = result.findings
    assert (finding.type, finding.preview) == ("email", "j***@example.com")


def test_allowed_email_domains_are_passed_through():
    assert kinds("a@corp.io b@other.com", allowed_domains=["corp.io"]) == ["email"]


def test_everything_in_one_text_with_exact_positions():
    text = (
        "Card 4111 1111 1111 1111, SSN 123-45-6789, call (212) 555-0147, "
        "mail jane@example.com, host 8.8.8.8, DOB: 12/03/1990."
    )
    result = detector.check(text)
    assert [f.type for f in result.findings] == [
        "credit_card",
        "ssn",
        "phone",
        "email",
        "ip_address",
        "date_of_birth",
    ]
    assert values(text) == [
        "4111 1111 1111 1111",
        "123-45-6789",
        "(212) 555-0147",
        "jane@example.com",
        "8.8.8.8",
        "12/03/1990",
    ]
    starts = [f.start for f in result.findings]
    assert starts == sorted(starts)


def test_a_card_is_not_also_reported_as_a_phone():
    assert kinds("4111 1111 1111 1111") == ["credit_card"]
    assert kinds("+1 212 555 0147 and 123-45-6789") == ["phone", "ssn"]


def test_only_the_chosen_types_are_reported():
    text = "jane@example.com 4111 1111 1111 1111 8.8.8.8"
    assert kinds(text, types=["email"]) == ["email"]
    assert kinds(text, types=["credit_card", "ip_address"]) == [
        "credit_card",
        "ip_address",
    ]


def test_unknown_types_are_rejected():
    with pytest.raises(ValueError, match="unknown PII types"):
        PiiDetector(types=["email", "dna"])


@pytest.mark.parametrize(
    "text",
    [
        "j\u200ba\u200bne@example.com",
        "4111\u200b1111\u200b1111\u200b1111",
        "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in "123-45-6789"),
    ],
)
def test_disguised_values_are_found(text):
    assert len(detector.check(text).findings) == 1


def test_masked_previews_never_show_the_full_value():
    checks = {
        "credit_card": ("4111 1111 1111 1111", "**** **** **** 1111"),
        "ssn": ("123-45-6789", "***-**-6789"),
        "phone": ("(212) 555-0147", "(***) ***-0147"),
        "ip_address": ("192.168.1.10", "192.168.*.*"),
        "date_of_birth": ("DOB: 12/03/1990", "**/**/****"),
    }
    for kind, (text, preview) in checks.items():
        (finding,) = [f for f in detector.check(text).findings if f.type == kind]
        assert finding.preview == preview, kind


def test_no_personal_data_is_stored_in_the_result():
    text = (
        "Card 4111 1111 1111 1111 SSN 123-45-6789 phone (212) 555-0147 "
        "mail very.private@example.com IBAN GB82 WEST 1234 5698 7654 32 "
        "DOB: 12/03/1990 passport: X1234567 host 203.0.113.77"
    )
    result = detector.check(text)
    dumped = json.dumps(result.to_dict()) + str(result) + repr(result)
    for secret in (
        "4111 1111 1111 1111",
        "555-0147",
        "very.private",
        "7654 32",
        "12/03/1990",
        "X1234567",
        "203.0.113.77",
    ):
        assert secret not in dumped, secret


def test_result_details():
    result = detector.check("jane@example.com and 8.8.8.8")
    assert isinstance(result, GuardrailResult)
    assert isinstance(detector, Guardrail)
    assert result.guardrail_id == "pii_detection"
    assert result.guardrail_name == "PII detection"
    assert (result.decision, result.count) == ("flag", 2)
    assert result.reason == "Found 2 pieces of personal data"
    assert detector.check("nothing").reason == "No personal data found"
    assert PiiDetector(action="block").check("8.8.8.8").decision == "block"
    assert PiiDetector.supported_types == (
        "credit_card", "iban", "ssn", "email", "phone", "ip_address",
        "date_of_birth", "passport",
    )  # fmt: skip


@pytest.mark.parametrize("value", [None, 5, b"x", ["x"]])
def test_rejects_non_string_input(value):
    with pytest.raises(TypeError):
        detector.check(value)


def test_validators():
    assert luhn_valid("4111111111111111") and not luhn_valid("4111111111111112")
    assert credit_card_valid("4111 1111 1111 1111")
    assert not credit_card_valid("1111111111111111")
    assert iban_valid("GB82 WEST 1234 5698 7654 32") and not iban_valid("GB00")
    assert not iban_valid("1234 5678 9012 3456")
    assert ssn_valid("123", "45", "6789") and not ssn_valid("666", "45", "6789")
    assert ip_valid("1.2.3.4") and not ip_valid("1.2.3") and not ip_valid("::")
    assert phone_digits_valid("+44 20 7946 0958") and not phone_digits_valid(
        "111111111"
    )
    assert (
        date_valid("1990-03-12") and date_valid("12 Mar 1990") and not date_valid("x")
    )
    assert (
        date_valid("March 5, 90")
        and not date_valid("1/1")
        and not date_valid("12 March")
    )


@pytest.mark.parametrize(
    "hostile",
    [
        "1" * 500_000,
        "1 " * 250_000,
        "1-" * 250_000,
        "+" + "1" * 500_000,
        "+1 " * 150_000,
        "(" * 300_000,
        "1." * 250_000,
        "::" * 250_000,
        ":" * 500_000,
        "a:" * 250_000,
        "GB82" * 100_000,
        "GB82 " * 100_000,
        "DOB: " * 100_000,
        "DOB: 1" + "/1" * 100_000,
        "passport " * 100_000,
        "phone: " + "1 " * 100_000,
        "ssn " * 100_000,
        "123-45-" * 100_000,
        ZWSP * 300_000,
        "4" + ZWSP + "1" * 200_000,
    ],
)
def test_hostile_inputs_are_handled_quickly(hostile):
    started = time.perf_counter()
    detector.check(hostile)
    assert time.perf_counter() - started < 4


def test_a_large_document_is_handled():
    text = "Quarterly figures were stable. Contact: ops@example.com. " * 20_000
    started = time.perf_counter()
    assert detector.check(text).count == 20_000
    assert time.perf_counter() - started < 6


ALPHABET = [
    *string.digits,
    *"-+(). :/@\n",
    "DOB:",
    "phone",
    "4111 1111 1111 1111",
    "123-45-6789",
    "8.8.8.8",
    "a@b.com",
    "passport",
    ZWSP,
]


def test_fuzz_findings_are_always_valid_and_do_not_overlap():
    rng = random.Random(1123)  # noqa: S311
    for _ in range(3000):
        text = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 60)))
        result = detector.check(text)
        last_end = 0
        for finding in result.findings:
            assert 0 <= finding.start < finding.end <= len(text), repr(text)
            assert finding.start >= last_end, repr(text)
            last_end = finding.end
            assert finding.type in PiiDetector.supported_types
            assert finding.category == "pii"
            assert 0 < finding.confidence <= 1
        assert detector.check(text).count == result.count
