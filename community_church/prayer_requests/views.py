from django.shortcuts import render, get_object_or_404, redirect
from .models import PrayerRequest, Comment
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.http import HttpResponseForbidden
import logging
from django.utils.timezone import make_aware
from datetime import datetime
from django.db.models import Count
from itertools import groupby
from django.db.models.functions import TruncDate
from django.db.models import Q
from django.contrib import messages
import traceback

# Logging 
logger = logging.getLogger(__name__)

# Home view to list all prayer requests
@login_required
def home(request):
    try:
        print(f"User authenticated: {request.user.is_authenticated}")
        print(f"User: {request.user}")
        
        if request.user.is_authenticated:
            prayer_types = PrayerRequest.PRAYER_TYPES
            requests = PrayerRequest.objects.filter(is_answered=False)

            # Detailed logging of request parameters
            logger.error(f"Request GET parameters: {request.GET}")

            # Search by keyword
            search_query = request.GET.get('search', '').strip()
            if search_query:
                requests = requests.filter(
                    Q(title__icontains=search_query) | 
                    Q(description__icontains=search_query)
                )

            # Filter by date range
            start_date_str = request.GET.get('start_date', '')
            end_date_str = request.GET.get('end_date', '')
            start_date = None
            end_date = None

            if start_date_str and end_date_str:
                try:
                    start_date = make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
                    end_date = make_aware(datetime.strptime(end_date_str, '%Y-%m-%d'))
                    # Extend end_date to include the entire day
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                    requests = requests.filter(created_at__range=[start_date, end_date])
                except Exception as date_error:
                    logger.error(f"Date parsing error: {date_error}")
                    logger.error(f"Start date: {start_date_str}, End date: {end_date_str}")
                    messages.error(request, f"Invalid date format: {date_error}")

            # Multi-select prayer type filtering
            prayer_types_filter = request.GET.getlist('prayer_types')
            logger.error(f"Prayer types filter: {prayer_types_filter}")
            if prayer_types_filter:
                requests = requests.filter(prayer_type__in=prayer_types_filter)

            # Sorting options
            sort_by = request.GET.get('sort_by', '-created_at')
            sort_options = {
                'recent': '-created_at',
                'most_commented': '-comments_count',
                'most_viewed': '-views_count'
            }
            sort_field = sort_options.get(sort_by, '-created_at')
            logger.error(f"Sort by: {sort_by}, Sort field: {sort_field}")

            # Annotate with comments count
            requests = requests.annotate(
                comments_count=Count('comments', distinct=True)
            )

            # Order the requests
            requests = requests.order_by(sort_field)

            # Group by date for display
            requests = requests.annotate(date=TruncDate('created_at'))
            grouped_requests = {
                date: list(group) for date, group in groupby(requests, key=lambda x: x.date)
            }

            context = {
                'grouped_requests': grouped_requests,
                'prayer_types': prayer_types,
                'current_search': search_query,
                'current_prayer_types': prayer_types_filter,
                'current_sort': sort_by,
                'start_date': start_date_str,
                'end_date': end_date_str,
            }
            return render(request, 'prayer_requests/home.html', context)
        else:
            return render(request, 'prayer_requests/home.html')
    except Exception as e:
        # Log the full stack trace
        logger.error(f"Unexpected error in home view: {e}")
        logger.error(traceback.format_exc())
        # Re-raise the exception to see the full error
        raise

# Detail view for a specific prayer request
def prayer_request_detail(request, pk):
    prayer_request = get_object_or_404(PrayerRequest, pk=pk)
    comments = prayer_request.comments.all()
    
    if request.method == 'POST' and request.user.is_authenticated:
        comment_text = request.POST.get('comment')
        if comment_text:
            Comment.objects.create(
                prayer_request=prayer_request,
                author=request.user,
                text=comment_text
            )
            messages.success(request, 'Comment added successfully.')
            return redirect('prayer_request_detail', pk=pk)
    
    return render(request, 'prayer_requests/prayer_request_detail.html', {
        'prayer_request': prayer_request,
        'comments': comments
    })

# View to see Answered prayers
@login_required
def answered_prayers(request):
    # Base queryset of answered prayers
    answered_prayers_qs = PrayerRequest.objects.filter(is_answered=True)
    prayer_types = PrayerRequest.PRAYER_TYPES

    # Filtering logic
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    prayer_type = request.GET.get('prayer_type')

    # Apply date range filter
    if start_date and end_date:
        answered_prayers_qs = answered_prayers_qs.filter(
            answered_at__date__range=[start_date, end_date]
        )
    
    # Apply prayer type filter
    if prayer_type:
        answered_prayers_qs = answered_prayers_qs.filter(prayer_type=prayer_type)

    # Sorting
    answered_prayers_qs = answered_prayers_qs.order_by('-answered_at')

    # Pagination
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(answered_prayers_qs, 9)  # 9 prayers per page
    page = request.GET.get('page')
    try:
        answered_prayers = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        answered_prayers = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        answered_prayers = paginator.page(paginator.num_pages)

    context = {
        'answered_prayers': answered_prayers,
        'prayer_types': prayer_types,
    }
    return render(request, 'prayer_requests/answered_prayers.html', context)

# View to mark a prayer as answered
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

def report_view(request):
    from django.db.models import Count, Avg, F, ExpressionWrapper, fields
    from django.db.models.functions import TruncDate, ExtractHour
    from datetime import datetime, timedelta
    import json
    from django.core.serializers.json import DjangoJSONEncoder
    from django.contrib.auth.models import User
    from django.db.models import Q

    # Date range filter
    date_filter = request.GET.get('date_range', '30')  # Default to 30 days
    try:
        days = int(date_filter)
    except ValueError:
        days = 30

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)

    # Basic statistics
    total_requests = PrayerRequest.objects.count()
    answered_prayers = PrayerRequest.objects.filter(is_answered=True).count()
    open_requests = PrayerRequest.objects.filter(is_answered=False).count()
    recent_requests = PrayerRequest.objects.order_by('-created_at')[:10]

    # User engagement metrics
    total_users = User.objects.count()
    active_users = User.objects.filter(
        prayerrequest__created_at__date__range=[start_date, end_date]
    ).distinct().count()
    
    # Prayer response metrics
    avg_response_time = PrayerRequest.objects.filter(
        is_answered=True,
        answered_at__isnull=False
    ).annotate(
        response_time=ExpressionWrapper(
            F('answered_at') - F('created_at'),
            output_field=fields.DurationField()
        )
    ).aggregate(avg=Avg('response_time'))

    avg_days = avg_response_time['avg'].days if avg_response_time['avg'] else 0

    # Prayer Type Chart Data
    prayer_type_labels = [type[1] for type in PrayerRequest.PRAYER_TYPES]
    prayer_type_data = [PrayerRequest.objects.filter(
        prayer_type=type[0],
        created_at__date__range=[start_date, end_date]
    ).count() for type in PrayerRequest.PRAYER_TYPES]

    # Status Chart Data
    status_labels = ['Answered', 'Open']
    status_data = [answered_prayers, open_requests]

    # Trend Chart Data
    daily_counts = (
        PrayerRequest.objects
        .filter(created_at__date__range=[start_date, end_date])
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(
            total=Count('id'),
            answered=Count('id', filter=Q(is_answered=True))
        )
        .order_by('date')
    )

    # Create a complete date range with zeros
    date_range = {(start_date + timedelta(days=x)).strftime('%m/%d/%Y'): {'total': 0, 'answered': 0}
                 for x in range(days)}
    
    # Fill in actual counts
    for entry in daily_counts:
        date_str = entry['date'].strftime('%m/%d/%Y')
        date_range[date_str] = {
            'total': entry['total'],
            'answered': entry['answered']
        }

    # Time of Day Analysis
    hour_analysis = (
        PrayerRequest.objects
        .filter(created_at__date__range=[start_date, end_date])
        .annotate(hour=ExtractHour('created_at'))
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('hour')
    )

    # Prepare data for charts
    trend_labels = list(date_range.keys())
    trend_total_data = [date_range[date]['total'] for date in trend_labels]
    trend_answered_data = [date_range[date]['answered'] for date in trend_labels]

    # Convert 24h to 12h format with AM/PM
    hour_labels = [
        (f"{h%12 or 12}:00 {'AM' if h<12 else 'PM'}")
        for h in [entry['hour'] for entry in hour_analysis]
    ]
    hour_data = [entry['count'] for entry in hour_analysis]

    # Ensure JSON serialization
    context = {
        'total_requests': total_requests,
        'answered_prayers': answered_prayers,
        'open_requests': open_requests,
        'recent_requests': recent_requests,
        'total_users': total_users,
        'active_users': active_users,
        'avg_response_days': avg_days,

        # Chart data with JSON-safe serialization
        'prayer_type_data': json.dumps(prayer_type_data, cls=DjangoJSONEncoder),
        'prayer_type_labels': json.dumps(prayer_type_labels, cls=DjangoJSONEncoder),
        'status_data': json.dumps(status_data, cls=DjangoJSONEncoder),
        'status_labels': json.dumps(status_labels, cls=DjangoJSONEncoder),
        'trend_labels': json.dumps(trend_labels, cls=DjangoJSONEncoder),
        'trend_total_data': json.dumps(trend_total_data, cls=DjangoJSONEncoder),
        'trend_answered_data': json.dumps(trend_answered_data, cls=DjangoJSONEncoder),
        'hour_labels': json.dumps(hour_labels, cls=DjangoJSONEncoder),
        'hour_data': json.dumps(hour_data, cls=DjangoJSONEncoder)
    }

    return render(request, 'prayer_requests/report.html', context)

@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    
    # Check if user has permission to edit
    if not (request.user == comment.author or request.user.is_superuser):
        return HttpResponseForbidden("You don't have permission to edit this comment.")
    
    if request.method == 'POST':
        new_text = request.POST.get('comment_text')
        if new_text:
            comment.text = new_text
            comment.save()
            messages.success(request, 'Comment updated successfully.')
        return redirect('prayer_request_detail', pk=comment.prayer_request.pk)
    
    return HttpResponseForbidden("Invalid request method.")

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    
    # Check if user has permission to delete
    if not (request.user == comment.author or request.user.is_superuser):
        return HttpResponseForbidden("You don't have permission to delete this comment.")
    
    if request.method == 'POST':
        prayer_request_id = comment.prayer_request.pk
        comment.delete()
        messages.success(request, 'Comment deleted successfully.')
        return redirect('prayer_request_detail', pk=prayer_request_id)
    
    return HttpResponseForbidden("Invalid request method.")