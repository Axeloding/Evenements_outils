# events/models.py
from django.db import models
from django.contrib.auth.models import User
import os

class Event(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nom Lieu / Promoter")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ville", db_index=True) # Index pour recherche
    latitude = models.FloatField(blank=True, null=True, verbose_name="Latitude")
    longitude = models.FloatField(blank=True, null=True, verbose_name="Longitude")
    description = models.TextField(blank=True, null=True, verbose_name="Comments")
    event_date = models.DateTimeField(blank=True, null=True, verbose_name="Date de l'événement")
    country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Pays", db_index=True) # Index pour recherche
    contact_email = models.TextField(blank=True, null=True, verbose_name="Mail Contact")
    booker_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Booker name")
    promoter_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Promoter Type", db_index=True) # Index pour filtre
    style = models.CharField(max_length=100, blank=True, null=True, verbose_name="Style")
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Ajouté par")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création", db_index=True) # Index pour tri
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière mise à jour")

    def __str__(self):
        return self.name if self.name else "Événement sans nom"

    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ['-created_at', 'name']

class UploadedFile(models.Model):
    file = models.FileField(upload_to='excel_uploads/', verbose_name="Fichier Excel")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'import")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Importé par")

    def __str__(self):
        filename = os.path.basename(self.file.name) if self.file else "Fichier non défini"
        user_str = self.uploaded_by.username if self.uploaded_by else "Utilisateur inconnu"
        date_str = self.uploaded_at.strftime('%d/%m/%Y %H:%M') if self.uploaded_at else "Date inconnue"
        return f"{filename} par {user_str} le {date_str}"

    class Meta:
        verbose_name = "Fichier importé"
        verbose_name_plural = "Fichiers importés"
        ordering = ['-uploaded_at']