# events/admin.py
from django.contrib import admin
from .models import Event, UploadedFile
import os
from django.utils.html import format_html

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'country', 'promoter_type', 'style', 'event_date', 'latitude', 'longitude', 'added_by')
    list_filter = ('promoter_type', 'country', 'city', 'style', 'event_date', ('latitude', admin.EmptyFieldListFilter), ('longitude', admin.EmptyFieldListFilter))
    search_fields = ('name', 'city', 'country', 'description', 'promoter_type', 'style', 'contact_email', 'booker_name')
    readonly_fields = ('created_at', 'updated_at', 'added_by')
    fieldsets = (
        (None, {'fields': ('name', 'latitude', 'longitude')}),
        ('Localisation', {'fields': ('city', 'country')}),
        ('Détails Événement', {'fields': ('promoter_type', 'style', 'event_date', 'description')}),
        ('Contact', {'fields': ('contact_email', 'booker_name')}),
        ('Métadonnées', {'fields': ('added_by', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('file_link', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_by', 'uploaded_at')
    readonly_fields = ('uploaded_at', 'uploaded_by', 'file_link')

    def file_link(self, obj):
        if obj.file:
            return format_html("<a href='{url}' target='_blank'>{name}</a>", url=obj.file.url, name=os.path.basename(obj.file.name))
        return "Pas de fichier"
    file_link.short_description = "Fichier Excel"
    file_link.admin_order_field = 'file'