from unittest.mock import MagicMock
from productboard_sync.productboard.paginator import paginate


def make_response(data, next_url=None):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": data, "links": {"next": next_url}}
    return resp


def test_single_page_yields_all_items():
    request_fn = MagicMock(return_value=make_response([{"id": "1"}, {"id": "2"}]))
    items = list(paginate(request_fn, "GET", "https://api.example.com/items"))
    assert len(items) == 2
    assert request_fn.call_count == 1


def test_multi_page_follows_cursor():
    responses = [
        make_response([{"id": "1"}], next_url="https://api.example.com/items?pageCursor=cursor1"),
        make_response([{"id": "2"}], next_url=None),
    ]
    request_fn = MagicMock(side_effect=responses)
    items = list(paginate(request_fn, "GET", "https://api.example.com/items"))
    assert len(items) == 2
    assert request_fn.call_count == 2
    second_call_params = request_fn.call_args_list[1][0][2]
    assert second_call_params.get("pageCursor") == "cursor1"


def test_empty_first_page_yields_nothing():
    request_fn = MagicMock(return_value=make_response([], next_url=None))
    items = list(paginate(request_fn, "GET", "https://api.example.com/items"))
    assert items == []


def test_post_sends_cursor_as_query_param_not_body():
    responses = [
        make_response([{"id": "1"}], next_url="https://api.example.com/search?pageCursor=abc"),
        make_response([{"id": "2"}], next_url=None),
    ]
    request_fn = MagicMock(side_effect=responses)
    body = {"data": {"filter": {"type": ["feature"]}}}
    items = list(paginate(request_fn, "POST", "https://api.example.com/search", json_body=body))
    assert len(items) == 2
    _, second_url, second_params, second_body = request_fn.call_args_list[1][0]
    assert second_url == "https://api.example.com/search"
    assert second_params.get("pageCursor") == "abc"
    assert second_body == body
