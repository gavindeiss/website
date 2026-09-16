"""Update generated sections of the website."""

from html import escape
from pathlib import Path
import re
from zipfile import ZipFile
from xml.etree import ElementTree


ROOT = Path(__file__).parent
WRITING_PAGE = ROOT / "writing" / "index.html"
POETRY_ROOT = ROOT / "writing" / "poems"
STORY_ROOT = ROOT / "writing" / "shortStories"
STORY_PAGE_ROOT = STORY_ROOT / "pages"
DOCX_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

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
			output.extend([
				'                <article class="writing-entry">',
				'                    <p class="entry-label">Untitled</p>',
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


def story_parts(path):
	if path.suffix.lower() == ".docx":
		return docx_parts(path)

	lines = path.read_text(encoding="utf-8").splitlines()
	if not lines:
		raise ValueError(f"Story file is empty: {path}")

	title = lines[0].strip()
	body = "\n".join(lines[1:]).lstrip("\n")
	return title, body, f'<pre class="story-text">{escape(body)}</pre>'


def docx_parts(path):
	w_namespace = DOCX_NAMESPACE["w"]
	left_attribute = "{" + w_namespace + "}left"
	first_line_attribute = "{" + w_namespace + "}firstLine"

	with ZipFile(path) as archive:
		document = ElementTree.fromstring(archive.read("word/document.xml"))

	paragraphs = document.findall(".//w:body/w:p", DOCX_NAMESPACE)
	if not paragraphs:
		raise ValueError(f"DOCX file has no paragraphs: {path}")

	paragraph_data = []
	for paragraph in paragraphs:
		paragraph_text = []
		paragraph_html = []
		for run in paragraph.findall("w:r", DOCX_NAMESPACE):
			properties = run.find("w:rPr", DOCX_NAMESPACE)
			plain_content = []
			content = []
			for child in run:
				if child.tag == f'{{{DOCX_NAMESPACE["w"]}}}t':
					text = child.text or ""
					plain_content.append(text)
					content.append(escape(text))
				elif child.tag == f'{{{DOCX_NAMESPACE["w"]}}}tab':
					plain_content.append("\t")
					content.append("\t")
				elif child.tag == f'{{{DOCX_NAMESPACE["w"]}}}br':
					plain_content.append("\n")
					content.append("\n")

			run_html = "".join(content)
			if properties is not None:
				if properties.find("w:b", DOCX_NAMESPACE) is not None:
					run_html = f"<strong>{run_html}</strong>"
				if properties.find("w:i", DOCX_NAMESPACE) is not None:
					run_html = f"<em>{run_html}</em>"
				if properties.find("w:u", DOCX_NAMESPACE) is not None:
					run_html = f"<u>{run_html}</u>"

			paragraph_text.append("".join(plain_content))
			paragraph_html.append(run_html)

		text = "".join(paragraph_text)
		paragraph_properties = paragraph.find("w:pPr", DOCX_NAMESPACE)
		style = []
		if paragraph_properties is not None:
			indent = paragraph_properties.find("w:ind", DOCX_NAMESPACE)
			if indent is not None:
				left = indent.get(left_attribute)
				first_line = indent.get(first_line_attribute)
				if left:
					style.append(f"margin-left: {int(left) / 15:g}px")
				if first_line:
					style.append(f"text-indent: {int(first_line) / 15:g}px")
		paragraph_data.append((text, "".join(paragraph_html), "; ".join(style)))

	title = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", path.stem)
	title = re.sub(r"[_-]+", " ", title).strip().title()
	body_parts = paragraph_data
	body = "\n".join(text for text, _, _ in body_parts)
	body_html_parts = []
	for _, html, style in body_parts:
		style_attribute = f' style="{style}"' if style else ""
		body_html_parts.append(f'<p{style_attribute}>{html or "<br>"}</p>')
	body_html = "\n".join(body_html_parts)
	return title, body, f'<div class="story-text">{body_html}</div>'


def story_slug(path):
	return re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")


def story_excerpt(text, limit=280):
	clean_text = re.sub(r"\s+", " ", text).strip()
	if len(clean_text) <= limit:
		return clean_text
	return clean_text[:limit].rsplit(" ", 1)[0] + "..."


def build_story_page(title, body_html):
	return f'''<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>{escape(title)} | Writing</title>

	<link rel="stylesheet" href="../../writing.css">
</head>

<body>

<header>
    <div class="page-heading">
        <h1>{escape(title)}</h1>
		<a class="support-link" href="../../../support/">Support</a>
    </div>

    <nav>
		<a href="../../../landing/">Formal Announcements Page</a>
    </nav>

    <hr>

    <nav>
		<a href="../../../">Home</a>
        |
		<a href="../../">Back to Writing</a>
    </nav>

    <hr>
</header>

<main>
    <article class="story-page">
        <p class="entry-label">Short Story</p>
		{body_html}
    </article>
</main>

</body>
</html>
'''


def build_story_markup():
	stories = sorted(STORY_ROOT.glob("**/*"), key=lambda path: (sort_key(path.parent), sort_key(path)))
	stories = [
		story for story in stories
		if story.is_file() and story.suffix.lower() in {".txt", ".docx"} and story.stat().st_size
	]
	if not stories:
		return '''        <article class="writing-entry">
            <p class="entry-label">Coming soon</p>
            <h3>A place for short stories</h3>
            <p>
                This is where short stories can live. Replace this
                placeholder with a story, title, and any details you want to
                share.
            </p>
        </article>'''

	STORY_PAGE_ROOT.mkdir(exist_ok=True)
	output = []
	for story in stories:
		title, body, body_html = story_parts(story)
		slug = story_slug(story)
		if story.parent != STORY_ROOT:
			slug = f"{story.parent.name}-{slug}"
		(STORY_PAGE_ROOT / f"{slug}.html").write_text(
			build_story_page(title, body_html), encoding="utf-8"
		)
		output.extend([
			'        <article class="writing-entry story-preview">',
			f'            <p class="entry-label">Short Story</p>',
			f'            <h3>{escape(title)}</h3>',
			f'            <p>{escape(story_excerpt(body))}</p>',
			f'            <a class="story-link" href="shortStories/pages/{slug}.html">Read the whole story</a>',
			'        </article>',
		])

	return "\n\n".join(output)


def update_writing_page():
	page = WRITING_PAGE.read_text(encoding="utf-8")
	sections = (
		(r"(?s)(        <!-- POETRY_ENTRIES_START -->\n).*?(\n        <!-- POETRY_ENTRIES_END -->)", build_poetry_markup(), "poetry"),
		(r"(?s)(        <!-- STORY_ENTRIES_START -->\n).*?(\n        <!-- STORY_ENTRIES_END -->)", build_story_markup(), "story"),
	)
	updated_page = page
	for pattern, markup, section_name in sections:
		updated_page, replacements = re.subn(pattern, rf"\1{markup}\2", updated_page, count=1)
		if replacements != 1:
			raise RuntimeError(f"Could not find the generated {section_name} section in writing/index.html")

	WRITING_PAGE.write_text(updated_page, encoding="utf-8")


if __name__ == "__main__":
	update_writing_page()
