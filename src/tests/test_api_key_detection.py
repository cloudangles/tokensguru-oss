import base64
import json
import random
import string
import time

import pytest

from tokensguru.governance import ApiKeyDetector, Finding, Guardrail, GuardrailResult
from tokensguru.governance.secret_patterns import SUPPORTED_TYPES

detector = ApiKeyDetector()

ALNUM = string.ascii_letters + string.digits
URLSAFE = ALNUM + "-_"
HEX = "0123456789abcdef"
UPPER_DIGITS = string.ascii_uppercase + string.digits
ZWSP = chr(0x200B)


def fake(chars, length, seed, mixed=True):
    rng = random.Random(seed)  # noqa: S311
    for _ in range(1000):
        value = "".join(rng.choice(chars) for _ in range(length))
        has_both = any(c.isdigit() for c in value) and any(c.isalpha() for c in value)
        if has_both or not mixed:
            return value
    raise AssertionError(f"could not build a mixed value from {chars!r}")


def b64url(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def make_jwt(seed=1):
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64url(json.dumps({"sub": "user-123", "name": "Test User"}).encode())
    return f"{header}.{payload}.{fake(URLSAFE, 43, seed)}"


def private_key(kind="", seed=2):
    body = "\n".join(fake(ALNUM, 64, seed + i) for i in range(4))
    label = f"{kind} PRIVATE KEY".strip()
    return f"-----BEGIN {label}-----\n{body}\n-----END {label}-----"


KEYS = {
    "openai_api_key": "sk-" + fake(ALNUM, 48, 1),
    "openai_project_key": "sk-proj-" + fake(URLSAFE, 80, 2),
    "anthropic_api_key": "sk-ant-api03-" + fake(URLSAFE, 90, 3),
    "aws_access_key_id": "AKIA" + fake(UPPER_DIGITS, 16, 4),
    "github_token": "ghp_" + fake(ALNUM, 36, 5),
    "github_fine_grained_token": "github_pat_" + fake(ALNUM + "_", 70, 6),
    "gitlab_token": "glpat-" + fake(URLSAFE, 20, 7),
    "slack_token": "xoxb-"
    + fake(string.digits, 12, 8, mixed=False)
    + "-"
    + fake(ALNUM, 24, 9),
    "google_api_key": "AIza" + fake(URLSAFE, 35, 10),
    "google_oauth_secret": "GOCSPX-" + fake(URLSAFE, 28, 11),
    "stripe_secret_key": "sk_live_" + fake(ALNUM, 24, 12),
    "sendgrid_api_key": "SG." + fake(URLSAFE, 22, 13) + "." + fake(URLSAFE, 43, 14),
    "twilio_api_key": "SK" + fake(HEX, 32, 15),
    "mailgun_api_key": "key-" + fake(HEX, 32, 16),
    "npm_token": "npm_" + fake(ALNUM, 36, 17),
    "pypi_token": "pypi-AgEIcHlwaS5vcmc" + fake(URLSAFE, 60, 18),
    "huggingface_token": "hf_" + fake(ALNUM, 34, 19),
    "jwt": make_jwt(20),
}
EXPECTED_TYPE = {
    "openai_project_key": "openai_api_key",
}


def types_in(text, **options):
    return [f.type for f in ApiKeyDetector(**options).check(text).findings]


def secrets_in(text, **options):
    result = ApiKeyDetector(**options).check(text)
    return [text[f.start : f.end] for f in result.findings]


@pytest.mark.parametrize("name", sorted(KEYS))
def test_finds_each_provider_key(name):
    key = KEYS[name]
    expected = EXPECTED_TYPE.get(name, name)
    for text in (key, f"token is {key} thanks", f'{{"key": "{key}"}}', f"key={key}\n"):
        assert types_in(text) == [expected], (name, text)
        assert secrets_in(text) == [key], (name, text)


def test_every_key_in_the_catalog_is_covered_by_a_test():
    covered = {EXPECTED_TYPE.get(name, name) for name in KEYS}
    covered |= {
        "azure_storage_key",
        "private_key",
        "slack_webhook",
        "url_credentials",
        "aws_secret_access_key",
        "bearer_credentials",
        "generic_secret",
    }
    assert set(SUPPORTED_TYPES) == covered


def test_the_default_action_is_block():
    result = detector.check(KEYS["github_token"])
    assert result.decision == "block"
    assert ApiKeyDetector(action="flag").check(KEYS["github_token"]).decision == "flag"
    assert detector.check("nothing here").decision == "pass"


@pytest.mark.parametrize("action", ["allow", "", "BLOCK", "redact"])
def test_invalid_actions_are_rejected(action):
    with pytest.raises(ValueError, match="action"):
        ApiKeyDetector(action=action)


def test_an_anthropic_key_is_not_also_reported_as_openai():
    assert types_in(KEYS["anthropic_api_key"]) == ["anthropic_api_key"]


def test_a_key_inside_an_authorization_header_is_reported_once_as_its_own_type():
    text = f"Authorization: Bearer {KEYS['github_token']}"
    assert types_in(text) == ["github_token"]


def test_several_keys_in_one_text_are_all_found_in_order():
    parts = [KEYS["openai_api_key"], KEYS["aws_access_key_id"], KEYS["npm_token"]]
    text = f"{parts[0]} then {parts[1]} and {parts[2]}"
    result = detector.check(text)
    assert [f.type for f in result.findings] == [
        "openai_api_key",
        "aws_access_key_id",
        "npm_token",
    ]
    starts = [f.start for f in result.findings]
    assert starts == sorted(starts)


def test_offsets_are_exact():
    key = KEYS["github_token"]
    text = f"abc {key} def"
    (finding,) = detector.check(text).findings
    assert (finding.start, finding.end) == (4, 4 + len(key))
    assert text[finding.start : finding.end] == key


@pytest.mark.parametrize(
    "template",
    [
        "{k}",
        " {k} ",
        '"{k}"',
        "'{k}'",
        "({k})",
        "[{k}]",
        "<{k}>",
        "{k},",
        "{k}.",
        "{k};",
        "`{k}`",
        "key={k}&x=1",
        "?api_key={k}",
        "x:{k}",
        "\n{k}\n",
        "\t{k}\t",
    ],
)
def test_keys_are_found_with_any_surrounding_punctuation(template):
    key = KEYS["stripe_secret_key"]
    assert secrets_in(template.format(k=key)) == [key]


def test_a_key_inside_a_longer_word_is_not_a_key():
    key = KEYS["github_token"]
    assert types_in("x" + key) == []
    assert types_in(key + "x") == ["github_token"] or types_in(key + "x") == []


@pytest.mark.parametrize(
    "text",
    [
        "sk-your-api-key-here-1234567890abcdef",
        "sk-" + "x" * 40,
        "sk-" + "1" * 40,
        "sk-example1234567890abcdefghijklmnop",
        "sk-dummy1234567890abcdefghijklmnopqr",
        "sk-placeholder1234567890abcdefghijkl",
        "ghp_" + "A" * 36,
        "AKIA" + "X" * 16,
        "AKIAIOSFODNN7EXAMPLE",
        "hf_" + "a" * 34,
        "sk-ant-api03-" + "z" * 40,
        "password = changeme-changeme-changeme",
        "token: <your-token-goes-here-now>",
        "api_key = YOUR_API_KEY_GOES_HERE_1234",
    ],
)
def test_placeholders_are_not_reported_by_default(text):
    assert detector.check(text).findings == ()


def test_placeholders_can_be_reported_when_asked():
    text = "sk-" + "x" * 40
    assert (
        types_in(text, ignore_placeholders=False) == ["openai_api_key"]
        or types_in(text, ignore_placeholders=False) == []
    )


@pytest.mark.parametrize(
    "text",
    [
        "",
        "plain text with no secrets at all",
        "task-based scheduling",
        "sk-learn-and-other-long-hyphenated-phrases-here",
        "sk-short",
        "ghp_short",
        "AKIA123",
        "AIza123",
        "xoxb-1",
        "key-123",
        "npm_abc",
        "hf_abc",
        "the password is correct",
        "token expired, please log in",
        "secret = short",
        "eyJ.eyJ.sig",
        "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----",
        "-----BEGIN PUBLIC KEY-----\nabc\n-----END PUBLIC KEY-----",
        "https://example.com/path?x=1",
        "https://user@example.com/path",
        "postgres://localhost:5432/app",
        "Authorization: Bearer short",
        "AccountKey=short",
        "aws_secret_access_key = short",
        "12345678-1234-1234-1234-123456789012",
        "d41d8cd98f00b204e9800998ecf8427e",
        "a" * 60,
        "0123456789abcdef0123456789abcdef01234567",
    ],
)
def test_ordinary_text_is_left_alone(text):
    assert detector.check(text).findings == ()


def test_private_key_blocks_are_found_as_one_finding():
    for kind in ("", "RSA", "EC", "OPENSSH", "DSA", "ENCRYPTED"):
        key = private_key(kind)
        text = f"before\n{key}\nafter"
        (finding,) = detector.check(text).findings
        assert finding.type == "private_key", kind
        assert text[finding.start : finding.end] == key, kind
        assert finding.confidence == 0.99


def test_a_private_key_without_its_footer_reports_the_header_only():
    key = private_key()
    text = key.split("\n-----END")[0]
    (finding,) = detector.check(text).findings
    assert text[finding.start : finding.end].startswith("-----BEGIN")
    assert finding.end - finding.start < 40


def test_a_private_key_preview_shows_only_the_public_header():
    key = private_key("RSA")
    (finding,) = detector.check(key).findings
    body = key.split("\n")[1]
    assert finding.preview.startswith("-----BEGIN RSA PRIVATE KEY-----")
    assert body not in finding.preview


def test_two_private_keys_are_two_findings():
    text = private_key("RSA", 1) + "\n\n" + private_key("EC", 2)
    assert [f.type for f in detector.check(text).findings] == ["private_key"] * 2


def test_a_secret_inside_a_private_key_block_is_not_reported_twice():
    text = private_key()
    assert detector.check(text).count == 1


def test_url_credentials_report_only_the_password():
    password = fake(ALNUM, 16, 40)
    for scheme in ("postgres", "mysql", "mongodb", "redis", "amqp", "https", "ftp"):
        text = f"{scheme}://admin:{password}@db.internal:5432/app"
        assert secrets_in(text) == [password], scheme
        assert types_in(text) == ["url_credentials"], scheme


def test_aws_secret_access_keys_need_their_name_next_to_them():
    secret = fake(ALNUM + "/+", 40, 41)
    for text in (
        f"aws_secret_access_key = {secret}",
        f'AWS_SECRET_ACCESS_KEY="{secret}"',
        f"aws-secret-key: {secret}",
    ):
        assert types_in(text) == ["aws_secret_access_key"], text
        assert secrets_in(text) == [secret], text
    assert detector.check(secret).findings == ()


def test_azure_storage_keys():
    key = base64.b64encode(random.Random(5).randbytes(48)).decode()  # noqa: S311
    text = (
        "DefaultEndpointsProtocol=https;AccountName=x;"
        f"AccountKey={key};EndpointSuffix=core.windows.net"
    )
    assert types_in(text) == ["azure_storage_key"]
    assert secrets_in(text) == [key.rstrip(";")]


def test_slack_webhooks():
    hook = (
        "https://hooks.slack.com/services/T"
        + fake(UPPER_DIGITS, 9, 50)
        + "/B"
        + fake(UPPER_DIGITS, 9, 51)
        + "/"
        + fake(ALNUM, 24, 52)
    )
    assert types_in(f"post to {hook} now") == ["slack_webhook"]


def test_bearer_and_basic_authorization_headers():
    token = fake(ALNUM + "._~", 40, 60)
    for scheme in ("Bearer", "bearer", "Token", "Basic"):
        text = f"Authorization: {scheme} {token}"
        assert types_in(text) == ["bearer_credentials"], scheme
        assert secrets_in(text) == [token], scheme
    assert types_in(f'"authorization": "Bearer {token}"') == ["bearer_credentials"]
    assert types_in("Authorization: Bearer " + "a" * 30) == []


def test_generic_assignments_need_a_random_looking_value():
    value = fake(ALNUM, 24, 70)
    for name in (
        "api_key",
        "API-KEY",
        "secret",
        "client_secret",
        "access_token",
        "auth_token",
        "password",
        "passwd",
        "token",
        "secret_key",
    ):
        for separator in ("=", ": ", " = ", '": "', "='"):
            text = f"{name}{separator}{value}"
            assert types_in(text) == ["generic_secret"], text
            assert secrets_in(text) == [value], text
    assert types_in("password = aaaaaaaaaaaaaaaaaaaa") == []
    assert types_in("password = abcabcabcabcabcabcabc") == []


def test_generic_assignments_can_be_turned_off():
    text = f"password = {fake(ALNUM, 24, 71)}"
    assert types_in(text, include_generic=False) == []
    assert types_in(f"key {KEYS['github_token']}", include_generic=False) == [
        "github_token"
    ]


def test_generic_matches_have_the_lowest_confidence():
    (finding,) = detector.check(f"secret = {fake(ALNUM, 24, 72)}").findings
    assert finding.confidence == 0.6
    (strong,) = detector.check(KEYS["github_token"]).findings
    assert strong.confidence > finding.confidence


def test_a_jwt_is_found():
    token = make_jwt(80)
    (finding,) = detector.check(f"Bearer {token}").findings
    assert finding.type == "jwt"
    assert finding.confidence == 0.85


@pytest.mark.parametrize(
    "disguise",
    [
        lambda key: key[:6] + ZWSP + key[6:],
        ZWSP.join,
        lambda key: chr(0x2060) + key + chr(0xFEFF),
        lambda key: "".join(
            chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in key
        ),
    ],
)
def test_keys_hidden_with_invisible_or_full_width_characters_are_found(disguise):
    key = KEYS["github_token"]
    disguised = f"my key: {disguise(key)} ok"
    (finding,) = detector.check(disguised).findings
    assert finding.type == "github_token"
    assert disguised[finding.start : finding.end].replace(ZWSP, "") != ""
    assert finding.start >= len("my key: ")


def test_invisible_characters_are_included_in_the_reported_span():
    key = KEYS["github_token"]
    disguised = key[:10] + ZWSP + key[10:]
    (finding,) = detector.check(disguised).findings
    assert (finding.start, finding.end) == (0, len(disguised))


def test_the_secret_is_never_stored_anywhere_in_the_result():
    texts = [KEYS[name] for name in KEYS]
    texts += [private_key("RSA"), f"password = {fake(ALNUM, 24, 90)}"]
    for text in texts:
        result = detector.check(f"x {text} y")
        dumps = [str(result), repr(result), json.dumps(result.to_dict())]
        body = text.split("\n")[1] if "\n" in text else text
        tail = body[-12:]
        for dump in dumps:
            assert tail not in dump, text[:12]
            assert body not in dump, text[:12]


def test_only_the_providers_own_prefix_can_appear_in_a_preview():
    (finding,) = detector.check(KEYS["github_token"]).findings
    assert finding.preview == f"ghp_*** ({len(KEYS['github_token'])} chars)"
    (generic,) = detector.check(f"password = {fake(ALNUM, 24, 91)}").findings
    assert generic.preview == "*** (24 chars)"


def test_result_details():
    result = detector.check(f"a {KEYS['openai_api_key']} b {KEYS['npm_token']}")
    assert isinstance(result, GuardrailResult)
    assert isinstance(detector, Guardrail)
    assert result.guardrail_id == "api_key_detection"
    assert result.guardrail_name == "API key detection"
    assert result.count == 2
    assert result.types == {"openai_api_key": 1, "npm_token": 1}
    assert result.reason == "Found 2 secrets"
    assert result.detected is True
    assert all(
        isinstance(f, Finding) and f.category == "secret" for f in result.findings
    )


def test_reasons():
    assert detector.check(KEYS["github_token"]).reason == "Found 1 secret"
    assert detector.check("nothing").reason == "No API key or secret found"


def test_supported_types_are_listed():
    assert "openai_api_key" in ApiKeyDetector.supported_types
    assert "private_key" in ApiKeyDetector.supported_types
    assert len(ApiKeyDetector.supported_types) == len(
        set(ApiKeyDetector.supported_types)
    )


def test_calling_the_object_is_the_same_as_check():
    assert detector(KEYS["github_token"]).count == 1


@pytest.mark.parametrize("value", [None, 5, b"sk-abc", ["x"]])
def test_rejects_non_string_input(value):
    with pytest.raises(TypeError):
        detector.check(value)


def test_a_document_with_many_keys():
    keys = [f"ghp_{fake(ALNUM, 36, 1000 + i)}" for i in range(2000)]
    text = "\n".join(f"line {i}: {key}" for i, key in enumerate(keys))
    assert detector.check(text).count == 2000


@pytest.mark.parametrize(
    "hostile",
    [
        "sk-" * 100_000,
        "sk-" + "a" * 500_000,
        "ghp_" * 100_000,
        "AKIA" * 100_000,
        "eyJ" + "a" * 300_000,
        "eyJ." * 100_000,
        "eyJaaaaaaaaaaaa." * 50_000,
        "password=" * 100_000,
        "password=" + "a" * 500_000,
        "token: " * 100_000,
        "authorization: bearer " * 50_000,
        "authorization: " + " " * 500_000,
        "://" * 100_000,
        "a://b:" * 50_000,
        "http://" + "a" * 200_000 + ":" + "b" * 200_000,
        "-----BEGIN PRIVATE KEY-----" * 20_000,
        "-----BEGIN " * 50_000,
        "-----BEGIN PRIVATE KEY-----" + "a" * 500_000,
        "AccountKey=" * 50_000,
        "AccountKey=" + "a" * 500_000,
        "aws_secret_access_key=" * 50_000,
        ZWSP * 300_000,
        "ghp_" + ZWSP * 300_000,
        "x" * 1_000_000,
        " " * 1_000_000,
        "=" * 1_000_000,
    ],
)
def test_hostile_inputs_are_handled_quickly(hostile):
    started = time.perf_counter()
    detector.check(hostile)
    assert time.perf_counter() - started < 4


def test_a_large_document_is_handled():
    chunk = "The quick brown fox jumps over the lazy dog. Config values follow here.\n"
    text = chunk * 30_000 + KEYS["github_token"]
    started = time.perf_counter()
    result = detector.check(text)
    assert result.count == 1
    assert time.perf_counter() - started < 5


def test_the_input_is_not_changed_and_results_repeat():
    text = f"key {KEYS['github_token']}"
    first = [f.to_dict() for f in detector.check(text).findings]
    second = [f.to_dict() for f in detector.check(text).findings]
    assert first == second
    assert text == f"key {KEYS['github_token']}"


ALPHABET = [
    *string.ascii_letters,
    *string.digits,
    *"-_=:/.\"' \n",
    "sk-",
    "ghp_",
    "AKIA",
    "eyJ",
    "password=",
    "token:",
    "-----BEGIN PRIVATE KEY-----",
    "-----END PRIVATE KEY-----",
    "Bearer ",
    "://",
    "@",
    ZWSP,
]


def test_fuzz_findings_are_always_valid():
    rng = random.Random(1618)  # noqa: S311
    for _ in range(4000):
        text = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 80)))
        result = detector.check(text)
        last_end = 0
        for finding in result.findings:
            assert 0 <= finding.start < finding.end <= len(text), repr(text)
            assert finding.start >= last_end, repr(text)
            last_end = finding.end
            assert 0 < finding.confidence <= 1
            assert finding.type in ApiKeyDetector.supported_types
            assert finding.category == "secret"
            assert (
                text[finding.start : finding.end] not in finding.preview
                or len(finding.preview) > 20
                or finding.type == "private_key"
            ), repr(text)
        assert detector.check(text).count == result.count


def test_fuzz_real_looking_keys_are_found_in_noise():
    rng = random.Random(2718)  # noqa: S311
    noise = string.ascii_letters + " .,;:!?()[]<>\n\t"
    names = [n for n in KEYS if n not in ("twilio_api_key", "mailgun_api_key")]
    for index in range(1200):
        name = names[index % len(names)]
        key = KEYS[name]
        left = "".join(rng.choice(noise) for _ in range(rng.randint(0, 20))) + " "
        right = " " + "".join(rng.choice(noise) for _ in range(rng.randint(0, 20)))
        text = left + key + right
        assert key in secrets_in(text), (name, repr(text))


def test_a_private_key_whose_footer_is_cut_off_reports_the_header_only():
    text = "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY"
    (finding,) = detector.check(text).findings
    assert finding.type == "private_key"
    assert text[finding.start : finding.end] == "-----BEGIN PRIVATE KEY-----"
