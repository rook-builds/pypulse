"""Agent-CLI introspection: `pypulse introspect` and `pypulse skill`.

Lets any AI agent discover how to drive this tool without a human in the loop.
"""
import json

from . import __version__


def get_introspect_json() -> str:
    return json.dumps(
        {
            "name": "pypulse",
            "version": __version__,
            "description": "CLI dashboard for monitoring your PyPI package portfolio — versions, downloads, and release cadence at a glance.",
            "commands": [
                {
                    "usage": "pypulse [TARGET] --limit N --output text|json|table|csv",
                    "description": "CLI dashboard for monitoring your PyPI package portfolio — versions, downloads, and release cadence at a glance.",
                }
            ],
        },
        indent=2,
    )


def get_skill_md() -> str:
    return (
        "# pypulse\n\n"
        "CLI dashboard for monitoring your PyPI package portfolio — versions, downloads, and release cadence at a glance.\n\n"
        "## Usage\n\n"
        "```\n"
        "pypulse [TARGET] --limit 10 --output json\n"
        "```\n\n"
        "Outputs: text (default), json, table, csv.\n"
    )
