from django.shortcuts import render, get_object_or_404, redirect
from .models import PrayerRequest
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.http import HttpResponseForbidden
import logging
from django.utils.timezone import make_aware
from datetime import datetime
from django.contrib import messages
from django.db.models import Count
from itertools import groupby
from django.db.models.functions import TruncDate

# Logging 
logger = logging.getLogger(__name__)

# Home view to list all prayer requests
def home(request):
    if request.user.is_authenticated:
        prayer_types = PrayerRequest.PRAYER_TYPES
        #requests = PrayerRequest.objects.all()
        requests = PrayerRequest.objects.filter(is_answered=False)

        # Filter by date range
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
            end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
            requests = requests.filter(created_at__range=[start_date, end_date])

        # Filter by prayer type
        prayer_type = request.GET.get('prayer_type')
        if prayer_type:
            requests = requests.filter(prayer_type=prayer_type)

        requests = requests.annotate(date=TruncDate('created_at')).order_by('-date', '-created_at')
        grouped_requests = {
            date: list(group) for date, group in groupby(requests, key=lambda x: x.date)
        }

        context = {
            'grouped_requests': grouped_requests,
            'prayer_types': prayer_types,
        }
        return render(request, 'prayer_requests/home.html', context)
    else:
        return render(request, 'prayer_requests/home.html')

# Detail view for a specific prayer request
def prayer_request_detail(request, pk):
    prayer_request = get_object_or_404(PrayerRequest, pk=pk)
    return render(request, 'prayer_requests/prayer_request_detail.html', {'prayer_request': prayer_request})

# View to see Answered prayers
@login_required
def answered_prayers(request):
    answered_prayers = PrayerRequest.objects.filter(is_answered=True)
    prayer_types = PrayerRequest.PRAYER_TYPES
    context = {
        'answered_prayers': answered_prayers,
        'prayer_types': prayer_types,
    }
    return render(request, 'prayer_requests/answered_prayers.html', context)

# View to see Answered prayers
@login_required
def mark_prayer_answered(request, pk):
    prayer_request = get_object_or_404(PrayerRequest, pk=pk)
    if request.user == prayer_request.created_by or request.user.is_superuser:
        prayer_request.mark_as_answered()
        return redirect('answered_prayers')
    else:
        # Handle unauthorized access
        return redirect('home')

# View to mark a prayer as unanswered
@login_required
def mark_prayer_unanswered(request, pk):
    prayer_request = get_object_or_404(PrayerRequest, pk=pk)
    if request.user == prayer_request.created_by or request.user.is_superuser:
        prayer_request.is_answered = False
        prayer_request.answered_at = None
        prayer_request.save()
        return redirect('home')
    else:
        # Handle unauthorized access
        return redirect('answered_prayers')    

# View to create a new prayer request
@login_required
def create_prayer_request(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        prayer_type = request.POST.get('prayer_type')
        PrayerRequest.objects.create(title=title, description=description, created_by=request.user, prayer_type=prayer_type)
        messages.success(request, 'Prayer request created successfully.')
        return redirect('home')
    return render(request, 'prayer_requests/create_prayer_request.html', {'prayer_types': PrayerRequest.PRAYER_TYPES})


# View to edit a prayer request
@login_required
def edit_prayer_request(request, pk):
    prayer_request = get_object_or_404(PrayerRequest, pk=pk)
    if request.user != prayer_request.created_by and not request.user.is_superuser:
        messages.error(request, "You don't have permission to edit this prayer request.")
        return redirect('home')

    if request.method == 'POST':
        prayer_request.title = request.POST.get('title')
        prayer_request.description = request.POST.get('description')
        prayer_request.prayer_type = request.POST.get('prayer_type')
        
        # Handle the "Answered" checkbox
        if 'is_answered' in request.POST and not prayer_request.is_answered:
            prayer_request.mark_as_answered()
        elif 'is_answered' not in request.POST and prayer_request.is_answered:
            prayer_request.is_answered = False
            prayer_request.answered_at = None

        prayer_request.save()
        messages.success(request, 'Prayer request updated successfully.')
        return redirect('home')

    return render(request, 'prayer_requests/edit_prayer_request.html', {
        'prayer_request': prayer_request, 
        'prayer_types': PrayerRequest.PRAYER_TYPES
    })

# Delete a prayer request view
@login_required
def delete_prayer_request(request, pk):
    prayer_request = get_object_or_404(PrayerRequest, pk=pk)
    if request.user != prayer_request.created_by and not request.user.is_superuser:
        return HttpResponseForbidden("You don't have permission to delete this prayer request.")
    
    if prayer_request.is_answered and not request.user.is_superuser:
        messages.error(request, "Answered prayers cannot be deleted.")
        return redirect('prayer_request_detail', pk=prayer_request.pk)

    if request.method == 'POST':
        prayer_request.delete()
        return redirect('home')
    
    return redirect('prayer_request_detail', pk=prayer_request.pk)

# Sign up page
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'prayer_requests/signup.html', {'form': form})

# Profile page
@login_required
def profile(request):
    prayer_requests = PrayerRequest.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'prayer_requests/profile.html', {'prayer_requests': prayer_requests})

# About page
def about(request):
    return render(request, 'prayer_requests/about.html')

# 404 error page
def error_404(request, exception):
    logger.error('Custom 404 page requested')
    #data = {"name": "404 page requested"}
    return render(request,'404.html', status=404)

# 500 error page
def error_500(request):
    logger.error('Custom 500 page requested')
    #data = {"name": "500 page requested"}
    return render(request, '500.html', status=500)

# Prayer request types
def prayer_request_types(request):
    prayer_types = [
        {
            "name": "Unspoken Prayer Requests",
            "description": "These are for individuals who have a personal or sensitive need but choose not to share the details.",
            "examples": [
                "Please pray for me as I face some personal challenges. God knows the details.",
                "I have an unspoken prayer request that I would appreciate prayers for."
            ]
        },
        {
            "name": "Verbal Prayer Requests",
            "description": "These are specific needs or situations shared openly.",
            "examples": [
                "Please pray for my grandmother, who is undergoing surgery next week.",
                "I ask for prayers for my upcoming job interview that I may find peace and confidence."
            ]
        },
        {
            "name": "Health-related Prayer Requests",
            "description": "For individuals who need healing or support in times of illness.",
            "examples": [
                "Praying for my friend who is battling cancer. May God grant her strength and healing.",
                "Please pray for my father's recovery from his recent heart surgery."
            ]
        },
        {
            "name": "Family-related Prayer Requests",
            "description": "These could involve issues like marriage, children, or general family struggles.",
            "examples": [
                "Pray for reconciliation in my marriage as we work through some difficulties.",
                "Please pray for my son, who is struggling with depression."
            ]
        },
        {
            "name": "Guidance Prayer Requests",
            "description": "Requests for divine guidance in decision-making or life transitions.",
            "examples": [
                "I'm seeking God's guidance as I decide whether to move to a new city for work.",
                "Please pray that God leads me in the right direction as I apply to universities."
            ]
        },
        {
            "name": "Praise Reports/Thanksgiving",
            "description": "These are positive updates or gratitude for answered prayers.",
            "examples": [
                "Thank you, Lord, for providing me with a new job after months of searching!",
                "I'm thankful for the safe arrival of our baby boy. God has been good."
            ]
        },
        {
            "name": "Community Prayer Requests",
            "description": "Prayer for larger groups or causes, such as communities or nations.",
            "examples": [
                "Pray for our community as we recover from the recent storm.",
                "Please pray for peace in our nation and wisdom for our leaders."
            ]
        },
        {
            "name": "Spiritual Growth",
            "description": "Requests for deepening faith or overcoming spiritual struggles.",
            "examples": [
                "Pray for me as I seek to grow closer to God and be more disciplined in my faith.",
                "Please pray that God strengthens my faith during this season of doubt."
            ]
        }
    ]
    return render(request, 'prayer_requests/prayer_request_types.html', {'prayer_types': prayer_types})
# Prayer Request Reports view
def report_view(request):
    total_requests = PrayerRequest.objects.count()
    answered_prayers = PrayerRequest.objects.filter(is_answered=True).count()
    open_requests = PrayerRequest.objects.filter(is_answered=False).count()
    recent_requests = PrayerRequest.objects.order_by('-created_at')[:10]

    # Prayer Type Chart Data
    prayer_type_labels = [type[1] for type in PrayerRequest.PRAYER_TYPES]
    prayer_type_data = [PrayerRequest.objects.filter(prayer_type=type[0]).count() for type in PrayerRequest.PRAYER_TYPES]

    # Status Chart Data
    status_labels = ['Answered', 'Open']
    status_data = [answered_prayers, open_requests]

    context = {
        'total_requests': total_requests,
        'answered_prayers': answered_prayers,
        'open_requests': open_requests,
        'recent_requests': recent_requests,
        'prayer_type_labels': prayer_type_labels,
        'prayer_type_data': prayer_type_data,
        'status_labels': status_labels,
        'status_data': status_data,
    }

    return render(request, 'prayer_requests/report.html', context)