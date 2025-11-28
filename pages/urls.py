from django.urls import path
from .views import (
    HomeRedirectView,
    CreateCardView,
    MyCardView,
    ToggleCellView,
    LeaderboardView,
    PublicCardView,
    SuperSettingsView,
    SignUpView,
)

urlpatterns = [
    path("", HomeRedirectView.as_view(), name="home"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("card/create/", CreateCardView.as_view(), name="create_card"),
    path("card/mine/", MyCardView.as_view(), name="my_card"),
    path("card/toggle/<int:cell_id>/", ToggleCellView.as_view(), name="toggle_cell"),
    path("leaderboard/", LeaderboardView.as_view(), name="leaderboard"),
    path("card/<str:username>/", PublicCardView.as_view(), name="public_card"),
    path("game/settings/", SuperSettingsView.as_view(), name="admin_controls"),
]
