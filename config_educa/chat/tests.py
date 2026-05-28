from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User, AnonymousUser
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.urls import re_path
from courses.models import Course, Subject
from chat.models import Message
from chat.consumers import ChatConsumer
import json
import asyncio


class ChatConsumerTest(TransactionTestCase):
    """Test WebSocket ChatConsumer with authentication and message handling"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test user
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # Create test course
        cls.subject = Subject.objects.create(
            title='Test Subject',
            slug='test-subject'
        )
        cls.course = Course.objects.create(
            owner=cls.user,
            subject=cls.subject,
            title='Test Course',
            slug='test-course',
            overview='Test overview'
        )

    async def test_authenticated_user_can_connect(self):
        """Test that authenticated users can connect to chat"""
        application = URLRouter([
            re_path(r'ws/chat/room/(?P<course_id>\d+)/$', ChatConsumer.as_asgi()),
        ])

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{self.course.id}/"
        )

        # Set user in scope
        communicator.scope['user'] = self.user

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        await communicator.disconnect()

    async def test_unauthenticated_user_cannot_connect(self):
        """Test that unauthenticated users are rejected"""
        application = URLRouter([
            re_path(r'ws/chat/room/(?P<course_id>\d+)/$', ChatConsumer.as_asgi()),
        ])

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{self.course.id}/"
        )

        # Set anonymous user
        communicator.scope['user'] = AnonymousUser()

        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)

    async def test_send_message(self):
        """Test sending a message through WebSocket"""
        application = URLRouter([
            re_path(r'ws/chat/room/(?P<course_id>\d+)/$', ChatConsumer.as_asgi()),
        ])

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{self.course.id}/"
        )
        communicator.scope['user'] = self.user

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send message
        test_message = "Hello from test!"
        await communicator.send_json_to({
            'message': test_message
        })

        # Receive message
        response = await communicator.receive_json_from()

        self.assertEqual(response['message'], test_message)
        self.assertEqual(response['user'], self.user.username)
        self.assertIn('datetime', response)

        await communicator.disconnect()

    async def test_message_saved_to_database(self):
        """Test that messages are saved to database"""
        application = URLRouter([
            re_path(r'ws/chat/room/(?P<course_id>\d+)/$', ChatConsumer.as_asgi()),
        ])

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{self.course.id}/"
        )
        communicator.scope['user'] = self.user

        await communicator.connect()

        # Send message
        test_message = "Database persistence test"
        await communicator.send_json_to({
            'message': test_message
        })

        # Wait for message to be received
        await communicator.receive_json_from()

        await communicator.disconnect()

        # Check database
        message = await Message.objects.filter(
            user=self.user,
            course=self.course,
            content=test_message
        ).afirst()

        self.assertIsNotNone(message)
        self.assertEqual(message.content, test_message)

    async def test_broadcast_to_room_group(self):
        """Test that messages broadcast to all users in room"""
        application = URLRouter([
            re_path(r'ws/chat/room/(?P<course_id>\d+)/$', ChatConsumer.as_asgi()),
        ])

        # Create second user
        user2 = await User.objects.acreate(username='testuser2', password='pass')

        # Create two connections
        communicator1 = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{self.course.id}/"
        )
        communicator1.scope['user'] = self.user

        communicator2 = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{self.course.id}/"
        )
        communicator2.scope['user'] = user2

        # Connect both
        await communicator1.connect()
        await communicator2.connect()

        # Send from user1
        test_message = "Broadcast test"
        await communicator1.send_json_to({'message': test_message})

        # Both should receive
        response1 = await communicator1.receive_json_from()
        response2 = await communicator2.receive_json_from()

        self.assertEqual(response1['message'], test_message)
        self.assertEqual(response2['message'], test_message)
        self.assertEqual(response1['user'], self.user.username)
        self.assertEqual(response2['user'], self.user.username)

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_empty_message_handling(self):
        """Test that empty messages are handled properly"""
        application = URLRouter([
            re_path(r'ws/chat/room/(?P<course_id>\d+)/$', ChatConsumer.as_asgi()),
        ])

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{self.course.id}/"
        )
        communicator.scope['user'] = self.user

        await communicator.connect()

        # Try to send empty message
        await communicator.send_json_to({'message': ''})

        # The consumer currently doesn't filter empty messages,
        # so we should receive it
        response = await communicator.receive_json_from(timeout=1)
        self.assertEqual(response['message'], '')

        await communicator.disconnect()

    async def test_room_name_isolation(self):
        """Test that messages don't leak between different rooms"""
        # Create second course
        course2 = await Course.objects.acreate(
            owner=self.user,
            subject=self.subject,
            title='Test Course 2',
            slug='test-course-2',
            overview='Test overview 2'
        )

        application = URLRouter([
            re_path(r'ws/chat/room/(?P<course_id>\d+)/$', ChatConsumer.as_asgi()),
        ])

        # Connect to room 1
        comm1 = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{self.course.id}/"
        )
        comm1.scope['user'] = self.user

        # Connect to room 2
        comm2 = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{course2.id}/"
        )
        comm2.scope['user'] = self.user

        await comm1.connect()
        await comm2.connect()

        # Send to room 1
        await comm1.send_json_to({'message': 'Room 1 message'})

        # Room 1 should receive
        response1 = await comm1.receive_json_from()
        self.assertEqual(response1['message'], 'Room 1 message')

        # Room 2 should NOT receive (timeout expected)
        try:
            await asyncio.wait_for(comm2.receive_json_from(), timeout=0.5)
            self.fail("Room 2 should not receive Room 1's messages")
        except asyncio.TimeoutError:
            pass  # Expected behavior

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_multiple_messages_in_sequence(self):
        """Test sending multiple messages in sequence"""
        application = URLRouter([
            re_path(r'ws/chat/room/(?P<course_id>\d+)/$', ChatConsumer.as_asgi()),
        ])

        communicator = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{self.course.id}/"
        )
        communicator.scope['user'] = self.user

        await communicator.connect()

        # Send multiple messages
        messages = ['First message', 'Second message', 'Third message']
        for msg in messages:
            await communicator.send_json_to({'message': msg})
            response = await communicator.receive_json_from()
            self.assertEqual(response['message'], msg)

        await communicator.disconnect()

        # Verify all messages are in database
        db_messages = await Message.objects.filter(
            user=self.user,
            course=self.course
        ).acount()

        self.assertEqual(db_messages, 3)

    async def test_disconnect_removes_from_group(self):
        """Test that disconnecting removes user from group"""
        application = URLRouter([
            re_path(r'ws/chat/room/(?P<course_id>\d+)/$', ChatConsumer.as_asgi()),
        ])

        # Create two connections
        comm1 = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{self.course.id}/"
        )
        comm1.scope['user'] = self.user

        user2 = await User.objects.acreate(username='disconnecttest', password='pass')
        comm2 = WebsocketCommunicator(
            application,
            f"/ws/chat/room/{self.course.id}/"
        )
        comm2.scope['user'] = user2

        await comm1.connect()
        await comm2.connect()

        # Disconnect comm1
        await comm1.disconnect()

        # Send message from comm2
        await comm2.send_json_to({'message': 'After disconnect'})

        # Only comm2 should receive
        response = await comm2.receive_json_from()
        self.assertEqual(response['message'], 'After disconnect')

        await comm2.disconnect()


class MessageModelTest(TestCase):
    """Test Message model"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='pass')
        cls.subject = Subject.objects.create(title='Subject', slug='subject')
        cls.course = Course.objects.create(
            owner=cls.user,
            subject=cls.subject,
            title='Course',
            slug='course',
            overview='Overview'
        )

    def test_message_creation(self):
        """Test creating a message"""
        message = Message.objects.create(
            user=self.user,
            course=self.course,
            content='Test message'
        )

        self.assertEqual(message.user, self.user)
        self.assertEqual(message.course, self.course)
        self.assertEqual(message.content, 'Test message')
        self.assertIsNotNone(message.sent_on)

    def test_message_ordering(self):
        """Test messages are ordered by sent_on descending"""
        msg1 = Message.objects.create(
            user=self.user,
            course=self.course,
            content='First'
        )
        msg2 = Message.objects.create(
            user=self.user,
            course=self.course,
            content='Second'
        )

        messages = Message.objects.all()
        self.assertEqual(messages[0], msg2)  # Most recent first
        self.assertEqual(messages[1], msg1)

    def test_message_string_representation(self):
        """Test __str__ method"""
        message = Message.objects.create(
            user=self.user,
            course=self.course,
            content='Test'
        )

        # The __str__ method returns: f'{self.user} on {self.course} at {self.sent_on}'
        str_repr = str(message)
        self.assertIn(self.user.username, str_repr)
        self.assertIn(self.course.title, str_repr)

    def test_message_indexes_exist(self):
        """Test that database indexes are defined"""
        meta = Message._meta
        self.assertTrue(hasattr(meta, 'indexes'))
        self.assertGreater(len(meta.indexes), 0)

        # Check for course and sent_on index
        index_fields = [list(index.fields) for index in meta.indexes]
        self.assertTrue(
            any('course' in fields and '-sent_on' in fields for fields in index_fields)
        )

    def test_message_user_relationship(self):
        """Test user foreign key relationship"""
        message = Message.objects.create(
            user=self.user,
            course=self.course,
            content='Test relationship'
        )

        # Test reverse relationship
        user_messages = self.user.chat_messages.all()
        self.assertIn(message, user_messages)

    def test_message_course_relationship(self):
        """Test course foreign key relationship"""
        message = Message.objects.create(
            user=self.user,
            course=self.course,
            content='Test relationship'
        )

        # Test reverse relationship
        course_messages = self.course.chat_messages.all()
        self.assertIn(message, course_messages)

    def test_message_protect_on_delete(self):
        """Test that deleting user or course is protected when messages exist"""
        message = Message.objects.create(
            user=self.user,
            course=self.course,
            content='Protected message'
        )

        # Attempting to delete should raise ProtectedError
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.user.delete()

        with self.assertRaises(ProtectedError):
            self.course.delete()

    def test_multiple_messages_per_user(self):
        """Test that a user can have multiple messages"""
        Message.objects.create(
            user=self.user,
            course=self.course,
            content='Message 1'
        )
        Message.objects.create(
            user=self.user,
            course=self.course,
            content='Message 2'
        )
        Message.objects.create(
            user=self.user,
            course=self.course,
            content='Message 3'
        )

        user_messages = self.user.chat_messages.all()
        self.assertEqual(user_messages.count(), 3)

    def test_multiple_messages_per_course(self):
        """Test that a course can have multiple messages"""
        user2 = User.objects.create_user(username='user2', password='pass')

        Message.objects.create(user=self.user, course=self.course, content='Msg 1')
        Message.objects.create(user=user2, course=self.course, content='Msg 2')

        course_messages = self.course.chat_messages.all()
        self.assertEqual(course_messages.count(), 2)


from django.test import override_settings
from django.urls import reverse


@override_settings(USE_FOUNDRY_UI=True)
class ChatRoomFoundryTests(TestCase):
    """M5: Foundry chat room — two-column layout, Foundry message styling."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="chatinstr", password="pw12345!")
        cls.student = User.objects.create_user(username="chatstu", password="pw12345!")
        cls.subject = Subject.objects.create(title="ChatTopic", slug="m5-chat")
        cls.course = Course.objects.create(
            owner=cls.owner, subject=cls.subject,
            title="M5 Chat Course", slug="m5-chat-course", overview="m5",
        )
        cls.course.students.add(cls.student)

    def setUp(self):
        self.client.login(username="chatstu", password="pw12345!")

    def test_chat_room_uses_foundry_base_when_flag_on(self):
        response = self.client.get(reverse("chat:course_chat_room", args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "foundry_base.html")

    def test_chat_room_renders_two_column_layout(self):
        response = self.client.get(reverse("chat:course_chat_room", args=[self.course.id]))
        # Foundry headers we expect
        self.assertContains(response, "ENROLLED")
        self.assertContains(response, "CHAT")

    def test_chat_room_lists_enrolled_users(self):
        response = self.client.get(reverse("chat:course_chat_room", args=[self.course.id]))
        # The current user should appear in the enrolled-users panel
        self.assertContains(response, "chatstu")

    def test_chat_room_input_present(self):
        response = self.client.get(reverse("chat:course_chat_room", args=[self.course.id]))
        # Message composer
        self.assertContains(response, 'id="chat-message-input"')
        self.assertContains(response, 'id="chat-message-submit"')

    def test_chat_room_websocket_url_in_script(self):
        response = self.client.get(reverse("chat:course_chat_room", args=[self.course.id]))
        # JS bootstrap data still present (existing WS connection)
        self.assertContains(response, "course-id")
        self.assertContains(response, "request-user")
