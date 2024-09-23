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
    path('answered-prayers/', views.answered_prayers, name='answered_prayers'),
]