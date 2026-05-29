import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from chat.models import Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        from courses.models import Course

        self.user = self.scope['user']

        # Reject unauthenticated users
        if not self.user.is_authenticated:
            await self.close()
            return

        self.id = self.scope['url_route']['kwargs']['course_id']

        # Load course once and verify the user is enrolled (or owner/staff).
        try:
            self.course = await Course.objects.aget(id=int(self.id))
        except (Course.DoesNotExist, ValueError, TypeError):
            await self.close()
            return

        is_member = await self._user_can_access_course()
        if not is_member:
            await self.close()
            return

        self.room_group_name = f'chat_{self.id}'
        # join room group
        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )
        # accept connection
        await self.accept()

    async def _user_can_access_course(self):
        """Allow course owner, staff, or enrolled students."""
        if self.user.is_staff or self.course.owner_id == self.user.id:
            return True
        return await self.course.students.filter(id=self.user.id).aexists()

    async def disconnect(self, close_code):
        # leave room group (only if we joined one)
        group = getattr(self, 'room_group_name', None)
        if group:
            await self.channel_layer.group_discard(
                group, self.channel_name
            )

    # persist message to database (reuses cached course FK)
    async def persist_message(self, message):
        await Message.objects.acreate(
            user=self.user, course=self.course, content=message
        )

    # receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        now = timezone.now()
        # send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user': self.user.username,
                'datetime': now.isoformat(),
            },
        )
        # persist message
        await self.persist_message(message)

    # receive message from room group
    async def chat_message(self, event):
        # send message to WebSocket
        await self.send(text_data=json.dumps(event))
