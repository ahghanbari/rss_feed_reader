from django.db import models
from django.contrib.auth.models import User

import datetime


class Source(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sources")
    name = models.CharField(max_length=255, blank=True, null=True)
    feed_url = models.CharField(max_length=512)
    image_url = models.CharField(max_length=512, blank=True, null=True)
    description = models.TextField(null=True, blank=True)
    last_result = models.BooleanField(default=True)
    live = models.BooleanField(default=True)
    num_of_failed_polls = models.PositiveIntegerField(default=0)
    next_poll = models.DateTimeField(default=datetime.datetime(1900, 1, 1))

    def __str__(self):
        if self.name is None or self.name == "":
            return self.feed_url
        else:
            return self.name


class Post(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="posts")
    title = models.TextField(blank=True)
    body = models.TextField()
    read = models.BooleanField(default=False)
    link = models.CharField(max_length=512, blank=True, null=True)
    found = models.DateTimeField(auto_now_add=True)
    created = models.DateTimeField(db_index=True)
    guid = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    author = models.CharField(max_length=255, blank=True, null=True)
    index = models.IntegerField(db_index=True)
    image_url = models.CharField(max_length=512, blank=True, null=True)

    @property
    def user(self):
        return self.source.user

    def __str__(self):
        return "%s: post %d, %s" % (str(self.source), self.index, self.title)
