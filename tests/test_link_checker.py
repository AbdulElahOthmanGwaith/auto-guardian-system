import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "link-checker.py"
spec = importlib.util.spec_from_file_location("link_checker", SCRIPT)
link_checker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(link_checker)


class LinkCheckerSecurityTests(unittest.TestCase):
    def test_private_and_non_http_urls_are_rejected(self):
        self.assertFalse(link_checker._is_public_http_url("http://127.0.0.1:8080"))
        self.assertFalse(link_checker._is_public_http_url("http://169.254.169.254/latest/meta-data"))
        self.assertFalse(link_checker._is_public_http_url("file:///etc/passwd"))
        self.assertFalse(link_checker._is_public_http_url("https://user:pass@example.com"))

    @patch.object(link_checker.socket, "getaddrinfo", return_value=[(None, None, 0, "", ("93.184.216.34", 443))])
    def test_public_url_can_be_checked_without_following_redirects(self, _getaddrinfo):
        response = Mock(status_code=204, headers={})
        with patch.object(link_checker.requests, "head", return_value=response) as head:
            self.assertTrue(link_checker.check_link("https://example.com/docs"))
            head.assert_called_once_with("https://example.com/docs", timeout=5, allow_redirects=False)

    def test_redirect_to_private_address_is_blocked(self):
        response = Mock(status_code=302, headers={"Location": "http://127.0.0.1:8080/admin"})

        def fake_getaddrinfo(hostname, port, type):
            address = "127.0.0.1" if hostname == "127.0.0.1" else "93.184.216.34"
            return [(None, None, 0, "", (address, port or 443))]

        with patch.object(link_checker.socket, "getaddrinfo", side_effect=fake_getaddrinfo):
            with patch.object(link_checker.requests, "head", return_value=response) as head:
                self.assertFalse(link_checker.check_link("https://example.com/redirect"))
                head.assert_called_once()

    def test_link_extraction_remains_http_only(self):
        text = "See https://example.com and http://localhost:8000, not file:///tmp/x."
        self.assertEqual(
            link_checker.find_links(text),
            ["https://example.com", "http://localhost:8000"],
        )


if __name__ == "__main__":
    unittest.main()
