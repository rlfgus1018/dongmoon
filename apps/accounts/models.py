from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    nickname = models.CharField(max_length=40, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="profiles/%Y/%m/", blank=True)
    verified_school = models.ForeignKey(
        "core.School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_profiles",
    )
    school_verified_at = models.DateTimeField(null=True, blank=True)
    school_verification_type = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name

    @property
    def display_name(self) -> str:
        return self.nickname or self.user.get_full_name() or self.user.username


class SchoolVerification(models.Model):
    class VerificationType(models.TextChoices):
        ENROLLED = "enrolled", "재학생"
        GRADUATED = "graduated", "졸업생"

    class Status(models.TextChoices):
        PENDING = "pending", "검토중"
        APPROVED = "approved", "승인"
        REJECTED = "rejected", "반려"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="school_verifications")
    school = models.ForeignKey(
        "core.School",
        on_delete=models.CASCADE,
        related_name="verification_requests",
    )
    verification_type = models.CharField(max_length=20, choices=VerificationType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    document = models.FileField(upload_to="school_verifications/%Y/%m/")
    note = models.TextField(blank=True)
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_school_verifications",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.TextField(blank=True)
    document_deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["school", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.school.name} ({self.get_status_display()})"

    def sync_profile(self) -> None:
        profile, _ = Profile.objects.get_or_create(user=self.user)
        profile.verified_school = self.school
        profile.school_verified_at = self.reviewed_at
        profile.school_verification_type = self.verification_type
        profile.save(
            update_fields=[
                "verified_school",
                "school_verified_at",
                "school_verification_type",
                "updated_at",
            ]
        )

    def save(self, *args, **kwargs) -> None:
        if self.status in {self.Status.APPROVED, self.Status.REJECTED} and not self.reviewed_at:
            self.reviewed_at = timezone.now()
        super().save(*args, **kwargs)
        if self.status == self.Status.APPROVED:
            self.sync_profile()

    def approve(self, reviewer: User) -> None:
        self.status = self.Status.APPROVED
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.reject_reason = ""
        self.save(
            update_fields=["status", "reviewer", "reviewed_at", "reject_reason", "updated_at"]
        )

    def reject(self, reviewer: User, reason: str = "") -> None:
        self.status = self.Status.REJECTED
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.reject_reason = reason
        self.save(
            update_fields=["status", "reviewer", "reviewed_at", "reject_reason", "updated_at"]
        )
