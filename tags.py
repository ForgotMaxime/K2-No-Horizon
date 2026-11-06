def parse_tags(text):
    return [tag.strip() for tag in text.split(',') if tag]
