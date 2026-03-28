# test_bus.py
from message_bus import send_message, get_messages, get_full_history, print_full_history, log_decision

# Test 1: Send a message
msg_id = send_message(
    from_agent="ceo",
    to_agent="product",
    message_type="task",
    payload={"idea": "DocuSprint", "focus": "Define personas and features"}
)

# Test 2: Send a reply
send_message(
    from_agent="product",
    to_agent="ceo",
    message_type="confirmation",
    payload={"status": "spec ready"},
    parent_id=msg_id
)

# Test 3: Log a decision
log_decision("ceo", "accepted product spec", "All 5 features and 3 personas present")

# Test 4: Print everything
print_full_history()