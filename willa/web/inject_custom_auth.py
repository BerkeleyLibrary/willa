"""
Inject the CalNet CAS OIDC provider into Chainlit.
"""

from chainlit.oauth_providers import providers, OAuthProvider


def provider_id_in_instance_list(provider_id: str) -> bool:
    """Determine if the given provider is present in the Chainlit providers list.

    :param str provider_id: The provider ID (short name) to search for.
    :returns bool: Whether the given provider ID is present.
    """
    if providers is None:
        return False

    return any(provider.id == provider_id for provider in providers)


def add_custom_oauth_provider(provider_id: str, provider_instance: OAuthProvider) -> None:
    """Add a custom OAuth provider to Chainlit.

    :param str provider_id: The provider ID (short name) of the provider.
    :param OAuthProvider provider_instance: An instance of the provider.
                                            The provider must subclass OAuthProvider.
    """
    if not provider_id_in_instance_list(provider_id):
        providers.append(provider_instance)
