# serializers.py created inside your app folder
from rest_framework import serializers
from .models import *

class ProfileSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = Profile
		fields = ['spotify_id',
			        'name', 'email', 
					'image', 'implicit_preferences',
					'preferences',
					'presets', 
					'data', 'following', 
					'access_token', 
					'refresh_token']
		
class RoomSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = Room
		fields = ['room_code', 'host', 'participants']