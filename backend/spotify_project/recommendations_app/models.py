from django.db import models

# Create your models here.
class Profile(models.Model):
    
    spotify_id = models.CharField(max_length=200, primary_key=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    image = models.CharField(max_length=200, null=True, blank=True)
    implicit_preferences = models.JSONField(default=dict, blank=True)
    preferences = models.JSONField(default=dict, blank=True)
    data = models.JSONField(default=dict, blank=True)
    following = models.JSONField(default=list, blank=True)
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    token_expiry = models.DateTimeField(null=True, blank=True) 
    visibility = models.CharField(default='public', max_length=15) #Types, public, following, private
    presets = models.JSONField(default=dict, blank=True) 
    # preset field = {'name of preset 1':
    #                        {artists: list of artists},
    #                        {genres: genres},
    #                         etc,
    #                       'name of preset 2' ... }

    def __str__(self):
        return f"{self.name} ({self.spotify_id})"
    
    @property
    def is_authenticated(self):
        """Required for Django's permission system"""
        return True
    
    @property
    def is_anonymous(self):
        """Required for Django's permission system"""
        return False
    
class Room(models.Model):
    room_code = models.CharField(max_length=4, primary_key=True)
    host = models.ForeignKey(Profile, on_delete=models.CASCADE)
    participants = models.JSONField(default=list, blank=True) 
    #participants = list of spotify_ids of people who joined the room

    def __str__(self):
        return f"Room {self.room_code} (Host: {self.host.name})"


# models.py
from django.db import models

class OAuthState(models.Model):
    state = models.CharField(max_length=100, unique=True)
    code_verifier = models.CharField(max_length=255)
    next_url = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @classmethod
    def cleanup_old_states(cls):
        from datetime import timedelta
        from django.utils import timezone
        cutoff = timezone.now() - timedelta(minutes=10)
        cls.objects.filter(created_at__lt=cutoff).delete()
