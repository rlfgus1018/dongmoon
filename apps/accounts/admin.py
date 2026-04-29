from django.contrib import admin

from .models import Profile, SchoolVerification


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "nickname", "verified_school", "school_verified_at"]
    search_fields = ["user__username", "nickname", "verified_school__name"]
    autocomplete_fields = ["user", "verified_school"]


@admin.register(SchoolVerification)
class SchoolVerificationAdmin(admin.ModelAdmin):
    list_display = ["user", "school", "verification_type", "status", "created_at", "reviewer"]
    list_filter = ["status", "verification_type", "created_at"]
    search_fields = ["user__username", "school__name", "note", "reject_reason"]
    autocomplete_fields = ["user", "school", "reviewer"]
    readonly_fields = ["created_at", "updated_at", "reviewed_at", "document_deleted_at"]
    actions = ["approve_requests", "reject_requests"]

    def save_model(self, request, obj, form, change):
        if obj.status in {obj.Status.APPROVED, obj.Status.REJECTED} and not obj.reviewer:
            obj.reviewer = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="선택한 학교 인증 승인")
    def approve_requests(self, request, queryset):
        for verification in queryset:
            verification.approve(request.user)

    @admin.action(description="선택한 학교 인증 반려")
    def reject_requests(self, request, queryset):
        for verification in queryset:
            verification.reject(request.user, "관리자 반려")
