# test_product.py
from dotenv import load_dotenv
load_dotenv()

import os
print("GROQ KEY:", os.environ.get("GROQ_API_KEY"))

from message_bus import send_message
from agents.product_agent import run

# Simulate CEO sending a task to Product agent
send_message(
    from_agent="ceo",
    to_agent="product",
    message_type="task",
    payload={
        "idea": "DocuSprint is a web-based tool for solo developers and open source maintainers that automatically generates a clean README, API documentation, and usage examples from their codebase.",
        "focus": "Define the core user personas and top 5 features"
    }
)

# Run the product agent
spec = run()

