"""The sample inputs used to measure each optimizer.

They are small, realistic and fixed, so the numbers are repeatable. Every set mixes
inputs the optimizer can shorten with inputs it cannot (already clean text, or text
it deliberately leaves alone), so the average is not flattered. Real savings depend
entirely on your own data.
"""

# ruff: noqa: E501
from __future__ import annotations

import json
from typing import Any

_WIDE = " " * 30

_ORDER_ITEMS = [
    {
        "id": 101,
        "customer": "Ana Lopez",
        "total": 249.99,
        "paid": True,
        "items": ["keyboard", "cable"],
    },
    {
        "id": 102,
        "customer": "Raj Patel",
        "total": 19.5,
        "paid": False,
        "items": ["mouse"],
    },
    {
        "id": 103,
        "customer": "Mei Chen",
        "total": 1200.0,
        "paid": True,
        "items": ["monitor", "stand", "cable"],
    },
]

_SYSTEM_PROMPT = (
    "You are a helpful support assistant for an online store. Answer politely and "
    "concisely, never share customer passwords or payment details, and always cite "
    "the help-center article you used."
)

_DISCLAIMER = (
    "This message and any attachments are confidential and intended only for the "
    "named recipient. If you received it in error, please delete it and notify the "
    "sender. Any unauthorized use or disclosure is prohibited."
)

_INTRO = (
    "The launch date is set for the first week of March, pending final approval from "
    "the legal team and confirmation of the marketing budget for the quarter."
)

WHITESPACE: dict[str, str] = {
    "Support chat export": (
        "Customer: Hi, my order has not arrived yet.   \n\n\n\n"
        "Agent: Sorry to hear that.  Could you share the order number?   \n\n\n\n\n"
        "Customer: It is 48213.   \n\n\n\n"
        "Agent: Thanks.   I can see it shipped on Monday and should arrive tomorrow.   \n"
    ),
    "Email pasted from a web page": (
        "Hello  team,   \n\n\n\n"
        "Please  find   the  updated  schedule   below.    \n\n\n\n\n"
        "Kickoff    is  on   Tuesday    at  10am.    \n\n\n\n"
        "Thanks,     \nPriya   \n"
    ),
    "Text extracted from a PDF": (
        f"Quarterly report{_WIDE}Q3 2026\n\n\n\n"
        f"Revenue grew{_WIDE}8% over the previous quarter.\n\n\n\n"
        f"Operating costs{_WIDE}were flat.\n"
    ),
    "Markdown with a code block": (
        "# Setup   \n\n\n\nInstall  the  package:   \n\n```\npip   install    tokensguru\n```\n\n\n\n"
        "Then  run   the   command   below.   \n"
    ),
    "Meeting notes": (
        "Notes from Monday   \n\n\n- Review the roadmap   \n- Assign owners  \n\n\n\n"
        "Next meeting:    Friday   \n"
    ),
    "Already clean text": (
        "This text is already clean.\n\nIt has normal spacing and no repeated blank lines.\n"
    ),
}

PARAGRAPHS: dict[str, str] = {
    "Report with a pasted intro": f"{_INTRO}\n\nBudget details follow in section two.\n\n{_INTRO}\n\nRisks are listed in section three.\n\n{_INTRO}\n",
    "Email thread with disclaimers": (
        f"Hi Sam, the contract is attached for review.\n\n{_DISCLAIMER}\n\n"
        f"Thanks Priya, I will sign it today.\n\n{_DISCLAIMER}\n\n"
        f"Great, please send it back by Friday.\n\n{_DISCLAIMER}\n"
    ),
    "Article with a repeated summary": (
        "Summary: the new pricing page increased sign-ups by twelve percent in the first month, "
        "with the largest gain among small teams.\n\n"
        "The test ran for four weeks across all regions and used a random split of visitors.\n\n"
        "Summary: the new pricing page increased sign-ups by twelve percent in the first month, "
        "with the largest gain among small teams.\n"
    ),
    "Unique paragraphs": (
        "The first paragraph introduces the topic and sets out the main question for the reader.\n\n"
        "The second paragraph gives the background and explains why the question matters now.\n\n"
        "The third paragraph describes the method and the data that were used in the study.\n"
    ),
    "Short repeated lines": "Thanks.\n\nOK.\n\nThanks.\n\nOK.\n\nThanks.\n",
    "Repeated product description": (
        "Our standard plan includes unlimited projects, daily backups and email support for every team.\n\n"
        "Pricing\n\nOur standard plan includes unlimited projects, daily backups and email support for every team.\n\n"
        "FAQ\n\nOur standard plan includes unlimited projects, daily backups and email support for every team.\n"
    ),
}

BULLETS: dict[str, str] = {
    "System prompt with repeated rules": (
        "Follow these rules:\n- Be concise and polite\n- Be concise and polite\n- Be concise and polite\n"
        "- Never share customer passwords\n- Always cite the help-center article\n- Always cite the help-center article\n"
    ),
    "Checklist with a pasted line": (
        "Before release:\n- Run the test suite\n- Update the changelog\n- Update the changelog\n- Tag the release\n"
    ),
    "Requirements without repeats": (
        "Requirements:\n- Python 3.9 or newer\n- Network access for the first run\n- About 50 MB of free disk space\n"
    ),
    "Same bullet, not adjacent": (
        "Todo:\n- Write the report\n- Send the invoice\n- Write the report\n- Book the venue\n"
    ),
    "Nested list with a repeat": (
        "Plan:\n- Backend\n  - Add the endpoint\n  - Add the endpoint\n  - Write the tests\n- Frontend\n  - Build the form\n"
    ),
    "Release notes with a repeat": (
        "Changes:\n- Fixed a crash on startup\n- Improved the error messages\n- Improved the error messages\n- Updated the docs\n"
    ),
}

JSON_TEXT: dict[str, str] = {
    "API response, 4-space indent": json.dumps(
        {"status": "ok", "total": 3, "orders": _ORDER_ITEMS}, indent=4
    ),
    "List of records, 2-space indent": json.dumps(_ORDER_ITEMS, indent=2),
    "Config file, tab indent": json.dumps(
        {
            "name": "service",
            "retries": 3,
            "regions": ["eu", "us"],
            "limits": {"rps": 50, "burst": 100},
        },
        indent="\t",
    ),
    "Deeply nested object": json.dumps(
        {"a": {"b": {"c": {"d": {"e": [1, 2, 3], "f": "value"}}}}}, indent=2
    ),
    "Already minified JSON": json.dumps(
        {"status": "ok", "items": [1, 2, 3]}, separators=(",", ":")
    ),
    "Plain text, not JSON": "This is a normal sentence and not a JSON document, so nothing can be minified.",
}


def _messages(*roles_and_text: tuple[str, str]) -> list[dict[str, Any]]:
    return [{"role": role, "content": text} for role, text in roles_and_text]


SYSTEM_MESSAGES: dict[str, list[dict[str, Any]]] = {
    "Agent loop adding the prompt each step": _messages(
        ("system", _SYSTEM_PROMPT),
        ("system", _SYSTEM_PROMPT),
        ("system", _SYSTEM_PROMPT),
        ("user", "Where is my order 48213?"),
    ),
    "System prompt sent once": _messages(
        ("system", _SYSTEM_PROMPT), ("user", "Where is my order 48213?")
    ),
    "Two identical system messages": _messages(
        ("system", _SYSTEM_PROMPT),
        ("system", _SYSTEM_PROMPT),
        ("user", "Hello"),
        ("assistant", "Hi, how can I help?"),
    ),
    "Repeats separated by a user message": _messages(
        ("system", _SYSTEM_PROMPT),
        ("user", "Hello"),
        ("system", _SYSTEM_PROMPT),
        ("user", "Any news?"),
    ),
    "Duplicate before tool results": _messages(
        ("system", _SYSTEM_PROMPT),
        ("system", _SYSTEM_PROMPT),
        ("user", "Find order 48213"),
        ("assistant", "Looking it up."),
        ("tool", '{"order": 48213, "status": "shipped"}'),
    ),
    "Different system messages": _messages(
        ("system", _SYSTEM_PROMPT),
        ("system", "Answer in the customer's language."),
        ("user", "Hola"),
    ),
}

PIPELINE: dict[str, str] = {
    "Messy report": (
        f"# Launch plan   \n\n\n\n{_INTRO}   \n\n\n\nBudget:\n\n- Marketing  gets the largest share\n- Marketing  gets the largest share\n\n\n\n{_INTRO}\n"
    ),
    "Prompt with repeated rules": (
        "You  are a   support assistant.   \n\n\n- Be concise\n- Be concise\n- Cite sources\n\n\n\nYou  are a   support assistant.   \n"
    ),
    "Pretty tool output": json.dumps(
        {"status": "ok", "orders": _ORDER_ITEMS}, indent=4
    ),
    "Email with disclaimers": (
        f"Hello  team,   \n\n\n\nThe schedule is attached.   \n\n\n\n{_DISCLAIMER}\n\n\n\nThanks!   \n\n\n\n{_DISCLAIMER}\n"
    ),
    "Notes with a pasted paragraph": (
        f"Weekly notes   \n\n\n\n{_INTRO}\n\n\n\nAction items:\n- Send the report\n- Send the report\n\n\n\n{_INTRO}\n"
    ),
    "Already clean text": "This text is already clean.\n\nIt has normal spacing and no repeats.\n",
}

TEXT_SAMPLES: dict[str, dict[str, str]] = {
    "prose_whitespace_cleanup": WHITESPACE,
    "exact_paragraph_deduplication": PARAGRAPHS,
    "exact_bullet_item_deduplication": BULLETS,
    "tokenguru_json_minifier": JSON_TEXT,
    "pipeline": PIPELINE,
}

MESSAGE_SAMPLES: dict[str, dict[str, list[dict[str, Any]]]] = {
    "exact_duplicate_system_messages": SYSTEM_MESSAGES,
}
