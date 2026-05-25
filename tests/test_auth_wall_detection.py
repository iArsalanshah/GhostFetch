import pytest

from src.core.scraper import StealthScraper, ScraperError


def test_linkedin_footer_text_does_not_trigger_auth_required():
    scraper = StealthScraper.__new__(StealthScraper)
    html = """
    <html><body>
      <main><h1>Public profile</h1><p>Some public content.</p></main>
      <footer>Join LinkedIn | Sign in</footer>
    </body></html>
    """
    # Should not raise, because footer text alone is not a strong auth-wall signal.
    scraper._raise_if_auth_wall("https://www.linkedin.com/in/public-user/", html)


def test_linkedin_login_form_triggers_auth_required():
    scraper = StealthScraper.__new__(StealthScraper)
    html = """
    <html><body>
      <form action="/checkpoint/lg/login-submit">
        <input name="session_key" />
        <input name="session_password" type="password" />
      </form>
    </body></html>
    """
    with pytest.raises(ScraperError) as exc:
        scraper._raise_if_auth_wall("https://www.linkedin.com/checkpoint/lg/login", html)
    assert exc.value.error_code == "auth_required"


def test_challenge_signal_triggers_auth_challenge():
    scraper = StealthScraper.__new__(StealthScraper)
    html = "<html><body><h1>Security challenge</h1><p>Enter verification code</p></body></html>"
    with pytest.raises(ScraperError) as exc:
        scraper._raise_if_auth_wall("https://example.com/challenge", html)
    assert exc.value.error_code == "auth_challenge"
