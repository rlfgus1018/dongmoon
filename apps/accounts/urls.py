from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

app_name = "accounts"

urlpatterns = [
    path("me/", views.mypage, name="mypage"),
    path(
        "me/school-verification/",
        views.request_school_verification,
        name="request_school_verification",
    ),
    path("me/school-search/", views.school_search_api, name="school_search_api"),
    path("login/", auth_views.LoginView.as_view(authentication_form=LoginForm), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("users/<int:user_id>/", views.user_profile, name="user_profile"),
]
