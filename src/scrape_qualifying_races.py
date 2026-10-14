import argparse
import csv
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from project_paths import CACHE_DIR, DERIVED_DATA_DIR

DEFAULT_URL_TEMPLATE = "https://coachcox.co.uk/imstats/im/qualification/{cycle}/races/"
DEFAULT_OUTPUT = DERIVED_DATA_DIR / "coachcox_qualifiers_2017_2026.md"
DEFAULT_CACHE_DIR = CACHE_DIR / "CoachCoxQualificationPages"
USER_AGENT = "Mozilla/5.0 (compatible; qualification-race-data-export/1.0)"


class RaceCardParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.div_depth = 0
        self.card_depth = None
        self.capture_depth = None
        self.capture_field = None
        self.capture_parts = []
        self.slot_count_depth = None
        self.pending_gender = None
        self.card = None
        self.cards = []

    @staticmethod
    def _attributes(attributes):
        return dict(attributes)

    def handle_starttag(self, tag, attributes):
        attrs = self._attributes(attributes)
        classes = set(attrs.get("class", "").split())

        if tag == "div":
            self.div_depth += 1
            if {"ims-infobox-wrap", "ims-infobox-race"}.issubset(classes):
                self.card_depth = self.div_depth
                self.card = {
                    "sort_name": attrs.get("data-sort-name", ""),
                    "sort_date": attrs.get("data-sort-date", ""),
                    "competitors": attrs.get("data-sort-size", ""),
                    "male_qualifiers": None,
                    "female_qualifiers": None,
                    "combined_qualifiers": None,
                }
            elif self.card is not None and "ims-infobox-title" in classes:
                self._start_capture("event_title")
            elif self.card is not None and {"infobody", "date"}.issubset(classes):
                self._start_capture("display_date")
            elif self.card is not None and "slot-count" in classes:
                self.slot_count_depth = self.div_depth
            elif self.slot_count_depth is not None and "ims-male-icon" in classes:
                self.pending_gender = "male"
            elif self.slot_count_depth is not None and "ims-female-icon" in classes:
                self.pending_gender = "female"

        if tag == "a" and self.card is not None:
            href = attrs.get("href", "")
            if re.search(r"/imstats/race/\d+/results/$", href):
                self.card["results_url"] = href
            elif re.search(r"/imstats/race/\d+/slots/$", href):
                self.card["qualification_url"] = href
            elif re.search(r"/imstats/series/\d+/$", href):
                self.card["series_url"] = href

    def _start_capture(self, field):
        self.capture_depth = self.div_depth
        self.capture_field = field
        self.capture_parts = []

    def handle_data(self, data):
        if self.capture_field is not None:
            self.capture_parts.append(data)

        if self.slot_count_depth is not None:
            value = data.strip()
            if value.isdigit():
                if self.pending_gender is None:
                    self.card["combined_qualifiers"] = int(value)
                else:
                    self.card[f"{self.pending_gender}_qualifiers"] = int(value)
                    self.pending_gender = None

    def handle_endtag(self, tag):
        if tag != "div":
            return

        if self.capture_depth == self.div_depth:
            value = " ".join("".join(self.capture_parts).split())
            self.card[self.capture_field] = value
            self.capture_depth = None
            self.capture_field = None
            self.capture_parts = []

        if self.slot_count_depth == self.div_depth:
            self.slot_count_depth = None
            self.pending_gender = None

        if self.card_depth == self.div_depth:
            self.cards.append(self.card)
            self.card = None
            self.card_depth = None

        self.div_depth -= 1


def fetch_html(url, cache_file=None, refresh=False):
    if cache_file is not None and cache_file.exists() and not refresh:
        return cache_file.read_text(encoding="utf-8")

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Referer": "https://coachcox.co.uk/imstats/im/qualification/",
        },
    )
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(html, encoding="utf-8")
    return html


def parse_races(html, source_url, qualification_cycle):
    parser = RaceCardParser()
    parser.feed(html)
    scraped_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []

    for card in parser.cards:
        title_match = re.fullmatch(r"(.+?)\s+(20\d{2})", card["event_title"])
        if not title_match:
            raise ValueError(f"Could not split event year from {card['event_title']!r}")

        qualification_match = re.search(
            r"/imstats/race/(\d+)/slots/$", card.get("qualification_url", "")
        )
        results_match = re.search(
            r"/imstats/race/(\d+)/results/$", card.get("results_url", "")
        )
        series_match = re.search(
            r"/imstats/series/(\d+)/$", card.get("series_url", "")
        )
        race_match = qualification_match or results_match
        race_id = (
            race_match.group(1)
            if race_match
            else f"{qualification_cycle}-{card['sort_name']}"
        )

        race_date = ""
        if re.fullmatch(r"\d{8}", card["sort_date"]):
            try:
                race_date = datetime.strptime(card["sort_date"], "%Y%m%d").date().isoformat()
            except ValueError:
                pass
        if race_date and re.fullmatch(r"\d{1,2} [A-Z][a-z]{2} \d{4}", card["display_date"]):
            display_date = datetime.strptime(card["display_date"], "%d %b %Y").date().isoformat()
            if race_date != display_date:
                raise ValueError(f"Conflicting dates for {card['event_title']}")

        male_qualifiers = card["male_qualifiers"]
        female_qualifiers = card["female_qualifiers"]
        combined_qualifiers = card["combined_qualifiers"]
        if combined_qualifiers is not None:
            total_qualifiers = combined_qualifiers
        elif male_qualifiers is not None or female_qualifiers is not None:
            total_qualifiers = (male_qualifiers or 0) + (female_qualifiers or 0)
        else:
            total_qualifiers = None
        rows.append(
            {
                "qualification_cycle": qualification_cycle,
                "race_id": race_id,
                "race_name": title_match.group(1),
                "event_year": title_match.group(2),
                "event_title": card["event_title"],
                "race_date": race_date,
                "display_date": card["display_date"],
                "male_qualifiers": male_qualifiers,
                "female_qualifiers": female_qualifiers,
                "combined_qualifiers": combined_qualifiers,
                "total_qualifiers": total_qualifiers,
                "competitors": int(card["competitors"]),
                "results_url": card.get("results_url", ""),
                "qualification_url": card.get("qualification_url", ""),
                "series_id": series_match.group(1) if series_match else "",
                "series_url": card.get("series_url", ""),
                "source_url": source_url,
                "scraped_at_utc": scraped_at,
            }
        )

    if len(rows) != len({row["race_id"] for row in rows}):
        raise ValueError("Duplicate race IDs found")
    return rows


def write_csv(rows, output_file):
    if not rows:
        raise ValueError("No race records found")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def markdown_value(value):
    return "—" if value is None or value == "" else str(value)


def write_markdown(rows, output_file, source_urls):
    if not rows:
        raise ValueError("No race records found")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# Coach Cox IRONMAN Qualifiers, 2017-2026",
        "",
        f"Generated: {generated_at}",
        "",
        "Counts are transcribed from each Coach Cox qualification-cycle race page. "
        "`Combined` is populated when the source publishes one unsplit qualifier total; "
        "`Men` and `Women` are populated when the source publishes separate counts. "
        "A blank (`—`) means the source did not publish that field and does not imply zero.",
        "",
    ]

    for cycle in sorted(source_urls, key=int):
        cycle_rows = [row for row in rows if row["qualification_cycle"] == cycle]
        lines.extend(
            [
                f"## {cycle} qualification cycle",
                "",
                f"Source: [{source_urls[cycle]}]({source_urls[cycle]})",
                "",
                "| Date | Race | Men | Women | Combined | Total | Competitors |",
                "|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for row in cycle_rows:
            race_url = row["qualification_url"] or row["results_url"] or row["series_url"]
            race_name = row["event_title"].replace("|", "\\|")
            race_cell = f"[{race_name}]({race_url})" if race_url else race_name
            lines.append(
                "| {date} | {race} | {male} | {female} | {combined} | {total} | {competitors} |".format(
                    date=markdown_value(row["race_date"] or row["display_date"]),
                    race=race_cell,
                    male=markdown_value(row["male_qualifiers"]),
                    female=markdown_value(row["female_qualifiers"]),
                    combined=markdown_value(row["combined_qualifiers"]),
                    total=markdown_value(row["total_qualifiers"]),
                    competitors=markdown_value(row["competitors"]),
                )
            )
        lines.extend(["", f"Records: {len(cycle_rows)}", ""])

    output_file.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export Coach Cox qualifying races to Markdown.")
    parser.add_argument("--start-cycle", type=int, default=2017)
    parser.add_argument("--end-cycle", type=int, default=2026)
    parser.add_argument("--url-template", default=DEFAULT_URL_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    if args.start_cycle > args.end_cycle:
        parser.error("--start-cycle must not exceed --end-cycle")

    rows = []
    source_urls = {}
    for cycle_number in range(args.start_cycle, args.end_cycle + 1):
        cycle = str(cycle_number)
        url = args.url_template.format(cycle=cycle)
        cache_file = args.cache_dir / f"qualification_{cycle}.html"
        cycle_rows = parse_races(
            fetch_html(url, cache_file=cache_file, refresh=args.refresh), url, cycle
        )
        rows.extend(cycle_rows)
        source_urls[cycle] = url
        print(f"Fetched {cycle}: {len(cycle_rows)} races")

    write_markdown(rows, args.output, source_urls)
    print(f"Saved {len(rows)} races to {args.output.resolve()}")


if __name__ == "__main__":
    main()