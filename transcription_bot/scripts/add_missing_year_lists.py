import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

from transcription_bot.template_environment import template_env
from transcription_bot.wiki import create_page

EPISODE_NUM_PATTERN = re.compile(r"\* \[\[SGU Episode (\d{1,4})")
DATE_PATTERN = re.compile(r"[A-Z][a-z]{2} \d{1,2} \d{4}")

STATUS_MAP = {
    "incomplete": "incomplete",
    "mag": "proofread",
    "tick": "verified",
    "open": "open",
    "bot": "machine",
    "a": "machine",
}


@dataclass
class EpisodeInfo:
    """Episode info."""

    number: str
    date: str
    status: str


def main():
    """Create a list of the year's episodes based on manual input."""
    for file in Path("input_files").glob("*.txt"):
        year = file.stem
        print(f"Processing {year}")
        input("Press enter to continue...")

        episodes = _get_episode_info(file)

        rendered_page = _render_episodes(episodes, year)
        print(rendered_page)

        input("Press enter to continue...")

        page_title = f"Template:EpisodeList{year}"

        create_page(requests.Session(), page_title, rendered_page, allow_page_editing=False)
        print(f"Page created: https://www.sgutranscripts.org/wiki/{page_title}")


def _render_episodes(episodes: list[EpisodeInfo], year: str) -> str:
    template = template_env.get_template("episode_list_entry.j2x")

    first_ep = min(int(e.number) for e in episodes)
    last_ep = max(int(e.number) for e in episodes)
    episode_range = f"(Episodes {first_ep}-{last_ep})"

    return template.render(episodes=episodes, year=year, episode_range=episode_range)


def _get_episode_info(file: Path) -> list[EpisodeInfo]:
    lines = file.read_text().split("\n")

    episodes: list[EpisodeInfo] = []
    for line in lines:
        if not line:
            continue

        episode_num_match = EPISODE_NUM_PATTERN.match(line)
        if not episode_num_match:
            raise ValueError(f"Episode number not found: {line}")

        episode_number = episode_num_match.group(1)
        assert episode_number.isdecimal(), f"Invalid episode number: {episode_number}"  # noqa: S101

        date_match = DATE_PATTERN.search(line)
        if not date_match:
            raise ValueError(f"Date not found: {line}")

        date_str = date_match.group(0)
        extracted_date = datetime.strptime(date_str, "%b %d %Y")

        assert extracted_date.year == int(file.stem), f"{extracted_date.year=} != {int(file.stem)=}"  # noqa: S101

        episode_date = extracted_date.strftime("%m-%d")

        for k, v in STATUS_MAP.items():
            if k in line.lower():
                episode_status = v
                break
        else:
            raise ValueError(f"Status not found: {line}")

        episodes.append(EpisodeInfo(episode_number, episode_date, episode_status))
    return episodes


if __name__ == "__main__":
    main()
