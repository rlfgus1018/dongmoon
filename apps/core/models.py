from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class School(TimestampedModel):
    code = models.CharField("school code", max_length=20, unique=True)
    name = models.CharField("school name", max_length=120, db_index=True)
    education_office = models.CharField(max_length=80, blank=True)
    support_office = models.CharField(max_length=80, blank=True)
    region = models.CharField(max_length=120, blank=True, db_index=True)
    establishment = models.CharField(max_length=30, blank=True)
    school_type = models.CharField(max_length=80, blank=True)
    day_night = models.CharField(max_length=20, blank=True)
    founded_on = models.DateField(null=True, blank=True)
    anniversary_on = models.DateField(null=True, blank=True)
    lot_address = models.CharField(max_length=255, blank=True)
    road_address = models.CharField(max_length=255, blank=True)
    road_address_detail = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    fax = models.CharField(max_length=30, blank=True)
    homepage_url = models.URLField(max_length=255, blank=True)
    gender_type = models.CharField(max_length=30, blank=True)
    is_closed = models.BooleanField(default=False)
    closed_on = models.DateField(null=True, blank=True)
    is_paused = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name", "region"]),
        ]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("core:school_detail", args=[self.code])


def user_display_name(user: User) -> str:
    profile = getattr(user, "profile", None)
    if profile and profile.nickname:
        return profile.nickname
    return user.get_full_name() or user.username


class GuestbookEntry(TimestampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="guestbook_entries")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="guestbook_entries")
    body = models.CharField(max_length=300)

    class Meta:
        ordering = ["-created_at"]

    @property
    def author_display_name(self) -> str:
        return user_display_name(self.author)

    def __str__(self) -> str:
        return f"{self.school.name} guestbook by {self.author_display_name}"


class SchoolModerator(TimestampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="moderators")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="moderated_schools")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "user"], name="unique_school_moderator"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} moderates {self.school.name}"


class SchoolFavorite(TimestampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="favorites")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="school_favorites")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["school", "user"], name="unique_school_favorite"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} favorites {self.school.name}"


class FamousAlumni(TimestampedModel):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="famous_alumni")
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    source_name = models.CharField(max_length=80, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_famous_alumni",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["school", "is_visible"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.school.name}"


class FamousAlumniCandidate(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "검토중"
        APPROVED = "approved", "승인"
        REJECTED = "rejected", "반려"

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="famous_alumni_candidates",
    )
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    source_name = models.CharField(max_length=80, blank=True)
    source_url = models.URLField(max_length=500)
    raw_text = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_famous_alumni_candidates",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.TextField(blank=True)
    approved_alumni = models.ForeignKey(
        FamousAlumni,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_candidates",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} candidate for {self.school.name}"


class Post(TimestampedModel):
    class BoardType(models.TextChoices):
        GENERAL = "general", "일반"
        VERIFIED = "verified", "인증"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    board_type = models.CharField(
        max_length=20,
        choices=BoardType.choices,
        default=BoardType.GENERAL,
        db_index=True,
    )
    title = models.CharField(max_length=120)
    body = models.TextField()
    image = models.ImageField(upload_to="posts/%Y/%m/", blank=True)
    is_hidden = models.BooleanField(default=False)
    hidden_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hidden_posts",
    )
    hidden_at = models.DateTimeField(null=True, blank=True)
    hidden_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def author_display_name(self) -> str:
        return user_display_name(self.author)

    def __str__(self) -> str:
        return self.title


class Comment(TimestampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    body = models.CharField(max_length=500)
    is_hidden = models.BooleanField(default=False)
    hidden_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hidden_comments",
    )
    hidden_at = models.DateTimeField(null=True, blank=True)
    hidden_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["created_at"]

    @property
    def author_display_name(self) -> str:
        return user_display_name(self.author)

    def __str__(self) -> str:
        return f"Comment by {self.author_display_name}"


class PostRecommendation(TimestampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="recommendations")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_recommendations")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["post", "user"], name="unique_post_recommendation"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} recommends {self.post_id}"


class ReportReason(models.TextChoices):
    SPAM = "spam", "스팸/광고"
    ABUSE = "abuse", "욕설/비방"
    PRIVACY = "privacy", "개인정보 노출"
    ILLEGAL = "illegal", "불법/유해 정보"
    OTHER = "other", "기타"


class ReportStatus(models.TextChoices):
    PENDING = "pending", "검토중"
    RESOLVED = "resolved", "처리완료"
    REJECTED = "rejected", "기각"


class PostReport(TimestampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_reports")
    reason = models.CharField(max_length=20, choices=ReportReason.choices)
    detail = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
    )
    handled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_post_reports",
    )
    handled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Report for post {self.post_id}"


class CommentReport(TimestampedModel):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comment_reports")
    reason = models.CharField(max_length=20, choices=ReportReason.choices)
    detail = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
    )
    handled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_comment_reports",
    )
    handled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Report for comment {self.comment_id}"
