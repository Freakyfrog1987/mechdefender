import io
import unittest
from urllib.parse import urlencode

from app import SESSIONS, application


class TestRoutes(unittest.TestCase):
    def setUp(self):
        SESSIONS.clear()

    def _call(self, method, path, body="", cookie=""):
        status_holder = {}

        def start_response(status, headers):
            status_holder["status"] = status
            status_holder["headers"] = headers

        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "CONTENT_LENGTH": str(len(body.encode("utf-8"))),
            "wsgi.input": io.BytesIO(body.encode("utf-8")),
            "HTTP_COOKIE": cookie,
        }
        payload = b"".join(application(environ, start_response)).decode("utf-8")
        return status_holder["status"], dict(status_holder["headers"]), payload

    def test_root_renders_login_page(self):
        status, _, body = self._call("GET", "/")
        self.assertTrue(status.startswith("200"))
        self.assertIn("<h1>Login</h1>", body)

    def test_unauthenticated_users_cannot_access_game_routes(self):
        for route in ("/game", "/hangar", "/lobby"):
            status, headers, _ = self._call("GET", route)
            self.assertTrue(status.startswith("302"))
            self.assertEqual(headers["Location"], "/")

    def test_successful_login_redirects_to_game(self):
        body = urlencode({"username": "pilot", "password": "secret"})
        status, headers, _ = self._call("POST", "/login", body=body)
        self.assertTrue(status.startswith("302"))
        self.assertEqual(headers["Location"], "/game")
        self.assertIn("Set-Cookie", headers)

    def test_logout_redirects_home_and_revokes_access(self):
        body = urlencode({"username": "pilot", "password": "secret"})
        _, headers, _ = self._call("POST", "/login", body=body)
        cookie = headers["Set-Cookie"].split(";", 1)[0]

        status, headers, _ = self._call("POST", "/logout", cookie=cookie)
        self.assertTrue(status.startswith("302"))
        self.assertEqual(headers["Location"], "/")

        status, headers, _ = self._call("GET", "/game", cookie=cookie)
        self.assertTrue(status.startswith("302"))
        self.assertEqual(headers["Location"], "/")

    def test_expired_session_redirects_home(self):
        body = urlencode({"username": "pilot", "password": "secret"})
        _, headers, _ = self._call("POST", "/login", body=body)
        cookie = headers["Set-Cookie"].split(";", 1)[0]

        status, headers, _ = self._call("GET", "/session/expire", cookie=cookie)
        self.assertTrue(status.startswith("302"))
        self.assertEqual(headers["Location"], "/")

        status, headers, _ = self._call("GET", "/lobby", cookie=cookie)
        self.assertTrue(status.startswith("302"))
        self.assertEqual(headers["Location"], "/")


if __name__ == "__main__":
    unittest.main()
