# rmq - Manual Testing Notes

## Overview

Manual test scenarios for the `rmq` module (RabbitMQ JSON messaging).
These are reference guides for testing during development, not automated tests.

## Prerequisites

### Install Dependencies
```bash
pip install pika
```

### Start RabbitMQ (Docker)
```bash
# Quick start with default guest/guest
docker run -d --name rabbitmq_mgmt \
  -p 5672:5672 -p 15672:15672 \
  rabbitmq:3.8.11-management

# Access management UI: http://localhost:15672
# Login: guest/guest

# With custom credentials
docker run -d --name rabbitmq_prod \
  -p 5672:5672 -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=admin \
  -e RABBITMQ_DEFAULT_PASS=secret123 \
  rabbitmq:3.8.11-management
```

---

## Test Data

```python
### Test payloads
SMALL_PAYLOAD  = {'task': 'test', 'id': 123}
MEDIUM_PAYLOAD = {'data': list(range(1000)), 'timestamp': '2024-01-01'}
LARGE_PAYLOAD  = {'content': 'x' * 1_500_000}  # ~1.5MB, should trigger warning

### Test queue names
QUEUE_WORK  = 'belt_test_work_queue'
QUEUE_TASKS = 'belt_test_tasks'

### Broker configurations
BROKER_LOCAL       = 'localhost'
BROKER_NONEXIST    = 'no.such.host'
BROKER_UNREACHABLE = '192.168.255.255'  # Timeout test
```

---------------------------------------------------------------------------

## Test Scenario 1: One-Shot Send (Default Credentials)

**Purpose:** Verify send_json() with guest/guest defaults

```python
from modules.rmq import send_json

result = send_json(SMALL_PAYLOAD, QUEUE_WORK)  # ✓ True (plain success case)
assert result is True

result = send_json(LARGE_PAYLOAD, QUEUE_WORK)  # ✓ True (with large payload warning logged)
assert result is True

result = send_json("not a dict", QUEUE_WORK)   # ✗ False (invalid input, error logged)
assert result is False

result = send_json([1, 2, 3], QUEUE_WORK)      # ✗ False (invalid input, error logged)
assert result is False

result = send_json({}, QUEUE_WORK)             # ✓ True (empty dict, valid)
assert result is True
```

**Verification:** +3 messages in queue

---

## Test Scenario 2: One-Shot Send (Explicit Credentials)

**Purpose:** Verify explicit username/password authentication

```bash
# Terminal: Start broker with custom credentials (see Prerequisites)
docker run -d --name rabbitmq_prod \
  -p 5672:5672 -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=admin \
  -e RABBITMQ_DEFAULT_PASS=secret123 \
  rabbitmq:3-management
```

```python
from modules.rmq import send_json

# Using explicit credentials
result = send_json(
    SMALL_PAYLOAD,
    QUEUE_WORK,
    username='admin',
    password='secret123'
)  # ✓ True
assert result is True
# Log should show: "Using explicit credentials for admin@localhost"

# Wrong credentials (should fail)
assert send_json(
    SMALL_PAYLOAD,
    QUEUE_WORK,
    username='wrong',
    password='bad'
) is False
# Log should show: "Connection failed"
```

---

## Test Scenario 3: Persistent Producer (High Frequency)

**Purpose:** Verify RMQProducer class with multiple sends

```python
from modules.rmq import RMQProducer

# Context manager (recommended)
with RMQProducer(QUEUE_TASKS) as producer:
    assert producer.send({'task': 1})  # ✓ True
    assert producer.send({'task': 2})  # ✓ True
    assert producer.send({'task': 3})  # ✓ True
# Connection auto-closed

# Manual lifecycle
producer = RMQProducer(QUEUE_TASKS)
assert producer.connect()          # ✓ True
assert producer.send({'task': 4})  # ✓ True
producer.close()

# Lazy connection (no explicit connect)
producer = RMQProducer(QUEUE_TASKS)
assert producer.send({'task': 5})  # ✓ True (auto-connects)
producer.close()
```

**Verification:** Check queue contains +5 messages in management UI

---

## Test Scenario 4: Producer with Enabled=False

**Purpose:** Verify disabled producer (testing/development)

```python
from modules.rmq import RMQProducer

producer = RMQProducer(QUEUE_WORK, enabled=False)
assert producer.send({'task': 'disabled'}) is True
# Log: "Send disabled to localhost/belt_test_work_queue"
```

**Verify:** no message actually sent

---

## Test Scenario 5: Consumer (Blocking)

**Purpose:** Verify consume_json()

```python
from modules.rmq import send_json, consume_json

# Send test messages first
for i in range(3):
    send_json({'task': f'work_{i}'}, QUEUE_WORK)

# Start consumer (blocks forever, use Ctrl+C to stop)
def process_task(data: dict):
    print(f"Processing: {data}")

consume_json(QUEUE_WORK, process_task)
```

**Expected Output:**
```
Processing: {'task': 'work_0'}
Processing: {'task': 'work_1'}
Processing: {'task': 'work_2'}
# Blocks waiting for more messages
```

**Stop:** Press Ctrl+C
**Expected:** Consumer logs "Consumer stopped by user" and exits gracefully <<XXX

---

## Test Scenario 6: Consumer Retry on Failure

**Purpose:** Verify manual ack and automatic retry on callback failure

```python
from modules.rmq import send_json, consume_json

# Send test messages first
for i in range(1,5):
    send_json({'task': 'test_retry', 'msg': i}, QUEUE_WORK)

run_count = 0

def failing_callback(data: dict):
    global run_count
    run_count += 1
    print(f"Callback run {run_count}: Processing {data}")

    # Fail on every 3rd
    if not run_count % 3:
        raise Exception(f"SIMULATED FAILURE on run {run_count}")

    print(f"Success on run {run_count}!\n")
    # Message will be acked here

consume_json(QUEUE_WORK, failing_callback)
```

**Expected Output:**
```
Callback run 1: Processing {'task': 'test_retry', 'msg': 1}
Success on run 1!

Callback run 2: Processing {'task': 'test_retry', 'msg': 2}
Success on run 2!

Callback run 3: Processing {'task': 'test_retry', 'msg': 3}
Callback failed, message requeued for retry: SIMULATED FAILURE on run 3
Callback run 4: Processing {'task': 'test_retry', 'msg': 3}
Success on run 4!

Callback run 5: Processing {'task': 'test_retry', 'msg': 4}
Success on run 5!
```

**Verification:**
- Same message automatically redelivered on failure (no manual intervention needed)
- Message requeued immediately when callback fails
- Message removed from queue when callback succeeds
- Queue should be empty after success

**Note:** Message is nacked with `requeue=True`, causing immediate redelivery to the same consumer.

---

## Test Scenario 7: Error Handling (Connection Failures)

**Purpose:** Verify error handling and logging

```python
from modules.rmq import send_json

# Non-existent host (DNS failure)
assert send_json(SMALL_PAYLOAD, QUEUE_WORK, host=BROKER_NONEXIST) is False
# Log should show: "Connection failed to no.such.host:5672"

# Unreachable host (wait for timeout)
assert send_json(SMALL_PAYLOAD, QUEUE_WORK, host=BROKER_UNREACHABLE, timeout=2.0) is False
# Log should show: "Connection failed to 192.168.255.255:5672"

# Wrong port
assert send_json(SMALL_PAYLOAD, QUEUE_WORK, host='localhost', port=9999) is False
# Log should show: "Connection failed to localhost:9999"

# Wrong credentials (if using custom broker)
assert send_json(
    SMALL_PAYLOAD,
    QUEUE_WORK,
    username='wrong',
    password='bad'
) is False
# Log should show: "Connection failed" (auth error)
```

---

## Test Scenario 8: Custom Logger (Loguru)

**Purpose:** Verify loguru compatibility

```bash
pip install loguru
```

```python
from loguru import logger
from modules.rmq import send_json, RMQProducer

# One-shot with loguru
assert send_json(SMALL_PAYLOAD, QUEUE_WORK, logger=logger) is True
# Should see loguru-formatted output (colored, with timestamps)

# Producer with loguru
with RMQProducer(QUEUE_TASKS, logger=logger) as producer:
    assert producer.send({'task': 'with_loguru'}) is True
    assert producer.send({'task': 'with_loguru'}) is True
# Loguru formatting throughout
```

---

## Test Scenario 9: JSON Error Handling

**Purpose:** Verify malformed JSON handling

```python
import pika

# Send non-JSON message directly (simulate malformed message)
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue=QUEUE_WORK)
channel.basic_publish(exchange='', routing_key=QUEUE_WORK, body=b'not json')
connection.close()

# Consumer should handle gracefully
from modules.rmq import consume_json

def process(data: dict):
    print(f"Data: {data}")

# Start consumer - should log error for invalid JSON and reject message
consume_json(QUEUE_WORK, process)
# Should log:
#  "Invalid JSON: ..."
#  "Message with invalid JSON rejected (not requeued)"
# Message is removed from queue (nacked without requeue)
```

**Expected:** Malformed message logged, rejected without requeue, consumer continues running

---

## Test Scenario 10: Integration with catch_signals

**Purpose:** Verify graceful shutdown with signal handling

```python
from time import sleep
from modules.rmq import send_json, consume_json
from modules.catch_signals import assist_signals

# Send some test messages
for i in range(10):
    send_json({'task': f'slow_{i}'}, QUEUE_WORK)

def slow_process(data: dict):
    with assist_signals():  # Protect message processing
        print(f"Processing: {data}")
        sleep(5)  # Simulate slow work
        print("Completed")

consume_json(QUEUE_WORK, slow_process)
```

**Test:** Press Ctrl+C during processing (while in sleep)
**Expected:** Current message completes before exit (remaining messages left unconsumed)
**Output should show:** "Completed" before consumer stops

---------------------------------------------------------------------------

## Common Issues & Troubleshooting

### Issue: "Connection refused"
**Cause:** RabbitMQ not running
**Solution:** Start Docker container (see Prerequisites)
```bash
docker ps  # Check if rabbitmq_mgmt is running
docker start rabbitmq_mgmt  # Start if stopped
```

### Issue: "Authentication failed"
**Cause:** Wrong credentials
**Solution:** Check credentials match broker config
```bash
# If using default guest/guest, no credentials needed
# If using custom broker, pass username/password explicitly
```

### Issue: "Module 'pika' not found"
**Cause:** pika not installed
**Solution:** `pip install pika`

### Issue: Consumer not receiving messages
**Cause:** Wrong queue name or queue empty
**Solution:** Verify queue name, send test message first
```python
# Send test message
from modules.rmq import send_json
send_json({'test': 'message'}, QUEUE_WORK)

# Then start consumer
from modules.rmq import consume_json
def process(data): print(data)
consume_json(QUEUE_WORK, process)
```

---

## Management UI Verification

Access: http://localhost:15672
Login: guest/guest (or custom credentials)
