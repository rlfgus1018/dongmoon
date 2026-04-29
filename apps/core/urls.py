from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("schools/", views.school_search, name="school_search"),
    path("schools/<str:code>/", views.school_detail, name="school_detail"),
    path(
        "schools/<str:code>/favorite/",
        views.toggle_school_favorite,
        name="toggle_school_favorite",
    ),
    path(
        "schools/<str:code>/guestbook/",
        views.create_guestbook_entry,
        name="create_guestbook_entry",
    ),
    path("schools/<str:code>/posts/", views.create_post, name="create_post"),
    path("schools/<str:code>/posts/<int:post_id>/", views.post_detail, name="post_detail"),
    path(
        "schools/<str:code>/posts/<int:post_id>/delete/",
        views.delete_post,
        name="delete_post",
    ),
    path(
        "schools/<str:code>/posts/<int:post_id>/comments/",
        views.create_comment,
        name="create_comment",
    ),
    path(
        "schools/<str:code>/posts/<int:post_id>/comments/<int:comment_id>/delete/",
        views.delete_comment,
        name="delete_comment",
    ),
    path(
        "schools/<str:code>/posts/<int:post_id>/recommend/",
        views.recommend_post,
        name="recommend_post",
    ),
    path("schools/<str:code>/posts/<int:post_id>/report/", views.report_post, name="report_post"),
    path(
        "schools/<str:code>/posts/<int:post_id>/comments/<int:comment_id>/report/",
        views.report_comment,
        name="report_comment",
    ),
    path(
        "schools/<str:code>/moderation/",
        views.moderation_dashboard,
        name="moderation_dashboard",
    ),
    path(
        "schools/<str:code>/moderation/posts/<int:post_id>/<str:action>/",
        views.moderate_post,
        name="moderate_post",
    ),
    path(
        "schools/<str:code>/moderation/posts/<int:post_id>/comments/<int:comment_id>/<str:action>/",
        views.moderate_comment,
        name="moderate_comment",
    ),
    path("health/", views.health, name="health"),
]
