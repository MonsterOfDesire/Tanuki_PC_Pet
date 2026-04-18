def should_request_slide_out(*, is_expanded, contains_dashboard):
    return bool(is_expanded and not contains_dashboard)
