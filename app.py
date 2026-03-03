import secrets
from http import cookies
from urllib.parse import parse_qs

SESSIONS = {}
GAME_ROUTES = {"/game", "/hangar", "/lobby"}


def _parse_cookies(environ):
    raw_cookie = environ.get("HTTP_COOKIE", "")
    jar = cookies.SimpleCookie()
    jar.load(raw_cookie)
    return {key: morsel.value for key, morsel in jar.items()}


def _response(start_response, status, body, headers=None):
    headers = headers or []
    headers.append(("Content-Type", "text/html; charset=utf-8"))
    start_response(status, headers)
    return [body.encode("utf-8")]


def _redirect(start_response, location, headers=None):
    headers = headers or []
    headers.append(("Location", location))
    return _response(start_response, "302 Found", "", headers)


def _new_session(username):
    sid = secrets.token_hex(16)
    SESSIONS[sid] = {"authenticated": True, "user": username}
    return sid


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()
    cookie_data = _parse_cookies(environ)
    sid = cookie_data.get("sid")
    session = SESSIONS.get(sid)

    if method == "GET" and path == "/":
        return _response(
            start_response,
            "200 OK",
            """
            <html><body>
                <h1>Login</h1>
                <form method='post' action='/login'>
                    <input name='username' />
                    <input name='password' type='password' />
                    <button type='submit'>Login</button>
                </form>
            </body></html>
            """,
        )

    if method == "POST" and path == "/login":
        size = int(environ.get("CONTENT_LENGTH") or 0)
        raw = environ["wsgi.input"].read(size).decode("utf-8")
        fields = parse_qs(raw)
        username = (fields.get("username") or [""])[0]
        password = (fields.get("password") or [""])[0]

        if not username or not password:
            return _response(start_response, "400 Bad Request", "username and password required")

        sid = _new_session(username)
        headers = [("Set-Cookie", f"sid={sid}; HttpOnly; Path=/")]
        return _redirect(start_response, "/game", headers=headers)

    if method == "POST" and path == "/logout":
        if sid and sid in SESSIONS:
            del SESSIONS[sid]
        headers = [("Set-Cookie", "sid=; Max-Age=0; Path=/")]
        return _redirect(start_response, "/", headers=headers)

    if method == "GET" and path == "/session/expire":
        if sid and sid in SESSIONS:
            del SESSIONS[sid]
        headers = [("Set-Cookie", "sid=; Max-Age=0; Path=/")]
        return _redirect(start_response, "/", headers=headers)

    if method == "GET" and path in GAME_ROUTES:
        if not session or not session.get("authenticated"):
            return _redirect(start_response, "/")
        return _response(start_response, "200 OK", f"{path[1:]} for {session['user']}")

    return _response(start_response, "404 Not Found", "not found")


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    with make_server("0.0.0.0", 3000, application) as server:
        print("Serving on http://0.0.0.0:3000")
        server.serve_forever()
