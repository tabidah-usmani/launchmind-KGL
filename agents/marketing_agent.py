
# agents/marketing_agent.py
import os
import json
import requests
from dotenv import load_dotenv
load_dotenv(override=True)

from groq import Groq
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from message_bus import send_message, get_messages, log_decision

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


def send_email(subject, body, to_email):
    try:
        message = Mail(
            from_email=os.environ.get("VERIFIED_EMAIL"),
            to_emails=to_email,
            subject=subject,
            html_content=f"<p>{body}</p>"
        )
        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(f"[MARKETING] Email sent — Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"[MARKETING] Email error: {e}")
        return False


def post_to_slack(tagline, description, pr_url):
    try:
        payload = {
            "channel": "#launches",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚀 New Launch: {tagline}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": description
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*GitHub PR:* <{pr_url}|View PR>"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Status:* Ready for review"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Product:* DocuSprint"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Stage:* MVP Launch"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Posted by LaunchMind Marketing Agent 🤖"
                        }
                    ]
                }
            ]
        }
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN')}"},
            json=payload
        )
        data = response.json()
        if data.get("ok"):
            print("[MARKETING] Slack message posted successfully")
        else:
            print(f"[MARKETING] Slack error: {data.get('error')}")
        return data.get("ok", False)
    except Exception as e:
        print(f"[MARKETING] Slack error: {e}")
        return False


def run(pr_url=None, revision_feedback=None):
    print("\n" + "="*50)
    print("MARKETING AGENT RUNNING")
    print("="*50)

    # Read message from Product agent
    messages = get_messages("marketing")
    if not messages:
        print("[MARKETING] No messages found.")
        return None

    latest = messages[-1]
    payload = latest["payload"]
    parent_id = latest["message_id"]
    product_spec = payload.get("product_spec", {})

    print("[MARKETING] Received product spec from Product agent")

    if revision_feedback:
        print(f"[MARKETING] Revision requested: {revision_feedback}")

    # Generate all marketing copy
    revision_note = ""
    if revision_feedback:
        revision_note = f"\n\nIMPORTANT: Fix these issues from previous version: {revision_feedback}"

    system_prompt = """You are a growth marketer for DocuSprint — a tool that 
auto-generates README and API docs from codebases for developers.
Generate marketing copy as a JSON object with exactly these fields:
- tagline: under 10 words, punchy and memorable
- product_description: 2-3 sentences for a landing page
- email_subject: compelling subject line for cold outreach
- email_body: cold outreach email to a solo developer, 3-4 short paragraphs with a clear CTA
- twitter_post: under 280 characters, casual and punchy with hashtags
- linkedin_post: professional tone, 3-4 sentences
- instagram_post: energetic with emojis, 2-3 sentences
CRITICAL RULES:
- Return ONLY valid JSON. No explanation, no markdown, no backticks.
- All string values must be on a single line — absolutely NO newlines or line breaks inside string values.
- Use spaces between sentences, never newline characters inside strings.
- The entire response must be parseable by json.loads() in Python."""

    user_prompt = f"""Product spec: {json.dumps(product_spec, indent=2)}{revision_note}"""

    print("[MARKETING] Generating marketing copy...")
    raw = call_llm(system_prompt, user_prompt)
    print("[MARKETING] Raw LLM response repr:")
    print(repr(raw[:500]))

    # Parse JSON
    import re
    try:
        # Remove markdown backticks if present
        clean = raw.strip()
        if clean.startswith("```"):
            clean = re.sub(r'^```[a-z]*\n?', '', clean)
            clean = re.sub(r'```$', '', clean).strip()
        
        copy = json.loads(clean)
    except json.JSONDecodeError:
        # Replace literal newlines inside strings only
        def fix_json_string(s):
            result = []
            in_string = False
            i = 0
            while i < len(s):
                c = s[i]
                if c == '"' and (i == 0 or s[i-1] != '\\'):
                    in_string = not in_string
                    result.append(c)
                elif in_string and c == '\n':
                    result.append(' ')
                elif in_string and c == '\t':
                    result.append(' ')
                else:
                    result.append(c)
                i += 1
            return ''.join(result)

        try:
            fixed = fix_json_string(raw)
            copy = json.loads(fixed)
        except json.JSONDecodeError:
            print("[MARKETING] ERROR: Could not parse LLM response as JSON")
            print(raw)
            return None

    print("\n[MARKETING] Marketing copy generated:")
    print(json.dumps(copy, indent=2))

    log_decision("marketing", "generated marketing copy", "LLM returned valid copy JSON")

    # Send email
    print("\n[MARKETING] Sending cold outreach email...")
    send_email(
        subject=copy.get("email_subject", "Introducing DocuSprint"),
        body=copy.get("email_body", ""),
        to_email=os.environ.get("TEST_EMAIL")
    )

    # Post to Slack
    print("[MARKETING] Posting to Slack...")
    slack_pr_url = pr_url or "https://github.com"
    post_to_slack(
        tagline=copy.get("tagline", "DocuSprint"),
        description=copy.get("product_description", ""),
        pr_url=slack_pr_url
    )

    # Send all copy back to CEO
    send_message(
        from_agent="marketing",
        to_agent="ceo",
        message_type="result",
        payload={
            "status": "marketing_ready",
            "copy": copy
        },
        parent_id=parent_id
    )

    print("[MARKETING] Results sent to CEO")
    return copy