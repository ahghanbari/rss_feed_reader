from django.contrib import admin
from django.utils.safestring import mark_safe

from feeds import models


class PostAdmin(admin.ModelAdmin):
    raw_id_fields = ('source',)
    list_display = ('id', 'title', 'source', 'user', 'created', 'guid', 'author')
    search_fields = ('title',)
    ordering = ('-created',)

class SourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'last_result', 'live', 'num_of_failed_polls')
    search_fields = ('title',)

admin.site.register(models.Source, SourceAdmin)
admin.site.register(models.Post, PostAdmin)
