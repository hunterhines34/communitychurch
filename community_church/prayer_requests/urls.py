from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create/', views.create_prayer_request, name='create_prayer_request'),
    path('request/<int:pk>/', views.prayer_request_detail, name='prayer_request_detail'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='prayer_requests/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='prayer_requests/logout.html'), name='logout'),
    path('about/', views.about, name='about'),
    path('profile/', views.profile, name='profile'),
    path('prayer-request/<int:pk>/edit/', views.edit_prayer_request, name='edit_prayer_request'),
    path('prayer-request/<int:pk>/delete/', views.delete_prayer_request, name='delete_prayer_request'),
    path('prayer-request-types/', views.prayer_request_types, name='prayer_request_types'),
    path('answered/', views.answered_prayers, name='answered_prayers'),
    path('mark-answered/<int:pk>/', views.mark_prayer_answered, name='mark_prayer_answered'),
    path('mark-unanswered/<int:pk>/', views.mark_prayer_unanswered, name='mark_prayer_unanswered'),
    path('report/', views.report_view, name='prayer_request_report'),
    # Password reset urls
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]