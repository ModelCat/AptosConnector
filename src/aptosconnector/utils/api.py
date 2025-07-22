import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Optional
from dataclasses import dataclass

APTOS_URL = "http://localhost:1234"


@dataclass
class APIConfig:
    """Configuration for the API client"""
    base_url: str
    oauth_token: Optional[str] = None
    timeout: int = 120
    max_retries: int = 3
    backoff_factor: float = 0.5
    retry_status_codes: tuple = (500, 502, 503, 504)


class APIError(Exception):
    """Base exception for API-related errors"""
    pass


class BaseAPIClient:
    """Base class for API clients with common functionality"""

    def __init__(self, config: APIConfig):
        self.config = config
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create and configure a requests session with retry logic"""
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=list(self.config.retry_status_codes)
        )

        session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_headers(self, additional_headers: Optional[Dict] = None) -> Dict:
        """Generate headers for the request"""
        headers = {
            'Content-Type': 'application/json'
        }

        # Add OAuth token if available
        if self.config.oauth_token:
            headers['Authorization'] = f"Bearer {self.config.oauth_token}"

        if additional_headers:
            headers.update(additional_headers)

        return headers

    def _make_request(
            self,
            method: str,
            endpoint: str,
            data: Optional[Dict] = None,
            params: Optional[Dict] = None,
            headers: Optional[Dict] = None
    ) -> Dict:
        """
        Make an HTTP request with error handling

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            headers: Additional headers

        Returns:
            Dict: Response data

        Raises:
            APIError: If the request fails or returns an error
        """
        try:
            url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            response = self._session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=self._get_headers(headers),
                timeout=self.config.timeout
            )

            response.raise_for_status()
            result = response.json()

            # Handle API-specific success/error format
            if isinstance(result, dict) and not result.get('success', True):
                error_msg = '; '.join(result.get('errors', ['Unknown error']))
                raise APIError(f"API returned error: {error_msg}")

            return result

        except requests.exceptions.JSONDecodeError as e:
            raise APIError(f"Failed to parse API response: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")

    def __del__(self):
        """Cleanup method to ensure session is closed"""
        if hasattr(self, '_session'):
            self._session.close()


class AwsAccessClient(BaseAPIClient):
    """Client for storage token related API endpoints"""

    def get_aws_access(self, group_id: str) -> Dict:
        """
        Get storage token for a specific group

        Args:
            group_id: The group ID to generate token for

        Returns:
            Dict containing token data:
                - group_id
                - access_key_id
                - secret_access_key
                - expiration_date
        """
        result = self._make_request(
            method='POST',
            endpoint='/api/storage/token/generate',
            data={'groupId': group_id}
        )

        if not result.get('data'):
            raise APIError("No data returned from API")

        required_fields = {'group_id', 'access_key_id', 'secret_access_key', 'expiration_date'}
        if not all(field in result['data'] for field in required_fields):
            raise APIError("Missing required fields in API response")

        return result['data']
