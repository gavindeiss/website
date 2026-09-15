"""Update generated sections of the website."""

from html import escape
from pathlib import Path
import re


ROOT = Path(__file__).parent
WRITING_PAGE = ROOT / "writing" / "index.html"
POETRY_ROOT = ROOT / "writing" / "poems"

POETRY_CATEGORIES = (
	("haikusAndTanka", "haiku-tanka", "Haiku &amp; Tanka"),
	("freeForm", "free-form", "Free-form"),
)


def sort_key(path):
	"""Sort numbered poem files and year folders numerically when possible."""
	value = path.stem if path.is_file() else path.name
	return (0, int(value)) if value.isdigit() else (1, value.lower())


def format_poem(text):
	"""Escape poem text without changing its whitespace or line breaks."""
	return escape(text)


def build_poetry_view(folder_name, view_id, heading):
	category_root = POETRY_ROOT / folder_name
	years = sorted((path for path in category_root.iterdir() if path.is_dir()), key=sort_key)
	output = [
		f'        <div class="poetry-view{" is-visible" if view_id == "haiku-tanka" else ""}" id="{view_id}"{" hidden" if view_id != "haiku-tanka" else ""}>',
		f"            <h3>{heading}</h3>",
	]

	for year in years:
		poems = sorted(year.glob("*.txt"), key=sort_key)
		if not poems:
			continue

		year_id = f"{view_id}-{year.name}"
		output.extend([
			f'            <section class="poetry-year" aria-labelledby="{year_id}">',
			f'                <h4 id="{year_id}">{escape(year.name)}</h4>',
		])

		for poem in poems:
			poem_number = escape(poem.stem)
			output.extend([
				'                <article class="writing-entry">',
				f'                    <p class="entry-label">Poem {poem_number}</p>',
				'                    <h4>Untitled</h4>',
				f'                    <pre class="poem-text">{format_poem(poem.read_text(encoding="utf-8"))}</pre>',
				'                </article>',
			])

		output.extend([
			"            </section>",
		])

	output.append("        </div>")
	return "\n".join(output)


def build_poetry_markup():
	return "\n\n".join(
		build_poetry_view(folder_name, view_id, heading)
		for folder_name, view_id, heading in POETRY_CATEGORIES
	)


def update_writing_page():
	page = WRITING_PAGE.read_text(encoding="utf-8")
	pattern = r"(?s)(        <!-- POETRY_ENTRIES_START -->\n).*?(\n        <!-- POETRY_ENTRIES_END -->)"
	replacement = rf"\1{build_poetry_markup()}\2"
	updated_page, replacements = re.subn(pattern, replacement, page, count=1)

	if replacements != 1:
		raise RuntimeError("Could not find the generated poetry section in writing/index.html")

	WRITING_PAGE.write_text(updated_page, encoding="utf-8")


if __name__ == "__main__":
	update_writing_page()
