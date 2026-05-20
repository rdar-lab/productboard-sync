import pytest
from unittest.mock import MagicMock, patch, call
from productboard_sync.utils.retry import retry_on_rate_limit


def make_response(status_code, retry_after=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {}
    if retry_after is not None:
        resp.headers["Retry-After"] = str(retry_after)
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_success_on_first_call_no_sleep():
    mock_fn = MagicMock(return_value=make_response(200))
    decorated = retry_on_rate_limit()(mock_fn)
    with patch("time.sleep") as mock_sleep:
        result = decorated()
    assert result.status_code == 200
    mock_sleep.assert_not_called()


def test_retries_on_429_then_succeeds():
    responses = [make_response(429), make_response(429), make_response(200)]
    mock_fn = MagicMock(side_effect=responses)
    decorated = retry_on_rate_limit()(mock_fn)
    with patch("time.sleep") as mock_sleep:
        result = decorated()
    assert result.status_code == 200
    assert mock_fn.call_count == 3
    mock_sleep.assert_has_calls([call(1), call(2)])


def test_raises_after_max_retries():
    mock_fn = MagicMock(return_value=make_response(429))
    decorated = retry_on_rate_limit(max_retries=3)(mock_fn)
    with patch("time.sleep"):
        with pytest.raises(RuntimeError, match="Rate limit retries exhausted"):
            decorated()
    assert mock_fn.call_count == 3


def test_non_429_error_raises_immediately():
    mock_fn = MagicMock(return_value=make_response(500))
    decorated = retry_on_rate_limit()(mock_fn)
    with patch("time.sleep") as mock_sleep:
        with pytest.raises(Exception):
            decorated()
    assert mock_fn.call_count == 1
    mock_sleep.assert_not_called()


def test_no_sleep_on_last_attempt():
    mock_fn = MagicMock(return_value=make_response(429))
    decorated = retry_on_rate_limit(max_retries=2)(mock_fn)
    with patch("time.sleep") as mock_sleep:
        with pytest.raises(RuntimeError):
            decorated()
    assert mock_fn.call_count == 2
    mock_sleep.assert_called_once()  # only the first attempt sleeps


def test_retry_after_header_used_for_wait():
    responses = [make_response(429, retry_after=30), make_response(200)]
    mock_fn = MagicMock(side_effect=responses)
    decorated = retry_on_rate_limit()(mock_fn)
    with patch("time.sleep") as mock_sleep:
        decorated()
    mock_sleep.assert_called_once_with(30)
