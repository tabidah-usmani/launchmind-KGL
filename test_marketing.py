# test_marketing.py
import os
from dotenv import load_dotenv
load_dotenv(override=True)
print("SLACK TOKEN:", os.environ.get("SLACK_BOT_TOKEN"))

from message_bus import send_message
from agents.marketing_agent import run

# Simulate Product agent sending spec to Marketing
send_message(
    from_agent="product",
    to_agent="marketing",
    message_type="result",
    payload={
        "product_spec": {
            "value_proposition": "DocuSprint auto-generates README and API docs from codebases for solo developers and open source maintainers.",
            "personas": [
                {"name": "Alex Chen", "role": "Solo Developer", "pain_point": "Spending too much time writing documentation"},
                {"name": "Maya Patel", "role": "Open Source Maintainer", "pain_point": "Keeping docs consistent across contributors"},
                {"name": "Ethan Kim", "role": "DevOps Engineer", "pain_point": "Manually updating API docs for internal tools"}
            ],
            "features": [
                {"name": "README Generator", "description": "Auto-generate README from codebase", "priority": 1},
                {"name": "API Docs Generator", "description": "Generate API docs from annotations", "priority": 1},
                {"name": "Code Example Extraction", "description": "Extract usage examples from code", "priority": 2},
                {"name": "Customizable Templates", "description": "Customize doc look and feel", "priority": 2},
                {"name": "CI/CD Integration", "description": "Auto-update docs on code changes", "priority": 1}
            ],
            "user_stories": [
                "As a solo developer I want to auto-generate a README so that I can focus on writing code",
                "As an open source maintainer I want API docs generated automatically so contributors understand the API",
                "As a DevOps engineer I want CI/CD integration so documentation is always up to date"
            ]
        }
    }
)
try:
    copy = run(pr_url="https://github.com/tabidah-usmani/launchmind-KGL/pull/2")
    print("\nDone:", copy)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
