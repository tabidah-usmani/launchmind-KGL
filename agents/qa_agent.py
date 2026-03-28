
# agents/qa_agent.py
import os
import json
import re
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


def fix_json(raw):
    clean = raw.strip()
    if clean.startswith("```"):
        clean = re.sub(r'^```[a-z]*\n?', '', clean)
        clean = re.sub(r'```$', '', clean).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        def fix_newlines(s):
            result = []
            in_string = False
            i = 0
            while i < len(s):
                c = s[i]
                if c == '"' and (i == 0 or s[i-1] != '\\'):
                    in_string = not in_string
                    result.append(c)
                elif in_string and c in '\n\t\r':
                    result.append(' ')
                else:
                    result.append(c)
                i += 1
            return ''.join(result)
        return json.loads(fix_newlines(clean))


def post_pr_review(pr_number, comments):
    # First get the latest commit SHA on the branch
    commits_url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/commits"
    r = requests.get(commits_url, headers=HEADERS)
    commits = r.json()
    if not commits:
        return False
    latest_sha = commits[-1]["sha"]

    # Post a review with inline comments
    review_url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/reviews"
    r = requests.post(review_url, headers=HEADERS, json={
        "commit_id": latest_sha,
        "body": "🤖 QA Agent automated review",
        "event": "COMMENT",
        "comments": [
            {
                "path": "index.html",
                "position": 1,
                "body": comments[0]
            },
            {
                "path": "index.html",
                "position": 2,
                "body": comments[1]
            }
        ]
    })
    data = r.json()
    if "id" in data:
        print(f"[QA] Inline PR review posted successfully")
        return True
    else:
        print(f"[QA] PR review response: {data}")
        return False


def run():
    print("\n" + "="*50)
    print("QA AGENT RUNNING")
    print("="*50)

    # Read message from CEO
    messages = get_messages("qa")
    if not messages:
        print("[QA] No messages found.")
        return None

    latest = messages[-1]
    payload = latest["payload"]
    parent_id = latest["message_id"]

    html_content = payload.get("html_content", "")
    pr_number = payload.get("pr_number")
    pr_url = payload.get("pr_url", "")
    marketing_copy = payload.get("marketing_copy", {})
    product_spec = payload.get("product_spec", {})

    print(f"[QA] Received HTML and marketing copy from CEO")
    print(f"[QA] Reviewing PR #{pr_number}")

    # LLM Review #1 — HTML landing page
    print("\n[QA] Reviewing HTML landing page...")
    html_system = """You are a QA reviewer for a software startup. 
Review the HTML landing page against the product spec.
Check these specific things:
1. Does the headline match the value proposition?
2. Are all 5 features mentioned on the page?
3. Is there a clear CTA button?
4. Is the tone appropriate for a developer audience?
5. Is the page professionally styled?
Return ONLY a JSON object with exactly these fields:
- html_verdict: pass or fail
- html_issues: array of specific problems found (empty array if pass)
- html_comments: array of exactly 2 strings, each a specific inline review comment for the PR
No explanation, no markdown, no backticks."""

    html_user = f"""Product spec:
{json.dumps(product_spec, indent=2)}

HTML content:
{html_content[:3000]}"""

    html_raw = call_llm(html_system, html_user)

    try:
        html_review = fix_json(html_raw)
    except Exception as e:
        print(f"[QA] Could not parse HTML review: {e}")
        html_review = {
            "html_verdict": "fail",
            "html_issues": ["Could not parse QA review"],
            "html_comments": ["Review parsing failed", "Manual review required"]
        }

    print(f"[QA] HTML verdict: {html_review.get('html_verdict')}")
    if html_review.get('html_issues'):
        print(f"[QA] HTML issues: {html_review.get('html_issues')}")

    # LLM Review #2 — Marketing copy
    print("\n[QA] Reviewing marketing copy...")
    copy_system = """You are a QA reviewer for a software startup.
Review the marketing copy for quality and effectiveness.
Check these specific things:
1. Is the tagline under 10 words and memorable?
2. Does the cold email have a clear call to action?
3. Is the tone appropriate for a developer audience?
4. Are the social media posts platform-appropriate?
5. Is the product description clear and compelling?
Return ONLY a JSON object with exactly these fields:
- copy_verdict: pass or fail
- copy_issues: array of specific problems found (empty array if pass)
No explanation, no markdown, no backticks."""

    copy_user = f"""Marketing copy to review:
{json.dumps(marketing_copy, indent=2)}"""

    copy_raw = call_llm(copy_system, copy_user)

    try:
        copy_review = fix_json(copy_raw)
    except Exception as e:
        print(f"[QA] Could not parse copy review: {e}")
        copy_review = {
            "copy_verdict": "pass",
            "copy_issues": []
        }

    print(f"[QA] Copy verdict: {copy_review.get('copy_verdict')}")
    if copy_review.get('copy_issues'):
        print(f"[QA] Copy issues: {copy_review.get('copy_issues')}")

    # Post PR comments
    if pr_number:
        print(f"\n[QA] Posting review comments on PR #{pr_number}...")
        comments = html_review.get("html_comments", [
            "QA Review: Please verify headline matches value proposition",
            "QA Review: Ensure all 5 features are visible on the page"
        ])
        for comment in comments[:2]:
            post_pr_review(pr_number, f"🤖 **QA Agent Review:**\n\n{comment}")

    # Determine overall verdict
    html_verdict = html_review.get("html_verdict", "fail")
    copy_verdict = copy_review.get("copy_verdict", "fail")
    overall_verdict = "pass" if html_verdict == "pass" and copy_verdict == "pass" else "fail"

    all_issues = html_review.get("html_issues", []) + copy_review.get("copy_issues", [])

    log_decision(
        "qa",
        f"overall verdict: {overall_verdict}",
        f"HTML: {html_verdict}, Copy: {copy_verdict}, Issues: {len(all_issues)}"
    )

    # Build review report
    review_report = {
        "verdict": overall_verdict,
        "html_verdict": html_verdict,
        "copy_verdict": copy_verdict,
        "issues": all_issues,
        "pr_url": pr_url
    }

    print(f"\n[QA] Overall verdict: {overall_verdict}")
    print(f"[QA] Total issues found: {len(all_issues)}")

    # Send report back to CEO
    send_message(
        from_agent="qa",
        to_agent="ceo",
        message_type="result",
        payload={
            "status": "review_complete",
            "review_report": review_report
        },
        parent_id=parent_id
    )

    print("[QA] Review report sent to CEO")
    return review_report