# Chat Consumer Testing Guide

## Overview

This test suite provides comprehensive coverage for the WebSocket-based chat functionality, including authentication, message broadcasting, database persistence, and room isolation.

## Running Tests

### All Chat Tests
```bash
cd /Users/mariussabaliauskas/Documents/Programming/eductoio/config_educa
python manage.py test chat
```

### Specific Test Classes
```bash
# Test WebSocket consumer functionality
python manage.py test chat.tests.ChatConsumerTest

# Test Message model
python manage.py test chat.tests.MessageModelTest
```

### Individual Tests
```bash
# Test authenticated user connection
python manage.py test chat.tests.ChatConsumerTest.test_authenticated_user_can_connect

# Test message broadcasting
python manage.py test chat.tests.ChatConsumerTest.test_broadcast_to_room_group

# Test database persistence
python manage.py test chat.tests.ChatConsumerTest.test_message_saved_to_database
```

### With Verbosity
```bash
# Detailed output
python manage.py test chat --verbosity=2

# Minimal output
python manage.py test chat --verbosity=0
```

## Test Coverage

### ChatConsumerTest (Async WebSocket Tests)

**Uses**: `TransactionTestCase` for async support

**Tests**:
- ✅ `test_authenticated_user_can_connect` - Verifies authenticated users can establish WebSocket connections
- ✅ `test_unauthenticated_user_cannot_connect` - Ensures anonymous users are rejected
- ✅ `test_send_message` - Tests sending and receiving messages through WebSocket
- ✅ `test_message_saved_to_database` - Verifies messages persist to database
- ✅ `test_broadcast_to_room_group` - Confirms messages broadcast to all room participants
- ✅ `test_empty_message_handling` - Tests handling of empty message payloads
- ✅ `test_room_name_isolation` - Ensures messages don't leak between different chat rooms
- ✅ `test_multiple_messages_in_sequence` - Tests sending multiple messages sequentially
- ✅ `test_disconnect_removes_from_group` - Verifies users are removed from group on disconnect

### MessageModelTest (Synchronous Model Tests)

**Uses**: `TestCase` for faster execution

**Tests**:
- ✅ `test_message_creation` - Tests creating Message instances
- ✅ `test_message_ordering` - Verifies messages ordered by `sent_on` descending
- ✅ `test_message_string_representation` - Tests `__str__` method output
- ✅ `test_message_indexes_exist` - Confirms database indexes are defined
- ✅ `test_message_user_relationship` - Tests user foreign key relationship
- ✅ `test_message_course_relationship` - Tests course foreign key relationship
- ✅ `test_message_protect_on_delete` - Verifies PROTECT on delete behavior
- ✅ `test_multiple_messages_per_user` - Tests one-to-many user relationship
- ✅ `test_multiple_messages_per_course` - Tests one-to-many course relationship

## Requirements

### Python Packages
- Django 4.2+
- Django Channels
- channels-testing
- channels-redis

### Infrastructure
- **Redis server** must be running for WebSocket tests
- Test database (automatically created/destroyed by Django)

### Installation
```bash
pip install channels channels-redis channels-testing
```

## Test Database

Tests use Django's test database which is:
- Automatically created before tests run
- Isolated from production/development databases
- Automatically destroyed after tests complete

## Troubleshooting

### Redis Connection Error

**Error**: `ConnectionRefusedError: [Errno 61] Connection refused`

**Solution**: Ensure Redis is running
```bash
redis-server
```

To verify Redis is running:
```bash
redis-cli ping
# Should return: PONG
```

### Async Test Failures

**Error**: `RuntimeError: There is no current event loop in thread`

**Solution**: Ensure using `TransactionTestCase` for async tests (already configured in test suite)

### Channel Layer Issues

**Error**: `AttributeError: 'NoneType' object has no attribute 'group_send'`

**Solution**: Verify channel layers configured in settings:
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'channels'`

**Solution**: Install missing dependencies:
```bash
pip install channels channels-redis channels-testing
```

## Test Architecture

### TransactionTestCase vs TestCase

**ChatConsumerTest** uses `TransactionTestCase`:
- Required for async test methods
- Supports WebSocket connections
- Slower but necessary for async operations

**MessageModelTest** uses `TestCase`:
- Faster execution with transaction rollback
- Sufficient for synchronous model tests
- Better performance for database-only tests

### WebSocket Testing Pattern

```python
# Create WebSocket application
application = URLRouter([
    re_path(r'ws/chat/room/(?P<course_id>\d+)/$', ChatConsumer.as_asgi()),
])

# Create communicator
communicator = WebsocketCommunicator(
    application,
    f"/ws/chat/room/{course_id}/"
)

# Set authenticated user
communicator.scope['user'] = user

# Connect
connected, _ = await communicator.connect()

# Send message
await communicator.send_json_to({'message': 'Hello'})

# Receive response
response = await communicator.receive_json_from()

# Disconnect
await communicator.disconnect()
```

## Coverage Summary

Total Tests: **19**
- WebSocket Consumer Tests: 10
- Model Tests: 9

Coverage Areas:
- Authentication and authorization
- WebSocket connection lifecycle
- Message sending and receiving
- Database persistence
- Room-based message isolation
- Broadcast functionality
- Model relationships and constraints
- Database indexes and ordering

## Continuous Integration

### Running in CI/CD

```yaml
# Example GitHub Actions workflow
- name: Start Redis
  run: |
    sudo apt-get install redis-server
    redis-server --daemonize yes

- name: Run tests
  run: |
    cd config_educa
    python manage.py test chat --verbosity=2
```

### Docker Testing

```bash
# Start Redis in Docker
docker run -d -p 6379:6379 redis:7.0.4

# Run tests
cd config_educa
python manage.py test chat
```

## Best Practices

1. **Always run Redis before testing** - WebSocket tests require Redis channel layer
2. **Use verbosity=2 for debugging** - Shows detailed test output
3. **Test isolation** - Each test creates fresh database state
4. **Async/await patterns** - All WebSocket tests are async
5. **Cleanup connections** - Always disconnect WebSocket communicators

## Performance

### Expected Test Duration
- ChatConsumerTest: ~5-10 seconds (async operations)
- MessageModelTest: ~1-2 seconds (database only)
- Total: ~6-12 seconds

### Optimization Tips
- Use `setUpTestData` for class-level fixtures (faster)
- Use `setUpClass` for WebSocket tests (required for TransactionTestCase)
- Run model tests separately if speed is critical

## Related Documentation

- [Django Channels Testing](https://channels.readthedocs.io/en/stable/topics/testing.html)
- [Django Testing](https://docs.djangoproject.com/en/4.2/topics/testing/)
- [WebSocket Testing with Channels](https://channels.readthedocs.io/en/stable/topics/testing.html#websocketcommunicator)
