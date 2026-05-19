from django.core.management.base import BaseCommand
from recommendations_app.models import *
from recommendations_app.helper_functions import *
import random

class Command(BaseCommand):
    help = 'Creates fake users and establishes relationships'
    
    def add_arguments(self, parser):
        parser.add_argument('--num_create', type=int, default=10, help='Number of fake users to create')
        parser.add_argument('--related', type=str, default='smartademide1303', help='Comma-separated real user spotify_ids')
        parser.add_argument('--to_follow', type=int, default=5, help='Number of fake users real users follow')
        parser.add_argument('--who_follow', type=int, default=5, help='Number of fake users following real users')
    
    def handle(self, *args, **options):
        # Parse related users
        related_users = []
        num_create = options['num_create']
        related_ids = options['related']
        num_to_follow = options['to_follow']
        num_who_follow = options['who_follow']

        related_ids = comma_seperation(related_ids)

        for id in related_ids:
            try:
                user = Profile.objects.get(spotify_id=id)
                related_users.append(user)
            except Profile.DoesNotExist:
                print(f"Warning: User '{id}' not found")
        
        if not related_users:
            print("No valid related users found")
            return
        
        fake_users = []
        for x in range(num_create):
            profile, _ = Profile.objects.update_or_create(
                    spotify_id=f'fake_user{x}an_id',
                    defaults={
                        'name': f'fake_user{x}',
                        'email': f'fake_email{x}@example.com',
                    }
                )
            fake_users.append(profile)
        
        if num_to_follow > num_create:
            num_to_follow = num_create

        if num_who_follow > num_create:
            num_who_follow = num_create

        for real in related_users:
            to_follow = random.sample(fake_users, num_to_follow)
            for x in to_follow:
                real.following.append(x.spotify_id)
            real.save()

            will_follow = random.sample(fake_users, num_to_follow)
            for x in will_follow:
                x.following.append(real.spotify_id)
                x.save()

        print(f"Created {len(fake_users)} fake users")
        print(f"Established relationships with {len(related_users)} real users")