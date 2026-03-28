
# agents/engineer_agent.py
import os
import json
import re
import base64
import requests
from dotenv import load_dotenv
load_dotenv(override=True)

from groq import Groq
from message_bus import send_message, get_messages, log_decision

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def call_llm(system_prompt, user_prompt):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=2000,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content


def get_main_sha():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/git/ref/heads/main"
    r = requests.get(url, headers=HEADERS)
    return r.json()["object"]["sha"]


def create_branch(branch_name, sha):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/git/refs"
    r = requests.post(url, headers=HEADERS, json={
        "ref": f"refs/heads/{branch_name}",
        "sha": sha
    })
    if r.status_code == 422:
        print(f"[ENGINEER] Branch {branch_name} already exists, continuing...")
    else:
        print(f"[ENGINEER] Branch {branch_name} created")


def commit_file(html_content, branch_name):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/index.html"
    
    # Check if file already exists
    r = requests.get(url, headers=HEADERS, params={"ref": branch_name})
    
    payload = {
        "message": "Add DocuSprint landing page",
        "content": base64.b64encode(html_content.encode()).decode(),
        "branch": branch_name,
        "author": {
            "name": "EngineerAgent",
            "email": "agent@launchmind.ai"
        }
    }
    
    if r.status_code == 200:
        payload["sha"] = r.json()["sha"]
    
    r = requests.put(url, headers=HEADERS, json=payload)
    print(f"[ENGINEER] File committed to branch {branch_name}")
    return r.json()


def create_issue(title, body):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    r = requests.post(url, headers=HEADERS, json={
        "title": title,
        "body": body
    })
    return r.json()["html_url"]


def create_pull_request(title, body, branch_name):
    # Check if PR already exists
    url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls"
    r = requests.get(url, headers=HEADERS, params={
        "head": f"{GITHUB_REPO.split('/')[0]}:{branch_name}",
        "base": "main",
        "state": "open"
    })
    existing = r.json()
    if existing and len(existing) > 0:
        pr_url = existing[0]["html_url"]
        pr_number = existing[0]["number"]
        print(f"[ENGINEER] PR already exists: {pr_url}")
        return pr_url, pr_number

    # Create new PR if none exists
    r = requests.post(url, headers=HEADERS, json={
        "title": title,
        "body": body,
        "head": branch_name,
        "base": "main"
    })
    data = r.json()
    if "html_url" in data:
        return data["html_url"], data["number"]
    else:
        print(f"[ENGINEER] PR creation response: {data}")
        return None, None


def run(revision_feedback=None):
    print("\n" + "="*50)
    print("ENGINEER AGENT RUNNING")
    print("="*50)

    # Read message from Product agent
    messages = get_messages("engineer")
    if not messages:
        print("[ENGINEER] No messages found.")
        return None

    latest = messages[-1]
    payload = latest["payload"]
    parent_id = latest["message_id"]
    product_spec = payload.get("product_spec", {})

    print("[ENGINEER] Received product spec from Product agent")

    if revision_feedback:
        print(f"[ENGINEER] Revision requested: {revision_feedback}")

    # Generate HTML landing page
    system_prompt = """You are a frontend developer building a landing page.
Generate a complete, single-file HTML page with inline CSS.
The page must include:
- A compelling headline
- A subheadline explaining the product in one sentence
- A features section listing all features from the spec
- A call-to-action button saying 'Generate My Docs Free'
- Clean, modern CSS styling with a dark navy and green color scheme
Return ONLY raw HTML starting with <!DOCTYPE html>. No explanation, no markdown."""

    revision_note = ""
    if revision_feedback:
        revision_note = f"\n\nIMPORTANT: Fix these issues from the previous version: {revision_feedback}"

    user_prompt = f"""Create a landing page for DocuSprint based on this product spec:
{json.dumps(product_spec, indent=2)}{revision_note}"""

    print("[ENGINEER] Generating HTML landing page...")
    html_content = call_llm(system_prompt, user_prompt)

    # Clean up if LLM added markdown
    if "```html" in html_content:
        html_content = html_content.split("```html")[1].split("```")[0].strip()
    elif "```" in html_content:
        html_content = html_content.split("```")[1].split("```")[0].strip()

    print("[ENGINEER] HTML generated successfully")

    # GitHub operations
    branch_name = "agent-landing-page"

    try:
        # Step 1: Get main SHA
        sha = get_main_sha()

        # Step 2: Create branch
        create_branch(branch_name, sha)

        # Step 3: Commit file
        commit_file(html_content, branch_name)

        # Step 4: Create GitHub issue
        issue_body = call_llm(
            "You write GitHub issue descriptions. Be concise and technical.",
            f"Write a GitHub issue description for adding the initial landing page for DocuSprint. Product spec: {json.dumps(product_spec)}"
        )
        issue_url = create_issue("Initial landing page", issue_body)
        print(f"[ENGINEER] Issue created: {issue_url}")

        # Step 5: Create Pull Request
        pr_body = call_llm(
            "You write GitHub pull request descriptions. Be concise and technical.",
            f"Write a pull request description for the DocuSprint landing page. Product spec: {json.dumps(product_spec)}"
        )
        pr_url, pr_number = create_pull_request(
            "Initial landing page for DocuSprint",
            pr_body,
            branch_name
        )
        print(f"[ENGINEER] PR created: {pr_url}")

        log_decision("engineer", "completed GitHub operations", "Branch created, file committed, issue and PR opened")

        # Send result back to CEO
        send_message(
            from_agent="engineer",
            to_agent="ceo",
            message_type="result",
            payload={
                "pr_url": pr_url,
                "pr_number": pr_number,
                "issue_url": issue_url,
                "html_content": html_content,
                "branch_name": branch_name
            },
            parent_id=parent_id
        )

        print("[ENGINEER] Results sent to CEO")
        return pr_url, pr_number, html_content

    except Exception as e:
        print(f"[ENGINEER] ERROR: {e}")
        send_message(
            from_agent="engineer",
            to_agent="ceo",
            message_type="result",
            payload={"error": str(e), "pr_url": None}
        )
        return None, None, None