from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile

from .models import (
    Comment,
    CommentReport,
    FamousAlumni,
    GuestbookEntry,
    Post,
    PostRecommendation,
    PostReport,
    School,
    SchoolFavorite,
    SchoolModerator,
)


class CoreViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(username="schoolmate", password="StrongPass123!")
        School.objects.create(
            code="S000000001",
            name="동문고등학교",
            region="서울특별시 강남구",
            establishment="사립",
            school_type="일반고등학교",
            road_address="서울특별시 강남구 테스트로 1",
            phone="02-0000-0000",
            homepage_url="https://example.com",
            gender_type="남녀공학",
        )

    def test_home_page_loads(self) -> None:
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dongmoon")

    def test_school_search_finds_school_by_name(self) -> None:
        response = self.client.get(reverse("core:school_search"), {"q": "동문"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "동문고등학교")

    def test_search_page_shows_verified_and_favorite_schools(self) -> None:
        school = School.objects.get(code="S000000001")
        Profile.objects.create(user=self.user, verified_school=school)
        SchoolFavorite.objects.create(user=self.user, school=school)
        self.client.login(username="schoolmate", password="StrongPass123!")

        response = self.client.get(reverse("core:school_search"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "내 인증 학교")
        self.assertContains(response, "즐겨찾기 학교")

    def test_user_can_toggle_school_favorite(self) -> None:
        self.client.login(username="schoolmate", password="StrongPass123!")

        self.client.post(reverse("core:toggle_school_favorite", args=["S000000001"]))

        self.assertTrue(
            SchoolFavorite.objects.filter(user=self.user, school__code="S000000001").exists()
        )

        self.client.post(reverse("core:toggle_school_favorite", args=["S000000001"]))

        self.assertFalse(
            SchoolFavorite.objects.filter(user=self.user, school__code="S000000001").exists()
        )

    def test_school_detail_loads(self) -> None:
        response = self.client.get(reverse("core:school_detail", args=["S000000001"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "기본정보")

    def test_alumni_tab_shows_verified_profiles(self) -> None:
        school = School.objects.get(code="S000000001")
        Profile.objects.create(
            user=self.user,
            nickname="동문닉",
            verified_school=school,
            school_verification_type="graduated",
        )

        response = self.client.get(
            reverse("core:school_detail", args=["S000000001"]),
            {"tab": "alumni"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "동문닉")
        self.assertContains(response, "졸업생")

    def test_alumni_tab_shows_visible_famous_alumni(self) -> None:
        school = School.objects.get(code="S000000001")
        FamousAlumni.objects.create(
            school=school,
            name="유명한 동문",
            description="가수",
            source_name="관리자 검수",
            source_url="https://example.com/source",
        )
        FamousAlumni.objects.create(
            school=school,
            name="숨김 동문",
            is_visible=False,
        )

        response = self.client.get(
            reverse("core:school_detail", args=["S000000001"]),
            {"tab": "alumni"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "유명한 동문")
        self.assertContains(response, "가수")
        self.assertNotContains(response, "숨김 동문")

    def test_guestbook_entry_can_be_created_by_logged_in_user(self) -> None:
        self.client.login(username="schoolmate", password="StrongPass123!")

        response = self.client.post(
            reverse("core:create_guestbook_entry", args=["S000000001"]),
            {"body": "반갑습니다."},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(GuestbookEntry.objects.filter(body="반갑습니다.").exists())

    def test_guestbook_entry_is_limited_to_once_per_day_per_user(self) -> None:
        self.client.login(username="schoolmate", password="StrongPass123!")

        self.client.post(
            reverse("core:create_guestbook_entry", args=["S000000001"]),
            {"body": "첫 번째 방명록"},
        )
        self.client.post(
            reverse("core:create_guestbook_entry", args=["S000000001"]),
            {"body": "두 번째 방명록"},
        )

        self.assertEqual(GuestbookEntry.objects.filter(author=self.user).count(), 1)
        self.assertFalse(GuestbookEntry.objects.filter(body="두 번째 방명록").exists())

    def test_post_comment_and_recommendation_flow(self) -> None:
        self.client.login(username="schoolmate", password="StrongPass123!")
        image = SimpleUploadedFile(
            "photo.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00\xff\xff\xff,\x00\x00"
            b"\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )

        create_response = self.client.post(
            reverse("core:create_post", args=["S000000001"]),
            {
                "title": "첫 글",
                "body": "학교 게시판 첫 글입니다.",
                "image": image,
            },
        )
        post = Post.objects.get(title="첫 글")

        self.assertRedirects(
            create_response,
            reverse("core:post_detail", args=["S000000001", post.id]),
            fetch_redirect_response=False,
        )

        self.client.post(
            reverse("core:create_comment", args=["S000000001", post.id]),
            {"body": "첫 댓글입니다."},
        )
        self.client.post(reverse("core:recommend_post", args=["S000000001", post.id]))

        self.assertTrue(post.image)
        self.assertTrue(Comment.objects.filter(post=post, body="첫 댓글입니다.").exists())
        self.assertTrue(PostRecommendation.objects.filter(post=post, user=self.user).exists())

    def test_author_can_delete_comment(self) -> None:
        self.client.login(username="schoolmate", password="StrongPass123!")
        school = School.objects.get(code="S000000001")
        post = Post.objects.create(
            school=school,
            author=self.user,
            title="삭제 테스트",
            body="본문",
        )
        comment = Comment.objects.create(post=post, author=self.user, body="삭제할 댓글")

        response = self.client.post(
            reverse("core:delete_comment", args=["S000000001", post.id, comment.id]),
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())

    def test_author_can_delete_post(self) -> None:
        self.client.login(username="schoolmate", password="StrongPass123!")
        school = School.objects.get(code="S000000001")
        post = Post.objects.create(
            school=school,
            author=self.user,
            title="삭제할 글",
            body="본문",
        )

        response = self.client.post(
            reverse("core:delete_post", args=["S000000001", post.id]),
        )

        self.assertRedirects(
            response,
            reverse("core:school_detail", args=["S000000001"]) + "?tab=community&section=board",
            fetch_redirect_response=False,
        )
        self.assertFalse(Post.objects.filter(id=post.id).exists())

    def test_unverified_user_cannot_read_verified_post(self) -> None:
        school = School.objects.get(code="S000000001")
        post = Post.objects.create(
            school=school,
            author=self.user,
            board_type=Post.BoardType.VERIFIED,
            title="인증 글",
            body="인증 사용자만 볼 수 있습니다.",
        )

        response = self.client.get(reverse("core:post_detail", args=["S000000001", post.id]))

        self.assertEqual(response.status_code, 403)

    def test_verified_user_can_create_verified_post(self) -> None:
        school = School.objects.get(code="S000000001")
        Profile.objects.create(user=self.user, verified_school=school)
        self.client.login(username="schoolmate", password="StrongPass123!")

        response = self.client.post(
            reverse("core:create_post", args=["S000000001"]),
            {
                "board_type": Post.BoardType.VERIFIED,
                "title": "인증 게시판 글",
                "body": "학교 인증을 받은 사용자만 작성합니다.",
            },
        )

        post = Post.objects.get(title="인증 게시판 글")
        self.assertRedirects(
            response,
            reverse("core:post_detail", args=["S000000001", post.id]),
            fetch_redirect_response=False,
        )
        self.assertEqual(post.board_type, Post.BoardType.VERIFIED)

    def test_unverified_user_cannot_create_verified_post(self) -> None:
        self.client.login(username="schoolmate", password="StrongPass123!")

        response = self.client.post(
            reverse("core:create_post", args=["S000000001"]),
            {
                "board_type": Post.BoardType.VERIFIED,
                "title": "막혀야 하는 글",
                "body": "본문",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Post.objects.filter(title="막혀야 하는 글").exists())

    def test_user_can_report_post_and_comment(self) -> None:
        reporter = User.objects.create_user(username="reporter", password="StrongPass123!")
        school = School.objects.get(code="S000000001")
        post = Post.objects.create(school=school, author=self.user, title="신고 대상", body="본문")
        comment = Comment.objects.create(post=post, author=self.user, body="댓글")
        self.client.login(username="reporter", password="StrongPass123!")

        self.client.post(
            reverse("core:report_post", args=["S000000001", post.id]),
            {"reason": "spam", "detail": "광고입니다."},
        )
        self.client.post(
            reverse("core:report_comment", args=["S000000001", post.id, comment.id]),
            {"reason": "abuse", "detail": "비방입니다."},
        )

        self.assertTrue(PostReport.objects.filter(post=post, reporter=reporter).exists())
        self.assertTrue(CommentReport.objects.filter(comment=comment, reporter=reporter).exists())

    def test_school_moderator_can_hide_post(self) -> None:
        school = School.objects.get(code="S000000001")
        post = Post.objects.create(school=school, author=self.user, title="숨김 대상", body="본문")
        SchoolModerator.objects.create(school=school, user=self.user)
        self.client.login(username="schoolmate", password="StrongPass123!")

        response = self.client.post(
            reverse("core:moderate_post", args=["S000000001", post.id, "hide"])
        )
        post.refresh_from_db()

        self.assertRedirects(response, reverse("core:moderation_dashboard", args=["S000000001"]))
        self.assertTrue(post.is_hidden)
        self.assertEqual(post.hidden_by, self.user)

    def test_non_moderator_cannot_access_moderation_dashboard(self) -> None:
        self.client.login(username="schoolmate", password="StrongPass123!")

        response = self.client.get(reverse("core:moderation_dashboard", args=["S000000001"]))

        self.assertEqual(response.status_code, 403)

    def test_health_check(self) -> None:
        response = self.client.get(reverse("core:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
