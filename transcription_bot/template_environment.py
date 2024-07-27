from jinja2 import Environment, FileSystemLoader, StrictUndefined

from transcription_bot.config import TEMPLATES_FOLDER

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
