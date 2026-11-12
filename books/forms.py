"""Forms for account creation and guardian controls."""
from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction

from .models import ParentChildLink

User = get_user_model()

TEXT_INPUT = "form-input"
SELECT_INPUT = "form-select"


def style_fields(form: forms.Form, *, skip: tuple[str, ...] = ()) -> None:
    """Apply consistent CSS classes and accessibility hints to a form."""
    for name, field in form.fields.items():
        if name in skip:
            continue
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "form-checkbox")
        elif isinstance(widget, forms.RadioSelect):
            widget.attrs.setdefault("class", "form-radio")
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            widget.attrs.setdefault("class", SELECT_INPUT)
        else:
            widget.attrs.setdefault("class", TEXT_INPUT)
        if not widget.attrs.get("placeholder") and isinstance(
            widget, (forms.TextInput, forms.EmailInput, forms.PasswordInput)
        ):
            widget.attrs["placeholder"] = field.label or name.replace("_", " ").title()
        widget.attrs.setdefault("autocomplete", "off")


class SignUpForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=User.Role.choices,
        initial=User.Role.CHILD,
        widget=forms.RadioSelect,
        label="I am signing up as a…",
    )
    display_name = forms.CharField(
        max_length=50,
        label="Display name",
        help_text="This is the name shown around WBooks.",
    )
    parent_email = forms.EmailField(
        required=False,
        label="Parent/guardian email (optional)",
        help_text="Young readers can connect to an existing guardian account.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("role", "display_name", "username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["email"].widget = forms.EmailInput()
        self.fields["username"].help_text = "Letters, digits and @/./+/-/_ only."
        self.fields["password1"].help_text = "At least 8 characters, not entirely numeric."
        self.fields["password2"].label = "Confirm password"
        self.fields["email"].label = "Email address"
        style_fields(self, skip=("role",))
        self.fields["role"].widget.attrs["class"] = "role-choice-input"
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"
        self.parent_user = None

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        parent_email = (cleaned.get("parent_email") or "").strip().lower()

        if role == User.Role.PARENT and parent_email:
            self.add_error(
                "parent_email",
                "Guardian accounts do not need a parent email. Leave this blank.",
            )
            return cleaned

        if role == User.Role.CHILD and parent_email:
            try:
                self.parent_user = User.objects.get(
                    email__iexact=parent_email, role=User.Role.PARENT
                )
            except User.DoesNotExist:
                self.add_error(
                    "parent_email",
                    "No guardian account uses this email. Ask them to sign up first, "
                    "or leave the field blank.",
                )
        return cleaned

    @transaction.atomic
    def save(self, commit: bool = True) -> User:
        user = super().save(commit=commit)
        if commit and self.parent_user is not None:
            ParentChildLink.objects.get_or_create(
                parent_profile=self.parent_user.profile, child=user
            )
        return user


class WBooksAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"autofocus": True}),
        label="Username",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        label="Password",
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "That username and password did not match. Please try again.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"


class LinkChildForm(forms.Form):
    child_email = forms.EmailField(
        label="Young reader's email",
        widget=forms.EmailInput(attrs={"placeholder": "reader@example.com"}),
    )

    def __init__(self, *args, parent=None, **kwargs):
        self.parent = parent
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_child_email(self) -> str:
        email = self.cleaned_data["child_email"].strip().lower()
        try:
            child = User.objects.get(email__iexact=email, role=User.Role.CHILD)
        except User.DoesNotExist:
            raise forms.ValidationError(
                "We couldn't find a young reader with that email."
            )
        existing = (
            ParentChildLink.objects.select_related("parent_profile__user")
            .filter(child=child)
            .first()
        )
        if existing:
            if self.parent and existing.parent_profile.user_id == self.parent.pk:
                raise forms.ValidationError(
                    "This reader is already linked to your account."
                )
            raise forms.ValidationError(
                "This reader is already linked to another guardian account."
            )
        self.child = child
        return email
