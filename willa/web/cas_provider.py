"""
Provides a Chainlit authentication provider for CAS.
"""

from typing import Any, Optional, Tuple, Dict

import httpx
from chainlit.oauth_providers import OAuthProvider
from chainlit.server import app
from chainlit.user import User
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse

from willa.config import CONFIG


if CONFIG['CALNET_ENV'] == 'test':
    BASE_URL = "https://auth-test.berkeley.edu/cas/oidc"
    """The base URL for the test instance of CalNet CAS."""
elif CONFIG['CALNET_ENV'] == 'production':
    BASE_URL = "https://auth.berkeley.edu/cas/oidc"
    """The base URL for the production instance of CalNet CAS."""
else:
    raise ValueError(f"Unknown CalNet environment {CONFIG['CALNET_ENV']}!")


class CASForbiddenException(HTTPException):
    """Exception class for when a CAS-authenticated user is not authorized."""
    def __init__(self, status_code: int, detail: Any = None,
                 headers: Optional[Dict[str, str]] = None) -> None:
        super().__init__(
            status_code=status_code, detail=detail, headers=headers
        )


@app.exception_handler(CASForbiddenException)
async def cas_forbidden_exception_handler(
    _request: Request,
    exc: CASForbiddenException
) -> HTMLResponse:
    """Exception handler to display a custom HTML error message."""
    return HTMLResponse(
        status_code=exc.status_code,
        content=f"""<!DOCTYPE html>
            <html>
            <head><title>Not Authorised</title></head>
            <body>{exc.detail}</body>
            </html>"""
    )


class CASProvider(OAuthProvider):
    """Connects Chainlit Auth to CalNet OIDC."""
    id = "cas"
    env = ['CALNET_OIDC_CLIENT_ID', 'CALNET_OIDC_CLIENT_SECRET']

    authorize_url = f"{BASE_URL}/oidcAuthorize"
    token_url = f"{BASE_URL}/oidcAccessToken"
    well_known_url = f"{BASE_URL}/.well-known"

    def __init__(self) -> None:
        self.client_id = CONFIG['CALNET_OIDC_CLIENT_ID']
        self.client_secret = CONFIG['CALNET_OIDC_CLIENT_SECRET']
        self.authorize_params = {
            'response_type': 'code',
            'scope': 'openid profile berkeley_edu_groups',
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

            groups = user_data['attributes'].get('groups', [])
            if 'cn=edu:berkeley:app:auth-cas:lib-willa:lib-willa-allow,' \
               'ou=campus groups,dc=berkeley,dc=edu' not in groups:
                raise CASForbiddenException(
                    status_code=403,
                    detail="""
                    <h1>Not Authorised</h1>
                    <p>You are not allowed to access Willa.</p>
                    """
                )

            user = User(identifier=user_data['id'])
            return user_data, user
