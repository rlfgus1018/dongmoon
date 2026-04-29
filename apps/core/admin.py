from django.contrib import admin
from django.utils import timezone

from .models import (
    Comment,
    CommentReport,
    FamousAlumni,
    FamousAlumniCandidate,
    GuestbookEntry,
    Post,
    PostRecommendation,
    PostReport,
    School,
    SchoolFavorite,
    SchoolModerator,
)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ["name", "region", "establishment", "school_type", "is_closed"]
    list_filter = ["establishment", "school_type", "gender_type", "is_closed", "is_paused"]
    search_fields = ["name", "code", "region", "road_address"]


@admin.register(SchoolModerator)
class SchoolModeratorAdmin(admin.ModelAdmin):
    list_display = ["school", "user", "is_active", "created_at"]
    list_filter = ["is_active", "school"]
    search_fields = ["school__name", "user__username"]
    autocomplete_fields = ["school", "user"]


@admin.register(SchoolFavorite)
class SchoolFavoriteAdmin(admin.ModelAdmin):
    list_display = ["school", "user", "created_at"]
    search_fields = ["school__name", "user__username"]
    autocomplete_fields = ["school", "user"]


@admin.register(FamousAlumni)
class FamousAlumniAdmin(admin.ModelAdmin):
    list_display = ["name", "school", "description", "is_visible", "verified_at"]
    list_filter = ["is_visible", "source_name", "verified_at"]
    search_fields = ["name", "description", "school__name", "source_url"]
    autocomplete_fields = ["school", "verified_by"]


@admin.register(FamousAlumniCandidate)
class FamousAlumniCandidateAdmin(admin.ModelAdmin):
    list_display = ["name", "school", "source_name", "status", "created_at", "reviewed_by"]
    list_filter = ["status", "source_name", "created_at"]
    search_fields = ["name", "description", "school__name", "source_url", "raw_text"]
    autocomplete_fields = ["school", "reviewed_by", "approved_alumni"]
    actions = ["approve_candidates", "reject_candidates"]

    @admin.action(description="선택한 유명 동문 후보 승인")
    def approve_candidates(self, request, queryset):
        for candidate in queryset.select_related("school"):
            alumni = FamousAlumni.objects.create(
                school=candidate.school,
                name=candidate.name,
                description=candidate.description,
                source_name=candidate.source_name,
                source_url=candidate.source_url,
                verified_by=request.user,
                verified_at=timezone.now(),
                is_visible=True,
            )
            candidate.status = candidate.Status.APPROVED
            candidate.reviewed_by = request.user
            candidate.reviewed_at = timezone.now()
            candidate.approved_alumni = alumni
            candidate.save(
                update_fields=[
                    "status",
                    "reviewed_by",
                    "reviewed_at",
                    "approved_alumni",
                    "updated_at",
                ]
            )

    @admin.action(description="선택한 유명 동문 후보 반려")
    def reject_candidates(self, request, queryset):
        queryset.update(
            status=FamousAlumniCandidate.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            reject_reason="관리자 반려",
        )


@admin.register(GuestbookEntry)
class GuestbookEntryAdmin(admin.ModelAdmin):
    list_display = ["school", "author", "created_at"]
    search_fields = ["school__name", "author__username", "body"]
    autocomplete_fields = ["school", "author"]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "school", "author", "board_type", "is_hidden", "created_at"]
    list_filter = ["board_type", "is_hidden", "created_at"]
    search_fields = ["title", "body", "school__name", "author__username"]
    autocomplete_fields = ["school", "author"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["post", "author", "is_hidden", "created_at"]
    list_filter = ["is_hidden", "created_at"]
    search_fields = ["post__title", "author__username", "body"]
    autocomplete_fields = ["post", "author"]


@admin.register(PostRecommendation)
class PostRecommendationAdmin(admin.ModelAdmin):
    list_display = ["post", "user", "created_at"]
    autocomplete_fields = ["post", "user"]


@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = ["post", "reporter", "reason", "status", "created_at"]
    list_filter = ["reason", "status", "created_at"]
    search_fields = ["post__title", "reporter__username", "detail"]
    autocomplete_fields = ["post", "reporter", "handled_by"]


@admin.register(CommentReport)
class CommentReportAdmin(admin.ModelAdmin):
    list_display = ["comment", "reporter", "reason", "status", "created_at"]
    list_filter = ["reason", "status", "created_at"]
    search_fields = ["comment__body", "reporter__username", "detail"]
    autocomplete_fields = ["comment", "reporter", "handled_by"]
