from jinja2 import Environment, FileSystemLoader, StrictUndefined, Template

from transcription_bot.utils.config import TEMPLATES_FOLDER

_TEMPLATE_SUFFIX = "j2x"
template_env = Environment(
    block_start_string="((*",
    block_end_string="*))",
    variable_start_string="(((",
    variable_end_string=")))",
    comment_start_string="((#",
    comment_end_string="#))",
    autoescape=False,  # noqa: S701
    loader=FileSystemLoader(TEMPLATES_FOLDER),
    undefined=StrictUndefined,
)


def get_template(name: str) -> Template:
    """Get a Jinja2 template."""
    return template_env.get_template(f"{name}.{_TEMPLATE_SUFFIX}")
