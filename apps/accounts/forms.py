from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Profile, SchoolVerification


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="아이디",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autofocus": True,
                "placeholder": "아이디",
            }
        ),
    )
    password = forms.CharField(
        label="비밀번호",
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "비밀번호",
            }
        ),
    )


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label="이메일",
        required=False,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
        labels = {
            "username": "아이디",
        }
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "autocomplete": "username",
                    "placeholder": "아이디",
                }
            ),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = "8자 이상으로 입력하세요."
        self.fields["password2"].help_text = "같은 비밀번호를 한 번 더 입력하세요."


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["nickname", "bio", "avatar"]
        labels = {
            "nickname": "닉네임",
            "bio": "소개",
            "avatar": "프로필 이미지",
        }
        widgets = {
            "nickname": forms.TextInput(attrs={"placeholder": "닉네임"}),
            "bio": forms.Textarea(attrs={"rows": 4, "placeholder": "간단한 소개를 입력하세요."}),
        }


class SchoolVerificationForm(forms.ModelForm):
    privacy_confirmed = forms.BooleanField(
        label="주민등록번호 뒷자리, 주소 등 불필요한 민감정보를 가렸습니다.",
        required=True,
    )

    class Meta:
        model = SchoolVerification
        fields = ["school", "verification_type", "document", "note"]
        labels = {
            "school": "학교",
            "verification_type": "인증 유형",
            "document": "증명서 파일",
            "note": "관리자에게 남길 말",
        }
        widgets = {
            "school": forms.HiddenInput(),
            "note": forms.Textarea(attrs={"rows": 3, "placeholder": "선택 입력"}),
        }

    def clean_document(self):
        document = self.cleaned_data["document"]
        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
        suffix = document.name.lower().rsplit(".", 1)
        extension = f".{suffix[-1]}" if len(suffix) == 2 else ""
        if extension not in allowed_extensions:
            raise ValidationError("PDF, JPG, PNG 파일만 업로드할 수 있습니다.")
        if document.size > 5 * 1024 * 1024:
            raise ValidationError("파일은 5MB 이하로 업로드하세요.")
        return document
