#!/usr/bin/env python3
"""Validate the structural contract for a source-grounded system-design HTML artifact."""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

REQUIRED_SECTION_TOKENS = [
    "high-level requirements", "constraints", "api", "data model", "reliability", "performance",
]


class SvgInfo:
    """Per-<svg> structural facts accumulated while inside that element."""

    def __init__(self, key: str, has_viewbox: bool) -> None:
        self.key = key
        self.has_viewbox = has_viewbox
        self.title_count = 0
        self.desc_count = 0
        self.text_count = 0


class IdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.svg_count = 0
        self.legend_count = 0
        self.source_notes_count = 0
        self.external_assets: list[str] = []
        self.svgs: list[SvgInfo] = []
        # Stack of SvgInfo for the currently-open svg elements (supports nesting).
        self._svg_stack: list[SvgInfo] = []

    def handle_starttag(self, tag: str, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "svg":
            self.svg_count += 1
            svg_id = attrs.get("id")
            key = f"#{svg_id}" if svg_id else f"(index {self.svg_count - 1})"
            info = SvgInfo(key=key, has_viewbox="viewbox" in {k.lower() for k in attrs})
            self.svgs.append(info)
            self._svg_stack.append(info)
        elif self._svg_stack:
            current = self._svg_stack[-1]
            if tag == "title":
                current.title_count += 1
            elif tag == "desc":
                current.desc_count += 1
            elif tag == "text":
                current.text_count += 1
        classes = attrs.get("class", "").split()
        if "legend" in classes:
            self.legend_count += 1
        if "source-notes" in classes:
            self.source_notes_count += 1
        for key in ("src", "href"):
            value = attrs.get(key, "")
            if value.startswith(("http://", "https://", "//")):
                self.external_assets.append(f"{tag}[{key}]={value}")

    def handle_endtag(self, tag: str):
        if tag == "svg" and self._svg_stack:
            self._svg_stack.pop()


def fail(errors: list[str]) -> int:
    print("VALIDATION FAILED")
    for error in errors:
        print(f"- {error}")
    return 1


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_system_design_html.py path/to/system-design.html")
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"ERROR: file not found: {path}")
        return 2

    text = path.read_text(encoding="utf-8", errors="ignore")
    parser = IdCollector()
    parser.feed(text)
    errors: list[str] = []

    if not re.search(r'<script\s+id=["\']system-design-manifest["\']\s+type=["\']application/json["\']', text):
        errors.append("missing embedded <script id=\"system-design-manifest\" type=\"application/json\">")
    match = re.search(r'<script\s+id=["\']system-design-manifest["\'][^>]*>(.*?)</script>', text, flags=re.S | re.I)
    manifest = None
    if match:
        try:
            manifest = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            errors.append(f"manifest is not valid JSON: {exc}")

    lower = re.sub(r"\s+", " ", text.lower())
    for token in REQUIRED_SECTION_TOKENS:
        if token not in lower:
            errors.append(f"missing required section or label containing: {token!r}")

    if parser.external_assets:
        errors.append("document uses external assets: " + "; ".join(parser.external_assets))
    if parser.svg_count == 0:
        errors.append("no inline SVG diagram found")
    if parser.legend_count < parser.svg_count:
        errors.append(f"each SVG needs a visible adjacent/contained legend: {parser.svg_count} SVG(s), {parser.legend_count} legend element(s)")

    for svg in parser.svgs:
        if not svg.has_viewbox:
            errors.append(f"svg {svg.key}: missing viewBox attribute")
        if svg.title_count == 0:
            errors.append(f"svg {svg.key}: missing <title>")
        if svg.desc_count == 0:
            errors.append(f"svg {svg.key}: missing <desc>")
        if svg.text_count == 0:
            errors.append(f"svg {svg.key}: missing <text> (labels must be selectable text, not paths/raster)")

    if "traceability" not in lower:
        errors.append("missing traceability appendix (no 'traceability' token found)")
    if parser.source_notes_count == 0:
        errors.append("missing per-section provenance: no element with class \"source-notes\" found")

    if manifest is not None:
        if manifest.get("format") != "system-design-html-svg/v2":
            errors.append("manifest format must be system-design-html-svg/v2")
        diagrams = manifest.get("diagrams")
        if not isinstance(diagrams, list) or not diagrams:
            errors.append("manifest must contain a non-empty diagrams list")
        else:
            seen_nodes: set[str] = set()
            seen_edges: set[str] = set()
            for diagram in diagrams:
                did = diagram.get("id", "<missing>")
                svg_id = diagram.get("svgId")
                if not svg_id or svg_id not in parser.ids:
                    errors.append(f"diagram {did}: svgId does not resolve to an HTML/SVG id")
                if not diagram.get("question"):
                    errors.append(f"diagram {did}: missing question")
                if not diagram.get("sourceRefs"):
                    errors.append(f"diagram {did}: missing sourceRefs")
                if not diagram.get("legend"):
                    errors.append(f"diagram {did}: missing legend metadata")
                node_ids: set[str] = set()
                for node in diagram.get("nodes", []):
                    nid = node.get("id", "<missing>")
                    if nid in seen_nodes:
                        errors.append(f"duplicate node id across manifest: {nid}")
                    seen_nodes.add(nid)
                    node_ids.add(nid)
                    if node.get("svgId") not in parser.ids:
                        errors.append(f"node {nid}: svgId does not resolve")
                    if not node.get("sourceRefs"):
                        errors.append(f"node {nid}: missing sourceRefs")
                for edge in diagram.get("edges", []):
                    eid = edge.get("id", "<missing>")
                    if eid in seen_edges:
                        errors.append(f"duplicate edge id across manifest: {eid}")
                    seen_edges.add(eid)
                    if edge.get("svgId") not in parser.ids:
                        errors.append(f"edge {eid}: svgId does not resolve")
                    if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
                        errors.append(f"edge {eid}: from/to must reference nodes in the same diagram")
                    if not edge.get("label"):
                        errors.append(f"edge {eid}: missing visible label")
                    if not edge.get("sourceRefs"):
                        errors.append(f"edge {eid}: missing sourceRefs")

    if errors:
        return fail(errors)
    print(f"VALIDATION PASSED: {path}")
    print(
        f"Inline SVG diagrams: {parser.svg_count}; visible legends: {parser.legend_count}; "
        f"source-notes blocks: {parser.source_notes_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
