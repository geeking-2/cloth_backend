from django.contrib import admin
from .models import Post, Story, Like, Comment

admin.site.register(Post)
admin.site.register(Story)
admin.site.register(Like)
admin.site.register(Comment)
