from libertyscope.explorer import LibertyExplorer
import re


_NUM_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def clean_str(value):
    if value is None:
        return None

    text = str(value).strip()

    if len(text) >= 2 and text[0] == text[-1] and text[0] in ["'", '"']:
        text = text[1:-1]

    return text


def to_float(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = clean_str(value)

    try:
        return float(text)
    except ValueError:
        return None


def numbers_from_text(text):
    return [float(x) for x in _NUM_RE.findall(str(text))]


def to_float_list(value):
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            out.extend(to_float_list(item))
        return out

    return numbers_from_text(clean_str(value))


def to_float_matrix(value):
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        return [to_float_list(row) for row in value]

    text = str(value)

    rows = re.findall(r'"([^"]*)"', text)

    if len(rows) > 1:
        return [numbers_from_text(row) for row in rows]

    return [numbers_from_text(text)]