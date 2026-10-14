from book_converter.text import markdown_to_text, sanitize_book_name


def test_markdown_to_text_strips_image_embeds():
    assert markdown_to_text("Hello ![fig](images/fig.png) world") == "Hello  world"
    assert markdown_to_text("no images") == "no images"


def test_sanitize_book_name():
    assert sanitize_book_name("My Book.djvu") == "My_Book"
    assert sanitize_book_name("a/b\\c.djvu") == "a_b_c"
    assert sanitize_book_name("___.djvu") == "book"
    assert sanitize_book_name("plain.djvu") == "plain"
