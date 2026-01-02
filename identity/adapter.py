from allauth.account.adapter import DefaultAccountAdapter


class IdentityAdapter(DefaultAccountAdapter):
    """
    Custom account adapter for the Trainer model.
    """

    def is_open_for_signup(self, request):
        """
        Checks whether or not the site is open for signups.
        """
        return False
