
# message_bus.py
import uuid
from datetime import datetime

# The shared message bus — a dictionary where keys are agent names
message_bus = {}
decision_log = []

def send_message(from_agent, to_agent, message_type, payload, parent_id=None):
    message = {
        "message_id": str(uuid.uuid4()),
        "from_agent": from_agent,
        "to_agent": to_agent,
        "message_type": message_type,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "parent_message_id": parent_id
    }

    if to_agent not in message_bus:
        message_bus[to_agent] = []

    message_bus[to_agent].append(message)

    print(f"\n[MESSAGE BUS] {from_agent.upper()} → {to_agent.upper()}")
    print(f"  Type    : {message_type}")
    print(f"  ID      : {message['message_id']}")
    print(f"  Time    : {message['timestamp']}")

    return message["message_id"]


def get_messages(agent_name):
    return message_bus.get(agent_name, [])


def get_latest_message(agent_name):
    messages = message_bus.get(agent_name, [])
    return messages[-1] if messages else None


def log_decision(agent, decision, reason):
    entry = {
        "agent": agent,
        "decision": decision,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    decision_log.append(entry)
    print(f"\n[DECISION LOG] {agent.upper()}: {decision}")
    print(f"  Reason: {reason}")


def get_full_history():
    all_messages = []
    for agent_messages in message_bus.values():
        all_messages.extend(agent_messages)
    return sorted(all_messages, key=lambda x: x["timestamp"])


def print_full_history():
    print("\n" + "="*60)
    print("FULL MESSAGE HISTORY")
    print("="*60)
    for msg in get_full_history():
        print(f"[{msg['timestamp']}]")
        print(f"  {msg['from_agent'].upper()} → {msg['to_agent'].upper()} | {msg['message_type']}")
        print(f"  ID: {msg['message_id']}")
        if msg['parent_message_id']:
            print(f"  Reply to: {msg['parent_message_id']}")
        print()