# main.py
from dotenv import load_dotenv
load_dotenv(override=True)

from agents import ceo_agent, product_agent, engineer_agent, marketing_agent, qa_agent
from message_bus import print_full_history

IDEA = """DocuSprint is a web-based tool for solo developers and open source 
maintainers that automatically generates a clean README, API documentation, 
and usage examples from their codebase. Users paste a GitHub repo link and 
receive production-ready documentation in seconds. Revenue comes from a 
freemium model — free for small repos, paid for unlimited access and 
custom templates."""

if __name__ == "__main__":
    print("=" * 60)
    print("LAUNCHMIND — DOCUSPRINT")
    print("=" * 60)

    result = ceo_agent.run(
        idea=IDEA,
        product_agent=product_agent,
        engineer_agent=engineer_agent,
        marketing_agent=marketing_agent,
        qa_agent=qa_agent
    )

    print("\n" + "="*60)
    print("FULL MESSAGE HISTORY")
    print("="*60)
    print_full_history()

    print("\n" + "="*60)
    print("FINAL RESULT")
    print("="*60)
    print(f"PR URL: {result['pr_url']}")
    print(f"QA Verdict: {result['verdict']}")
    print(f"Product revisions: {result['product_revisions']}")
    print(f"Engineer revisions: {result['engineer_revisions']}")
