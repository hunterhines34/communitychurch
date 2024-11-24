from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here
class PrayerRequest(models.Model):
    PRAYER_TYPES = [
        ('UNSPOKEN', 'Unspoken Prayer Request'),
        ('VERBAL', 'Verbal Prayer Request'),
        ('HEALTH', 'Health-related Prayer Request'),
        ('FAMILY', 'Family-related Prayer Request'),
        ('GUIDANCE', 'Guidance Prayer Request'),
        ('PRAISE', 'Praise Report/Thanksgiving'),
        ('COMMUNITY', 'Community Prayer Request'),
        ('SPIRITUAL', 'Spiritual Growth'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    prayer_type = models.CharField(max_length=20, choices=PRAYER_TYPES, default='VERBAL')
    is_answered = models.BooleanField(default=False)
    answered_at = models.DateTimeField(null=True, blank=True)

    def mark_as_answered(self):
        self.is_answered = True
        self.answered_at = timezone.now()
        self.save()

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']     


class Comment(models.Model):
    prayer_request = models.ForeignKey(PrayerRequest, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comment by {self.author.username} on {self.prayer_request.title}'