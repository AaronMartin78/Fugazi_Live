#!/usr/bin/env python3
"""Turn scrape_fugazi.py's show JSON into a lightweight node/edge graph."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def slugify(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[^\w]+", "-", value, flags=re.UNICODE).strip("-")
    return value or "unknown"


def load_shows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON array in {path}")
    return payload


def graph_for(shows: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str, int | None]] = set()

    def add_node(node_id: str, kind: str, name: str, **properties: Any) -> None:
        node = {"id": node_id, "type": kind, "name": name}
        node.update({key: value for key, value in properties.items() if value not in (None, "", [])})
        nodes.setdefault(node_id, node)

    def add_edge(source: str, relation: str, target: str, position: int | None = None) -> None:
        key = (source, relation, target, position)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edge: dict[str, Any] = {"source": source, "relation": relation, "target": target}
        if position is not None:
            edge["position"] = position
        edges.append(edge)

    for index, show in enumerate(shows, start=1):
        show_key = show.get("show_id") or show.get("slug") or f"row-{index}"
        show_node_id = f"show:{slugify(str(show_key))}"
        add_node(
            show_node_id,
            "show",
            str(show_key),
            show_id=show.get("show_id"),
            date=show.get("event_date"),
            venue=show.get("venue"),
            city=show.get("city"),
            subdivision=show.get("subdivision"),
            country=show.get("country"),
            source_url=show.get("source_url"),
        )

        if show.get("venue"):
            venue_id = f"venue:{slugify(show['venue'])}"
            add_node(venue_id, "venue", show["venue"])
            add_edge(show_node_id, "played_at", venue_id)

        place_parts = [show.get("city"), show.get("subdivision"), show.get("country")]
        place_name = ", ".join(part for part in place_parts if part)
        if place_name:
            place_id = "place:" + slugify("|".join(str(p) for p in place_parts if p))
            add_node(place_id, "place", place_name, city=show.get("city"), subdivision=show.get("subdivision"), country=show.get("country"))
            add_edge(show_node_id, "happened_in", place_id)

        for act in show.get("opening_acts", []):
            if not act:
                continue
            act_id = f"band:{slugify(act)}"
            add_node(act_id, "band", act)
            add_edge(show_node_id, "opened_by", act_id)

        for track in show.get("setlist", []):
            title = track.get("title")
            if not title:
                continue
            song_id = f"song:{slugify(title)}"
            add_node(song_id, "song", title, title_as_listed=title)
            add_edge(show_node_id, "performed", song_id, track.get("position"))

    return {"nodes": list(nodes.values()), "edges": edges}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="data/fugazi_shows.json", help="Show JSON from scrape_fugazi.py")
    parser.add_argument("--output", default="data/fugazi_graph.json", help="Output graph JSON file")
    args = parser.parse_args()

    graph = graph_for(load_shows(Path(args.input)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(graph['nodes'])} nodes and {len(graph['edges'])} edges to {output}")


if __name__ == "__main__":
    main()
