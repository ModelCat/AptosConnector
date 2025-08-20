import unittest
from unittest.mock import patch, MagicMock, mock_open

from aptosconnector.setup import run_setup, setup_cli


class TestSetup(unittest.TestCase):
    """Test cases for the setup module."""

    @patch('aptosconnector.setup.check_awscli')
    @patch('aptosconnector.setup.input')
    @patch('aptosconnector.setup.getpass')
    @patch('aptosconnector.setup.AptosClient')
    @patch('aptosconnector.setup.run_cli_command')
    @patch('aptosconnector.setup.check_aws_configuration')
    @patch('aptosconnector.utils.aws.check_s3_access')
    @patch('aptosconnector.setup.os.makedirs')
    def test_run_setup_success(
            self, mock_makedirs, mock_check_s3_access, mock_check_aws_config,
            mock_run_cli, mock_aptos_client, mock_getpass, mock_input, mock_check_awscli
    ):
        """Test a successful setup process."""
        # Mock AWS CLI check
        mock_check_awscli.return_value = True

        # Mock user input
        mock_input.return_value = "12345678-1234-1234-1234-123456789012"
        mock_getpass.return_value = "1_1234567890abcdef1234567890abcdef12345678"

        # Mock AptosClient
        mock_client_instance = MagicMock()
        mock_client_instance.get_aws_access.return_value = {
            "access_key_id": "mock_access_key",
            "secret_access_key": "mock_secret_key"
        }
        mock_aptos_client.return_value = mock_client_instance

        # Mock AWS configuration check
        mock_check_aws_config.return_value = True

        # Mock S3 access check
        mock_check_s3_access.return_value = True

        # Run the setup function with mocked open
        with patch('builtins.open', mock_open()) as mock_file:
            run_setup()

        # Verify AWS CLI was checked
        mock_check_awscli.assert_called_once()

        # Verify user input was requested
        mock_input.assert_called_once()
        mock_getpass.assert_called_once()

        # Verify AptosClient was created and used
        mock_aptos_client.assert_called_once()
        mock_client_instance.get_aws_access.assert_called_once_with("12345678-1234-1234-1234-123456789012")

        # Verify AWS CLI commands were run (4 commands)
        self.assertEqual(mock_run_cli.call_count, 4)

        # Verify AWS configuration was checked
        mock_check_aws_config.assert_called_once()

        # Verify S3 access was checked
        mock_check_s3_access.assert_called_once_with("12345678-1234-1234-1234-123456789012", verbose=False)

        # Verify config directory was created
        mock_makedirs.assert_called_once()

        # Verify config file was written
        mock_file.assert_called_once()
        # The write method is called multiple times to write the JSON config file
        self.assertTrue(mock_file().write.called)

    @patch('aptosconnector.setup.check_awscli')
    def test_run_setup_no_aws_cli(self, mock_check_awscli):
        """Test setup process when AWS CLI is not installed."""
        # Mock AWS CLI check to fail
        mock_check_awscli.return_value = False

        # Run the setup function with exit expected
        with self.assertRaises(SystemExit) as cm:
            run_setup()

        # Verify exit code
        self.assertEqual(cm.exception.code, 1)

        # Verify AWS CLI was checked
        mock_check_awscli.assert_called_once()

    @patch('aptosconnector.setup.run_setup')
    def test_setup_cli(self, mock_run_setup):
        """Test the setup_cli function."""
        # Run the CLI function
        setup_cli()

        # Verify run_setup was called with verbose=1
        mock_run_setup.assert_called_once_with(verbose=1)

    @patch('aptosconnector.setup.check_awscli')
    @patch('aptosconnector.setup.input')
    @patch('aptosconnector.setup.getpass')
    @patch('aptosconnector.setup.AptosClient')
    def test_run_setup_api_error(self, mock_aptos_client, mock_getpass, mock_input, mock_check_awscli):
        """Test setup process when API returns an error."""
        # Mock AWS CLI check
        mock_check_awscli.return_value = True

        # Mock user input
        mock_input.return_value = "12345678-1234-1234-1234-123456789012"
        mock_getpass.return_value = "1_1234567890abcdef1234567890abcdef12345678"

        # Mock AptosClient to raise an APIError
        from aptosconnector.utils.api import APIError
        mock_client_instance = MagicMock()
        mock_client_instance.get_aws_access.side_effect = APIError("API Error")
        mock_aptos_client.return_value = mock_client_instance

        # Run the setup function with exit expected
        with self.assertRaises(SystemExit) as cm:
            run_setup()

        # Verify exit code
        self.assertEqual(cm.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
