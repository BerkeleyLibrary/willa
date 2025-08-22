"""
Provides a Chainlit authentication provider for CAS.
"""

import os
from typing import Tuple, Dict

import httpx
from chainlit.oauth_providers import OAuthProvider
from chainlit.user import User
import willa.config  # pylint: disable=W0611

CALNET_ENV: str = os.environ.get('CALNET_ENV', 'test')
"""The environment we are running in; either 'test' or 'production'."""


if CALNET_ENV == 'test':
    BASE_URL = "https://auth-test.berkeley.edu/cas/oidc"
    """The base URL for the test instance of CalNet CAS."""
elif CALNET_ENV == 'production':
    BASE_URL = "https://auth.berkeley.edu/cas/oidc"
    """The base URL for the production instance of CalNet CAS."""
else:
    raise ValueError(f'Unknown CalNet environment {CALNET_ENV}!')


class CASProvider(OAuthProvider):
    """Connects Chainlit Auth to CalNet OIDC."""
    id = "cas"
    env = ['CALNET_OIDC_CLIENT_ID', 'CALNET_OIDC_CLIENT_SECRET']

    authorize_url = f"{BASE_URL}/oidcAuthorize"
    token_url = f"{BASE_URL}/oidcAccessToken"
    well_known_url = f"{BASE_URL}/.well-known"

    def __init__(self) -> None:
        self.client_id = os.environ['CALNET_OIDC_CLIENT_ID']
        self.client_secret = os.environ['CALNET_OIDC_CLIENT_SECRET']
        self.authorize_params = {
            'response_type': 'code',
            'scope': 'openid profile',
        }

    async def get_token(self, code: str, url: str) -> str:
        request = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': url,
            'scope': self.authorize_params['scope']
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=request)
            response.raise_for_status()
            data = response.json()

            token: str = data['access_token']
            if not token:
                raise httpx.HTTPStatusError('Failed to obtain access token',
                                            request=response.request, response=response)

            return token

    async def get_user_info(self, token: str) -> Tuple[Dict[str, str], User]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/oidcProfile",
                                        headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
            user_data = response.json()

            # Future TODO: Find out where groups are returned, and check them. (AP-397)

            user = User(identifier=user_data['id'])
            return user_data, user
