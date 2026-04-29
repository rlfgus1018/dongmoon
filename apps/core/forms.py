from django import forms

from .models import Comment, CommentReport, GuestbookEntry, Post, PostReport


class GuestbookEntryForm(forms.ModelForm):
    class Meta:
        model = GuestbookEntry
        fields = ["body"]
        labels = {"body": "방명록"}
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": 300,
                    "placeholder": "학교 커뮤니티에 짧은 인사를 남겨보세요.",
                }
            )
        }


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "body", "image"]
        labels = {
            "title": "제목",
            "body": "내용",
            "image": "사진",
        }
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "제목"}),
            "body": forms.Textarea(attrs={"rows": 8, "placeholder": "내용을 입력하세요."}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]
        labels = {"body": "댓글"}
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": 500,
                    "placeholder": "댓글을 입력하세요.",
                }
            )
        }


class PostReportForm(forms.ModelForm):
    class Meta:
        model = PostReport
        fields = ["reason", "detail"]
        labels = {
            "reason": "신고 사유",
            "detail": "상세 내용",
        }
        widgets = {
            "detail": forms.Textarea(attrs={"rows": 3, "placeholder": "선택 입력"}),
        }


class CommentReportForm(forms.ModelForm):
    class Meta:
        model = CommentReport
        fields = ["reason", "detail"]
        labels = {
            "reason": "신고 사유",
            "detail": "상세 내용",
        }
        widgets = {
            "detail": forms.Textarea(attrs={"rows": 3, "placeholder": "선택 입력"}),
        }
