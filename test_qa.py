# test_qa.py
import json

from dotenv import load_dotenv
load_dotenv(override=True)

from message_bus import send_message
from agents.qa_agent import run

# Simulate CEO sending to QA agent
send_message(
    from_agent="ceo",
    to_agent="qa",
    message_type="task",
    payload={
        "pr_number": 2,
        "pr_url": "https://github.com/tabidah-usmani/launchmind-KGL/pull/2",
        "html_content": """<!DOCTYPE html>
<html>
<head><title>DocuSprint</title></head>
<body>
<h1>Ship Code. Skip the Docs.</h1>
<p>DocuSprint auto-generates README and API docs from your codebase.</p>
<ul>
<li>README Generator</li>
<li>API Docs Generator</li>
<li>Code Example Extraction</li>
</ul>
<button>Generate My Docs Free</button>
</body>
</html>""",
        "marketing_copy": {
            "tagline": "Code less docs",
            "product_description": "DocuSprint auto-generates README and API docs.",
            "email_subject": "Automate your documentation",
            "email_body": "Hi, try DocuSprint today.",
            "twitter_post": "Auto-generate docs with DocuSprint!",
            "linkedin_post": "DocuSprint saves developers time.",
            "instagram_post": "No more manual docs!"
        },
        "product_spec": {
            "value_proposition": "DocuSprint auto-generates README and API docs from codebases.",
            "features": [
                {"name": "README Generator", "priority": 1},
                {"name": "API Docs Generator", "priority": 1},
                {"name": "Code Example Extraction", "priority": 2},
                {"name": "Customizable Templates", "priority": 2},
                {"name": "CI/CD Integration", "priority": 1}
            ]
        }
    }
)

report = run()
print("\nFinal Report:", json.dumps(report, indent=2) if report else "None")