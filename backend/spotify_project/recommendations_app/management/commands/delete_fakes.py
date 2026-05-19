from django.core.management.base import BaseCommand
from recommendations_app.models import *
from recommendations_app.helper_functions import *
from django.db.models import Q


class Command(BaseCommand):
    help = 'Deletes fake users created by the fake users command'
    
    def handle(self, *args, **options):
        fakes = Profile.objects.filter(spotify_id__startswith='fake_user')
        non_fakes = Profile.objects.filter(~Q(spotify_id__startswith='fake_user'))
        fake_ids = [profile.spotify_id for profile in Profile.objects.filter(spotify_id__startswith='fake_user')]
        num_fakes = len(fakes)
        for profile in non_fakes:
            profile.following = [spotify_id for spotify_id in profile.following if spotify_id not in fake_ids]
            profile.save()
        fakes.delete()
        print(f'Deleted {num_fakes} profiles')