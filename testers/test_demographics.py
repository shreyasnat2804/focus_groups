from src.demographics import tag_post, extract_from_text, age_to_group


def test_age_to_group():
    assert age_to_group(16) is None
    assert age_to_group(20) == "18-24"
    assert age_to_group(30) == "25-34"
    assert age_to_group(45) == "35-54"
    assert age_to_group(60) == "55+"


def test_extract_age_from_text():
    assert extract_from_text("I'm 24 and love tech")["age_group"] == "18-24"
    assert extract_from_text("32 year old here")["age_group"] == "25-34"
    assert extract_from_text("24M looking for advice")["age_group"] == "18-24"


def test_extract_gender_from_text():
    assert extract_from_text("24M here")["gender"] == "M"
    assert extract_from_text("30/F checking in")["gender"] == "F"
    assert extract_from_text("I'm a guy who likes cars")["gender"] == "M"
    assert extract_from_text("as a woman I think")["gender"] == "F"


def test_tag_post_subreddit_mapping():
    tags = tag_post("some random post", "GenZ")
    assert tags["age_group"] == "18-24"
    assert tags["gender"] == "unknown"


def test_tag_post_text_overrides_unknown():
    tags = tag_post("I'm a 24M student", "gadgets")
    assert tags["age_group"] == "18-24"
    assert tags["gender"] == "M"


def test_tag_post_confidence():
    tags = tag_post("just a post", "gadgets")
    assert 0 < tags["confidence"] <= 1.0
