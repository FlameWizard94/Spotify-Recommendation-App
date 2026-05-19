from django.core.management.base import BaseCommand
from recommendations_app.models import *
from recommendations_app.helper_functions import ARTISTS, GENRES, RANKING_TYPES
from django.db.models import Q
import random


class Command(BaseCommand):
    help = 'Creates fake presets'

    def handle(self, *args, **options):
        fakes = Profile.objects.filter(spotify_id__startswith='fake_user')
        for fake in fakes:
            for x in range(3):
                new_preset_data = {}
                new_preset_data['artists'] = random.sample(ARTISTS, random.randint(1, 3))
                new_preset_data['genres'] = random.sample(GENRES, random.randint(1, 3))
                new_preset_data['num_tracks'] = random.randint(1, 50)
                new_preset_data['ranking'] = random.sample(RANKING_TYPES, 1)[0]
                fake.presets[f'fake_preset{x}'] = new_preset_data

            fake.save()

        print(f'{len(fakes)} presets created')