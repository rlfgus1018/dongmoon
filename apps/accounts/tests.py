from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile, SchoolVerification
from apps.core.models import Comment, GuestbookEntry, Post, School


class AccountViewTests(TestCase):
    def test_signup_creates_and_logs_in_user(self) -> None:
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "schoolmate",
                "email": "schoolmate@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            follow=True,
        )

        self.assertTrue(User.objects.filter(username="schoolmate").exists())
        self.assertRedirects(response, reverse("core:school_search"))
        self.assertContains(response, "schoolmate")

    def test_login_with_valid_credentials(self) -> None:
        User.objects.create_user(username="schoolmate", password="StrongPass123!")

        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "schoolmate",
                "password": "StrongPass123!",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("core:school_search"))
        self.assertContains(response, "schoolmate")

    def test_logout_requires_post_and_logs_out(self) -> None:
        User.objects.create_user(username="schoolmate", password="StrongPass123!")
        self.client.login(username="schoolmate", password="StrongPass123!")

        response = self.client.post(reverse("accounts:logout"), follow=True)

        self.assertRedirects(response, reverse("core:school_search"))
        self.assertContains(response, "로그인")

    def test_mypage_shows_user_activity(self) -> None:
        user = User.objects.create_user(username="schoolmate", password="StrongPass123!")
        Profile.objects.create(user=user, nickname="동문")
        school = School.objects.create(code="S000000001", name="동문고등학교")
        post = Post.objects.create(school=school, author=user, title="내 글", body="본문")
        Comment.objects.create(post=post, author=user, body="내 댓글")
        GuestbookEntry.objects.create(school=school, author=user, body="내 방명록")
        self.client.login(username="schoolmate", password="StrongPass123!")

        response = self.client.get(reverse("accounts:mypage"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "동문")
        self.assertContains(response, "내 글")
        self.assertContains(response, "내 댓글")
        self.assertContains(response, "내 방명록")

    def test_public_profile_shows_user_activity(self) -> None:
        user = User.objects.create_user(username="schoolmate", password="StrongPass123!")
        school = School.objects.create(code="S000000001", name="동문고등학교")
        Post.objects.create(school=school, author=user, title="공개 글", body="본문")

        response = self.client.get(reverse("accounts:user_profile", args=[user.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "공개 글")

    def test_user_can_request_school_verification(self) -> None:
        user = User.objects.create_user(username="schoolmate", password="StrongPass123!")
        school = School.objects.create(code="S000000001", name="동문고등학교")
        document = SimpleUploadedFile(
            "certificate.pdf",
            b"%PDF-1.4\n%test\n",
            content_type="application/pdf",
        )
        self.client.login(username="schoolmate", password="StrongPass123!")

        response = self.client.post(
            reverse("accounts:request_school_verification"),
            {
                "school": school.id,
                "verification_type": SchoolVerification.VerificationType.GRADUATED,
                "document": document,
                "note": "확인 부탁드립니다.",
                "privacy_confirmed": "on",
            },
        )

        self.assertRedirects(response, reverse("accounts:mypage"))
        verification = SchoolVerification.objects.get(user=user)
        self.assertEqual(verification.school, school)
        self.assertEqual(verification.status, SchoolVerification.Status.PENDING)

    def test_school_search_api_returns_matching_schools(self) -> None:
        User.objects.create_user(username="schoolmate", password="StrongPass123!")
        School.objects.create(code="S000000001", name="동문고등학교", region="서울특별시")
        self.client.login(username="schoolmate", password="StrongPass123!")

        response = self.client.get(reverse("accounts:school_search_api"), {"q": "동문"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["name"], "동문고등학교")

    def test_approving_school_verification_updates_profile(self) -> None:
        user = User.objects.create_user(username="schoolmate", password="StrongPass123!")
        reviewer = User.objects.create_user(username="admin", password="StrongPass123!")
        school = School.objects.create(code="S000000001", name="동문고등학교")
        verification = SchoolVerification.objects.create(
            user=user,
            school=school,
            verification_type=SchoolVerification.VerificationType.GRADUATED,
            document=SimpleUploadedFile(
                "certificate.pdf",
                b"%PDF-1.4\n%test\n",
                content_type="application/pdf",
            ),
        )

        verification.approve(reviewer)

        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.verified_school, school)
        self.assertEqual(profile.school_verification_type, "graduated")

    def test_direct_status_approval_updates_profile(self) -> None:
        user = User.objects.create_user(username="schoolmate", password="StrongPass123!")
        school = School.objects.create(code="S000000001", name="동문고등학교")
        verification = SchoolVerification.objects.create(
            user=user,
            school=school,
            verification_type=SchoolVerification.VerificationType.ENROLLED,
            document=SimpleUploadedFile(
                "certificate.pdf",
                b"%PDF-1.4\n%test\n",
                content_type="application/pdf",
            ),
        )

        verification.status = SchoolVerification.Status.APPROVED
        verification.save()

        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.verified_school, school)
        self.assertEqual(profile.school_verification_type, "enrolled")
        self.assertIsNotNone(profile.school_verified_at)
