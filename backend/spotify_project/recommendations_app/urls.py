from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import *
from .views_api import *
from .models import *
from rest_framework import routers
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


router = routers.DefaultRouter()
router.register(r'profile', ProfileViewSet)
router.register(r'room', RoomViewSet)

urlpatterns = [
    path('', Home, name='home'),
    path('spotify_login/', spotify_login, name='spotify_login'),
    path('auth-complete/', spotify_auth_complete, name='spotify_auth_complete'),
    path('profile/', spotify_profile, name='spotify_profile'),
    path('logout/', logout, name='logout'),
    path('profile/following/', manage_following, name='manage_following'),
    path('recommendations/', recommendation_page, name='recommendation_page'),
    path('get-recommendations/', get_recommendation, name='get_recommendation'),
    path('group_recommendations/', group_recommendation_page, name='group_recommendation_page'),
    path('get_group_recommendations', get_group_recommendation, name='get_group_recommendation'),
    path('search_page/', search_page, name='search_page'),
    path('profile/<str:id>', view_profile, name='view_profile'),
    path('Follow/<str:id>', follow, name='follow'),
    path('Set_Preferences/', set_preferences, name='set_preferences'),
    path('Visibility/', change_visibility, name='change_visibility'),
    path('profile/presets/', presets, name='presets'),
    path('profile/presets/delete/<str:name>', delete_preset, name='delete_preset'),
    path('spotify-group-recommendations/', spotify_group_recommendations, name='spotify_group_rec'),
    path('room/<str:room_code>/', room_view, name='room_view'),
    path('room/<str:room_code>/generate/', generate_room_mix, name='generate_room_mix'),
    path('make-playlist/', make_spotify_playlist, name='make_spotify_playlist'),
    path('api/', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/search/', api_search_page, name='api_search'),
    path('api/spotify-login/', spotify_login_api, name='spotify_login_api'),
    path('api/spotify-auth-complete/', spotify_auth_complete_api, name='spotify_auth_complete_api'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/logout/', logout_api, name='logout_api'),
    path('api/current-user/', current_user_api, name='current_user_api'),
    path('api/get-following/', get_following_api, name="get_following_api"),
    path('api/search-profiles/', api_search_profiles, name='search_profiles_api'),
    path('api/visibility/', change_visibility_api, name="change_visibility_api"),
    #path('api/search-profiles-term/<str:term>', api_search_profiles_term, name='search_profiles_term_api'),
    path('api/view-profile/<str:spotify_id>', view_profile_api, name="view_profile_api"),
    path('api/follow/<str:spotify_id>', follow_api, name="follow_api"),
    path('api/test-session/', test_session, name='test_session'),
    path('api/set-preferences/', set_preferences_api, name="set_preferences_api"),
    path('api/presets/add/', add_preset_api, name="add_preset_api"),
    path('api/presets/delete/', delete_preset_api, name="delete_preset_api"),
    path('api/genres/', get_genres_api, name='genres_api'),
    path('api/get-recommendations/', get_recommendations_api, name="get_recommendations_api"),
    path('api/get-presets/', get_presets_api, name='get_presets_api'),
    path('api/get-group-recommendations/', get_group_recommendations_api, name="get_group_recommendations_api"),
    path('api/make_playlist_api', make_spotify_playlist_api, name="make_spotify_playlist_api"),
]

