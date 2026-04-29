from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.models import School

from .forms import ProfileForm, SchoolVerificationForm, SignUpForm
from .models import Profile


def signup(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("core:school_search")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            return redirect("core:school_search")
    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})


def user_profile(request: HttpRequest, user_id: int) -> HttpResponse:
    profile_user = get_object_or_404(User, id=user_id)
    Profile.objects.get_or_create(user=profile_user)
    return render_profile(request, profile_user, is_mypage=False)


@login_required
def mypage(request: HttpRequest) -> HttpResponse:
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("accounts:mypage")
    return render_profile(request, request.user, is_mypage=True, form=ProfileForm(instance=profile))


@login_required
def request_school_verification(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SchoolVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            verification = form.save(commit=False)
            verification.user = request.user
            verification.save()
    return redirect("accounts:mypage")


@login_required
def school_search_api(request: HttpRequest) -> JsonResponse:
    query = request.GET.get("q", "").strip()
    schools = School.objects.none()
    if query:
        schools = School.objects.filter(
            Q(name__icontains=query)
            | Q(region__icontains=query)
            | Q(road_address__icontains=query)
        )[:10]

    return JsonResponse(
        {
            "results": [
                {
                    "id": school.id,
                    "name": school.name,
                    "region": school.region,
                    "address": school.road_address,
                }
                for school in schools
            ]
        }
    )


def render_profile(
    request: HttpRequest,
    profile_user: User,
    *,
    is_mypage: bool,
    form: ProfileForm | None = None,
) -> HttpResponse:
    profile, _ = Profile.objects.get_or_create(user=profile_user)
    posts = profile_user.posts.select_related("school")[:20]
    comments = profile_user.comments.select_related("post", "post__school")[:20]
    guestbook_entries = profile_user.guestbook_entries.select_related("school")[:20]
    recommendations = profile_user.post_recommendations.select_related("post", "post__school")[:20]
    verifications = profile_user.school_verifications.select_related("school", "reviewer")[:10]

    return render(
        request,
        "accounts/profile.html",
        {
            "profile_user": profile_user,
            "profile": profile,
            "is_mypage": is_mypage,
            "form": form,
            "verification_form": SchoolVerificationForm() if is_mypage else None,
            "verifications": verifications,
            "posts": posts,
            "comments": comments,
            "guestbook_entries": guestbook_entries,
            "recommendations": recommendations,
        },
    )
