from datetime import date, timedelta
from pathlib import Path

SWITCH_TEMPLATE = "\n|EEE= {{#switch:{{{2}}}\n\t|episodebox = {{Episode|MMM|DDD|YYYY}} |boxdate = {{month|MMM}} {{date|DDD}} YYYY|download = {{DownloadLink|YYYY-MMM-DDD}} |}}"
START_OF_SWITCH = "{{#switch:{{{1}}}"

END_OF_SWITCH = "|}}"


BOTTOM = """
<noinclude>
=== Description ===
Please use this template in the Episode skeleton in order to streamline the insertion of date-specific information to the headers and to episodes' infoboxes.

If for some reason these dates do not match up with the broadcasted release of their respective episodes, please be careful in how you modify the entries so as not to disrupt past episodes' date format data.

[[Template:800s]] is set up just like this one. Perhaps one day a Template:1000s will be useful to compile.

=== Usage ===
Replace NNN with the specific XXX group episode number.

<pre>
{{XXX|NNN|episodebox}}
{{XXX|NNN|boxdate}}
{{XXX|NNN|download}}
</pre>

[[Category: Maintenance templates]]
[[Category: Templates]]
</noinclude>
"""

FIRST_EPISODE_DATE = date(2005, 5, 4)


def main(group_start: int, first_episode_of_group_date: date) -> None:
    """Create a page for a 100s group of episodes."""
    switch_parts = []
    for ep_num in range(group_start, group_start + 100):
        ep_date = first_episode_of_group_date + timedelta(days=(ep_num - group_start) * 7)
        switch_parts.append(
            SWITCH_TEMPLATE.replace("EEE", str(ep_num))
            .replace("MMM", ep_date.strftime("%m"))
            .replace("DDD", ep_date.strftime("%d"))
            .replace("YYYY", ep_date.strftime("%Y"))
        )

    group_name = f"{group_start}s"
    bottom = BOTTOM.replace("XXX", group_name)

    full_page = f"{START_OF_SWITCH}{''.join(switch_parts)}{END_OF_SWITCH}{bottom}"
    Path(f"{group_name}.txt").write_text(full_page)


if __name__ == "__main__":
    # main(600, date(2017, 1, 17))
    # main(700, date(2018, 12, 8))
    # main(900, date(2022, 10, 8))
    main(1000, date(2024, 9, 7))
