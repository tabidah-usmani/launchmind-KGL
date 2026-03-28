# agents/ceo_agent.py
import os
import json
import re
import requests
from dotenv import load_dotenv
load_dotenv(override=True)

from groq import Groq
from message_bus import send_message, get_messages, log_decision

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

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


def post_final_summary_to_slack(idea, pr_url, tagline, verdict):
    try:
        payload = {
            "channel": "#launches",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🎯 LaunchMind — Final Summary"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Startup:* DocuSprint\n*Idea:* {idea[:200]}"
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
                            "text": f"*Tagline:* {tagline}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*QA Verdict:* {verdict.upper()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*GitHub PR:* <{pr_url}|View PR>"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Status:* Pipeline Complete ✅"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Posted by LaunchMind CEO Agent 🤖"
                        }
                    ]
                }
            ]
        }
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json=payload
        )
        data = response.json()
        if data.get("ok"):
            print("[CEO] Final summary posted to Slack ✅")
        else:
            print(f"[CEO] Slack error: {data.get('error')}")
    except Exception as e:
        print(f"[CEO] Slack error: {e}")


def decompose_idea(idea):
    print("[CEO] Decomposing startup idea into tasks...")
    system_prompt = """You are the CEO of a tech startup. You receive a startup idea 
and break it down into specific tasks for your team.
Return ONLY a valid JSON object with exactly these fields:
- product_task: detailed instruction string for the Product Manager
- engineer_task: detailed instruction string for the Engineer
- marketing_task: detailed instruction string for the Marketing team
No explanation, no markdown, no backticks. All values on single lines."""

    user_prompt = f"Startup idea: {idea}"
    raw = call_llm(system_prompt, user_prompt)

    try:
        tasks = fix_json(raw)
        log_decision("ceo", "decomposed idea into tasks", f"Generated tasks for product, engineer, marketing")
        return tasks
    except Exception as e:
        print(f"[CEO] Could not parse task decomposition: {e}")
        return {
            "product_task": "Define user personas, core features, and user stories for the startup",
            "engineer_task": "Build a complete HTML landing page with all features and a CTA button",
            "marketing_task": "Generate tagline, product description, cold email, and social media posts"
        }


def review_output(agent_name, output, context):
    print(f"[CEO] Reviewing {agent_name} output with LLM...")
    system_prompt = """You are the CEO of a tech startup reviewing your team's work.
Be critical and specific. 
Return ONLY a valid JSON object with exactly these fields:
- verdict: pass or fail
- feedback: specific issues to fix if fail, empty string if pass
No explanation, no markdown, no backticks."""

    user_prompt = f"""Review this output from the {agent_name} agent.
Context: {context}
Output to review: {json.dumps(output) if isinstance(output, dict) else str(output)[:2000]}
Is this output specific, complete, and relevant to the startup idea?"""

    raw = call_llm(system_prompt, user_prompt)

    try:
        review = fix_json(raw)
        log_decision(
            "ceo",
            f"reviewed {agent_name} output: {review.get('verdict')}",
            review.get('feedback', 'Output accepted') or 'Output accepted'
        )
        return review
    except Exception as e:
        print(f"[CEO] Could not parse review: {e}")
        return {"verdict": "pass", "feedback": ""}


def run(idea, product_agent, engineer_agent, marketing_agent, qa_agent):
    print("\n" + "="*60)
    print("CEO AGENT RUNNING")
    print("="*60)
    print(f"[CEO] Received idea: {idea[:100]}...")

    # ─────────────────────────────────────────
    # STEP 1: Decompose idea into tasks
    # ─────────────────────────────────────────
    tasks = decompose_idea(idea)
    print(f"[CEO] Tasks generated: {list(tasks.keys())}")

    # ─────────────────────────────────────────
    # STEP 2: Send task to Product agent
    # ─────────────────────────────────────────
    print("\n[CEO] Sending task to Product agent...")
    send_message(
        from_agent="ceo",
        to_agent="product",
        message_type="task",
        payload={
            "idea": idea,
            "focus": tasks.get("product_task", "")
        }
    )
    # Send task to Engineer
    send_message(
        from_agent="ceo",
        to_agent="engineer",
        message_type="task",
        payload={
            "idea": idea,
            "focus": tasks.get("engineer_task", "")
        }
    )

    # Send task to Marketing
    send_message(
        from_agent="ceo",
        to_agent="marketing",
        message_type="task",
        payload={
            "idea": idea,
            "focus": tasks.get("marketing_task", "")
        }
    )

    # Run Product agent
    product_spec = product_agent.run()

    # ─────────────────────────────────────────
    # STEP 3: CEO reviews Product spec
    # ─────────────────────────────────────────
    print("\n[CEO] Reviewing Product spec...")
    product_review = review_output(
        "Product",
        product_spec,
        f"Startup idea: {idea}"
    )

    # Feedback loop 1 — Product revision if needed
    max_retries = 2
    retry = 0
    while product_review.get("verdict") == "fail" and retry < max_retries:
        retry += 1
        print(f"\n[CEO] Product spec rejected. Requesting revision #{retry}...")
        send_message(
            from_agent="ceo",
            to_agent="product",
            message_type="revision_request",
            payload={
                "idea": idea,
                "focus": tasks.get("product_task", ""),
                "feedback": product_review.get("feedback", "")
            }
        )
        product_spec = product_agent.run(
            revision_feedback=product_review.get("feedback")
        )
        product_review = review_output(
            "Product",
            product_spec,
            f"Startup idea: {idea}"
        )

    print(f"[CEO] Product spec accepted after {retry} revision(s)")

    # ─────────────────────────────────────────
    # STEP 4: Send spec to Engineer + Marketing
    # ─────────────────────────────────────────
    print("\n[CEO] Sending product spec to Engineer and Marketing...")

    # Engineer runs using message already sent by Product agent
    pr_url, pr_number, html_content = engineer_agent.run()

    send_message(
    from_agent="ceo",
    to_agent="marketing",
    message_type="task",
    payload={"pr_url": pr_url}
)
    # Marketing runs using message already sent by Product agent
    marketing_copy = marketing_agent.run(pr_url=pr_url)

    # ─────────────────────────────────────────
    # STEP 5: Send everything to QA agent
    # ─────────────────────────────────────────
    print("\n[CEO] Sending outputs to QA agent for review...")
    send_message(
        from_agent="ceo",
        to_agent="qa",
        message_type="task",
        payload={
            "pr_number": pr_number,
            "pr_url": pr_url,
            "html_content": html_content,
            "marketing_copy": marketing_copy,
            "product_spec": product_spec
        }
    )

    qa_report = qa_agent.run()

    # ─────────────────────────────────────────
    # STEP 6: CEO reviews QA verdict
    # ─────────────────────────────────────────
    print(f"\n[CEO] QA verdict received: {qa_report.get('verdict')}")

    # Feedback loop 2 — Engineer revision if QA fails
    qa_retry = 0
    max_qa_retries = 2

    while qa_report.get("verdict") == "fail" and qa_retry < max_qa_retries:
        qa_retry += 1
        issues = qa_report.get("issues", [])
        html_issues = qa_report.get("html_issues", []) or qa_report.get("issues", [])

        print(f"\n[CEO] QA failed. Requesting Engineer revision #{qa_retry}...")
        log_decision(
            "ceo",
            f"requesting engineer revision #{qa_retry}",
            f"QA found {len(issues)} issues: {issues[:2]}"
        )

        # Send revision request to Engineer
        send_message(
            from_agent="ceo",
            to_agent="engineer",
            message_type="revision_request",
            payload={
                "product_spec": product_spec,
                "feedback": f"QA Review failed. Fix these issues: {qa_report.get('issues', [])}",
                "pr_number": pr_number
            }
        )

        # Engineer revises
        pr_url, pr_number, html_content = engineer_agent.run(
            revision_feedback=f"Fix these QA issues: {qa_report.get('issues', [])}"
        )

        # Re-run QA
        print("[CEO] Re-running QA after Engineer revision...")
        send_message(
            from_agent="ceo",
            to_agent="qa",
            message_type="task",
            payload={
                "pr_number": pr_number,
                "pr_url": pr_url,
                "html_content": html_content,
                "marketing_copy": marketing_copy,
                "product_spec": product_spec
            }
        )
        qa_report = qa_agent.run()
        print(f"[CEO] QA re-review verdict: {qa_report.get('verdict')}")

    # ─────────────────────────────────────────
    # STEP 7: Post final summary to Slack
    # ─────────────────────────────────────────
    print("\n[CEO] Posting final summary to Slack...")
    tagline = marketing_copy.get("tagline", "DocuSprint") if marketing_copy else "DocuSprint"
    final_verdict = qa_report.get("verdict", "complete")

    post_final_summary_to_slack(
        idea=idea,
        pr_url=pr_url or "https://github.com",
        tagline=tagline,
        verdict=final_verdict
    )

    print("\n" + "="*60)
    print("CEO AGENT COMPLETE")
    print("="*60)
    print(f"[CEO] PR URL: {pr_url}")
    print(f"[CEO] QA Final Verdict: {final_verdict}")
    print(f"[CEO] Product revisions: {retry}")
    print(f"[CEO] Engineer revisions: {qa_retry}")

    return {
        "pr_url": pr_url,
        "verdict": final_verdict,
        "product_revisions": retry,
        "engineer_revisions": qa_retry
    }