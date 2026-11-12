from django.contrib.auth import views as auth_views
from django.urls import path

from . import api, views

app_name = "books"

urlpatterns = [
    path("", views.home, name="home"),
    path("api/progress/", api.ReadingProgressAPIView.as_view(), name="api_progress"),
    path("accounts/register/", views.register, name="register"),
    path(
        "accounts/login/",
        views.WBooksLoginView.as_view(),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(next_page="books:home"),
        name="logout",
    ),
    path("dashboard/", views.dashboard, name="dashboard"),
    path(
        "dashboard/parent/", views.parent_dashboard, name="parent_dashboard"
    ),
    path("dashboard/child/", views.child_dashboard, name="child_dashboard"),
    path("quiz/general/", views.general_quiz, name="general_quiz"),
    path("quiz/results/<int:pk>/", views.quiz_result, name="quiz_result"),
    path("books/<slug:slug>/", views.book_detail, name="book_detail"),
    path("books/<slug:slug>/read/", views.reader, name="reader"),
    path("books/<slug:slug>/recap/", views.recap, name="recap"),
    path("books/<slug:slug>/quiz/", views.quiz, name="quiz"),
    path(
        "books/<slug:slug>/progress/",
        views.update_progress,
        name="update_progress",
    ),
]
