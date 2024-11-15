from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomUserAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        user.force_password_update = False
        return user
