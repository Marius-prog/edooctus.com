from django.conf import settings
from django.db import models


class Message(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='chat_messages',
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.PROTECT,
        related_name='chat_messages',
    )
    content = models.TextField()
    sent_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_on']
        indexes = [
            models.Index(fields=['course', '-sent_on']),
            models.Index(fields=['user', '-sent_on']),
        ]

    def __str__(self):
        return f'{self.user} on {self.course} at {self.sent_on}'