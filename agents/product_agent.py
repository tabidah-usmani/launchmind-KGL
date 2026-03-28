
# agents/product_agent.py
# agents/product_agent.py
import os
import json
import re
from groq import Groq
from message_bus import send_message, get_messages, log_decision

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def call_llm(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1000,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content

def run(revision_feedback=None):
    print("\n" + "="*50)
    print("PRODUCT AGENT RUNNING")
    print("="*50)

    # Read task from CEO
    messages = get_messages("product")
    if not messages:
        print("[PRODUCT] No messages found.")
        return None

    latest = messages[-1]
    payload = latest["payload"]
    parent_id = latest["message_id"]

    idea = payload.get("idea", "")
    focus = payload.get("focus", "")
    feedback = revision_feedback or payload.get("feedback", "")

    print(f"[PRODUCT] Received task from CEO")
    print(f"[PRODUCT] Idea: {idea}")
    if feedback:
        print(f"[PRODUCT] Revision feedback: {feedback}")

    # Build prompt
    revision_note = ""
    if feedback:
        revision_note = f"\n\nIMPORTANT: A previous version was rejected. Fix these issues: {feedback}"

    system_prompt = """You are a Product Manager for DocuSprint — a tool that 
auto-generates README and API docs from codebases for developers.
Generate a detailed product specification as a JSON object with exactly these fields:
- value_proposition: one sentence describing what DocuSprint does and for whom
- personas: array of 3 objects each with: name, role, pain_point
- features: array of 5 objects each with: name, description, priority (1=highest)
- user_stories: array of 3 strings in 'As a [user] I want [action] so that [benefit]' format
Return ONLY valid JSON. No explanation, no markdown, no backticks. IMPORTANT: Return EXACTLY 5 features, EXACTLY 3 personas, 
and EXACTLY 3 user stories. No more, no less."""

    user_prompt = f"""Startup idea: {idea}
Focus areas: {focus}{revision_note}"""

    # Call LLM
    print("[PRODUCT] Generating product spec...")
    raw = call_llm(system_prompt, user_prompt)

    # Parse JSON
    # Parse JSON
    import re
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = re.sub(r'^```[a-z]*\n?', '', clean)
            clean = re.sub(r'```$', '', clean).strip()
        spec = json.loads(clean)
        log_decision("product", "generated product spec", "LLM returned valid JSON spec")
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
        try:
            fixed = fix_newlines(raw)
            spec = json.loads(fixed)
            log_decision("product", "generated product spec", "LLM returned valid JSON spec")
        except json.JSONDecodeError:
            print("[PRODUCT] ERROR: Could not parse LLM response as JSON")
            print(raw)
            return None

    print("\n[PRODUCT] Product spec generated:")
    print(json.dumps(spec, indent=2))

    # Send spec to Engineer
    send_message(
        from_agent="product",
        to_agent="engineer",
        message_type="result",
        payload={"product_spec": spec},
        parent_id=parent_id
    )

    # Send spec to Marketing
    send_message(
        from_agent="product",
        to_agent="marketing",
        message_type="result",
        payload={"product_spec": spec},
        parent_id=parent_id
    )

    # Send confirmation to CEO
    send_message(
        from_agent="product",
        to_agent="ceo",
        message_type="confirmation",
        payload={
            "status": "spec_ready",
            "product_spec": spec
        },
        parent_id=parent_id
    )

    print("[PRODUCT] Spec sent to Engineer, Marketing, and CEO")
    return spec