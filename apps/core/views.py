from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import Profile

from .forms import CommentForm, CommentReportForm, GuestbookEntryForm, PostForm, PostReportForm
from .models import (
    Comment,
    CommentReport,
    Post,
    PostRecommendation,
    PostReport,
    ReportStatus,
    School,
    SchoolFavorite,
)

MODERATION_UPDATE_FIELDS = [
    "is_hidden",
    "hidden_by",
    "hidden_at",
    "hidden_reason",
    "updated_at",
]


def user_can_access_verified_board(request: HttpRequest, school: School) -> bool:
    if not request.user.is_authenticated:
        return False
    profile = getattr(request.user, "profile", None)
    return bool(profile and profile.verified_school_id == school.id)


def user_can_moderate_school(request: HttpRequest, school: School) -> bool:
    if not request.user.is_authenticated:
        return False
    if request.user.is_staff:
        return True
    return school.moderators.filter(user=request.user, is_active=True).exists()


def home(request: HttpRequest) -> HttpResponse:
    return school_search(request)


def school_search(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    schools = School.objects.all()
    verified_school = None
    favorite_schools = School.objects.none()
    favorite_school_ids = set()

    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        verified_school = getattr(profile, "verified_school", None)
        favorite_schools = School.objects.filter(favorites__user=request.user).order_by(
            "-favorites__created_at"
        )[:30]
        favorite_school_ids = set(
            SchoolFavorite.objects.filter(user=request.user).values_list("school_id", flat=True)
        )

    if query:
        schools = schools.filter(
            Q(name__icontains=query)
            | Q(region__icontains=query)
            | Q(road_address__icontains=query)
        )

    context = {
        "query": query,
        "schools": schools[:40],
        "total_count": schools.count() if query else School.objects.count(),
        "verified_school": verified_school,
        "favorite_schools": favorite_schools,
        "favorite_school_ids": favorite_school_ids,
    }
    return render(request, "core/school_search.html", context)


def school_detail(request: HttpRequest, code: str) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    active_tab = request.GET.get("tab", "info")
    if active_tab not in {"info", "community", "alumni"}:
        active_tab = "info"
    community_section = request.GET.get("section", "guestbook")
    if community_section not in {"guestbook", "board"}:
        community_section = "guestbook"
    board_type = request.GET.get("board", "all")
    if board_type not in {"all", "general", "verified"}:
        board_type = "all"
    can_access_verified_board = user_can_access_verified_board(request, school)
    is_favorite_school = False
    has_guestbook_entry_today = False
    if request.user.is_authenticated:
        is_favorite_school = SchoolFavorite.objects.filter(
            school=school,
            user=request.user,
        ).exists()
        today = timezone.localdate()
        has_guestbook_entry_today = school.guestbook_entries.filter(
            author=request.user,
            created_at__date=today,
        ).exists()

    posts = (
        school.posts.filter(is_hidden=False)
        .select_related("author")
        .prefetch_related("comments", "recommendations")
    )
    if board_type == "general":
        posts = posts.filter(board_type=Post.BoardType.GENERAL)
    elif board_type == "verified":
        if can_access_verified_board:
            posts = posts.filter(board_type=Post.BoardType.VERIFIED)
        else:
            posts = Post.objects.none()
    elif not can_access_verified_board:
        posts = posts.filter(board_type=Post.BoardType.GENERAL)

    return render(
        request,
        "core/school_detail.html",
        {
            "school": school,
            "active_tab": active_tab,
            "community_section": community_section,
            "board_type": board_type,
            "can_access_verified_board": can_access_verified_board,
            "can_moderate_school": user_can_moderate_school(request, school),
            "is_favorite_school": is_favorite_school,
            "guestbook_entries": school.guestbook_entries.select_related("author")[:20],
            "guestbook_form": GuestbookEntryForm(),
            "has_guestbook_entry_today": has_guestbook_entry_today,
            "posts": posts[:30],
            "post_form": PostForm(),
            "verified_profiles": Profile.objects.filter(verified_school=school)
            .select_related("user")
            .order_by("-school_verified_at", "user__username")[:100],
            "famous_alumni": school.famous_alumni.filter(is_visible=True)[:100],
        },
    )


@login_required
def toggle_school_favorite(request: HttpRequest, code: str) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    if request.method == "POST":
        favorite, created = SchoolFavorite.objects.get_or_create(
            school=school,
            user=request.user,
        )
        if not created:
            favorite.delete()

    next_url = request.POST.get("next") or school.get_absolute_url()
    return redirect(next_url)


@login_required
def create_guestbook_entry(request: HttpRequest, code: str) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    if request.method == "POST":
        today = timezone.localdate()
        already_wrote = school.guestbook_entries.filter(
            author=request.user,
            created_at__date=today,
        ).exists()
        if already_wrote:
            return redirect(f"{school.get_absolute_url()}?tab=community&section=guestbook")

        form = GuestbookEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.school = school
            entry.author = request.user
            entry.save()
    return redirect(f"{school.get_absolute_url()}?tab=community&section=guestbook")


@login_required
def create_post(request: HttpRequest, code: str) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    board_type = request.POST.get("board_type", Post.BoardType.GENERAL)
    if board_type not in {Post.BoardType.GENERAL, Post.BoardType.VERIFIED}:
        board_type = Post.BoardType.GENERAL
    if board_type == Post.BoardType.VERIFIED and not user_can_access_verified_board(
        request, school
    ):
        return HttpResponseForbidden("학교 인증 후 이용할 수 있습니다.")

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.school = school
            post.author = request.user
            post.board_type = board_type
            post.save()
            return redirect("core:post_detail", code=school.code, post_id=post.id)
    return redirect(f"{school.get_absolute_url()}?tab=community&section=board&board={board_type}")


def post_detail(request: HttpRequest, code: str, post_id: int) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    can_moderate_school = user_can_moderate_school(request, school)
    post = get_object_or_404(
        Post.objects.select_related("school", "author").prefetch_related(
            "comments__author", "recommendations"
        ),
        id=post_id,
        school=school,
    )
    if post.is_hidden and not can_moderate_school and request.user != post.author:
        return HttpResponseForbidden("숨김 처리된 글입니다.")
    if post.board_type == Post.BoardType.VERIFIED and not user_can_access_verified_board(
        request, school
    ):
        return HttpResponseForbidden("학교 인증 후 이용할 수 있습니다.")
    has_recommended = False
    if request.user.is_authenticated:
        has_recommended = post.recommendations.filter(user=request.user).exists()

    return render(
        request,
        "core/post_detail.html",
        {
            "school": school,
            "post": post,
            "comment_form": CommentForm(),
            "post_report_form": PostReportForm(),
            "comment_report_form": CommentReportForm(),
            "comments": post.comments.filter(is_hidden=False).select_related("author"),
            "has_recommended": has_recommended,
            "can_moderate_school": can_moderate_school,
        },
    )


@login_required
def create_comment(request: HttpRequest, code: str, post_id: int) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    post = get_object_or_404(Post, id=post_id, school=school)
    if post.board_type == Post.BoardType.VERIFIED and not user_can_access_verified_board(
        request, school
    ):
        return HttpResponseForbidden("학교 인증 후 이용할 수 있습니다.")
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
    return redirect("core:post_detail", code=school.code, post_id=post.id)


@login_required
def delete_post(request: HttpRequest, code: str, post_id: int) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    post = get_object_or_404(Post, id=post_id, school=school, author=request.user)
    if request.method == "POST":
        post.delete()
        return redirect(f"{school.get_absolute_url()}?tab=community&section=board")
    return redirect("core:post_detail", code=school.code, post_id=post.id)


@login_required
def delete_comment(request: HttpRequest, code: str, post_id: int, comment_id: int) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    post = get_object_or_404(Post, id=post_id, school=school)
    comment = get_object_or_404(Comment, id=comment_id, post=post, author=request.user)
    if request.method == "POST":
        comment.delete()
    return redirect("core:post_detail", code=school.code, post_id=post.id)


@login_required
def recommend_post(request: HttpRequest, code: str, post_id: int) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    post = get_object_or_404(Post, id=post_id, school=school)
    if post.board_type == Post.BoardType.VERIFIED and not user_can_access_verified_board(
        request, school
    ):
        return HttpResponseForbidden("학교 인증 후 이용할 수 있습니다.")
    if request.method == "POST":
        PostRecommendation.objects.get_or_create(post=post, user=request.user)
    return redirect("core:post_detail", code=school.code, post_id=post.id)


@login_required
def report_post(request: HttpRequest, code: str, post_id: int) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    post = get_object_or_404(Post, id=post_id, school=school, is_hidden=False)
    if request.method == "POST":
        form = PostReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.post = post
            report.reporter = request.user
            report.save()
    return redirect("core:post_detail", code=school.code, post_id=post.id)


@login_required
def report_comment(request: HttpRequest, code: str, post_id: int, comment_id: int) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    post = get_object_or_404(Post, id=post_id, school=school)
    comment = get_object_or_404(Comment, id=comment_id, post=post, is_hidden=False)
    if request.method == "POST":
        form = CommentReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.comment = comment
            report.reporter = request.user
            report.save()
    return redirect("core:post_detail", code=school.code, post_id=post.id)


@login_required
def moderation_dashboard(request: HttpRequest, code: str) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    if not user_can_moderate_school(request, school):
        return HttpResponseForbidden("학교 커뮤니티 관리자만 이용할 수 있습니다.")

    post_reports = PostReport.objects.filter(post__school=school).select_related(
        "post", "reporter", "handled_by"
    )[:30]
    comment_reports = CommentReport.objects.filter(comment__post__school=school).select_related(
        "comment", "comment__post", "reporter", "handled_by"
    )[:30]
    posts = school.posts.select_related("author")[:30]
    comments = Comment.objects.filter(post__school=school).select_related("post", "author")[:30]

    return render(
        request,
        "core/moderation_dashboard.html",
        {
            "school": school,
            "post_reports": post_reports,
            "comment_reports": comment_reports,
            "posts": posts,
            "comments": comments,
        },
    )


@login_required
def moderate_post(request: HttpRequest, code: str, post_id: int, action: str) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    if not user_can_moderate_school(request, school):
        return HttpResponseForbidden("학교 커뮤니티 관리자만 이용할 수 있습니다.")
    post = get_object_or_404(Post, id=post_id, school=school)
    if request.method == "POST":
        if action == "hide":
            post.is_hidden = True
            post.hidden_by = request.user
            post.hidden_at = timezone.now()
            post.hidden_reason = request.POST.get("reason", "관리자 숨김")
            post.save(update_fields=MODERATION_UPDATE_FIELDS)
            post.reports.update(
                status=ReportStatus.RESOLVED,
                handled_by=request.user,
                handled_at=timezone.now(),
            )
        elif action == "restore":
            post.is_hidden = False
            post.hidden_by = None
            post.hidden_at = None
            post.hidden_reason = ""
            post.save(update_fields=MODERATION_UPDATE_FIELDS)
        elif action == "delete":
            post.delete()
    return redirect("core:moderation_dashboard", code=school.code)


@login_required
def moderate_comment(
    request: HttpRequest,
    code: str,
    post_id: int,
    comment_id: int,
    action: str,
) -> HttpResponse:
    school = get_object_or_404(School, code=code)
    if not user_can_moderate_school(request, school):
        return HttpResponseForbidden("학교 커뮤니티 관리자만 이용할 수 있습니다.")
    post = get_object_or_404(Post, id=post_id, school=school)
    comment = get_object_or_404(Comment, id=comment_id, post=post)
    if request.method == "POST":
        if action == "hide":
            comment.is_hidden = True
            comment.hidden_by = request.user
            comment.hidden_at = timezone.now()
            comment.hidden_reason = request.POST.get("reason", "관리자 숨김")
            comment.save(update_fields=MODERATION_UPDATE_FIELDS)
            comment.reports.update(
                status=ReportStatus.RESOLVED,
                handled_by=request.user,
                handled_at=timezone.now(),
            )
        elif action == "restore":
            comment.is_hidden = False
            comment.hidden_by = None
            comment.hidden_at = None
            comment.hidden_reason = ""
            comment.save(update_fields=MODERATION_UPDATE_FIELDS)
        elif action == "delete":
            comment.delete()
    return redirect("core:moderation_dashboard", code=school.code)


def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})
