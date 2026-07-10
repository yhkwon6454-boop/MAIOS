from __future__ import annotations

from pathlib import Path


class OntologyAdapter:
    """Query expansion backed by an RDFS/OWL ontology (Turtle file).

    Builds a label neighborhood index from the ontology: for every labeled
    term, its subclass parents and children, its instances and classes, and
    every class connected through an object property's domain/range. A query
    mentioning a known label expands to its neighbors, so recall and research
    can match documents that share no surface tokens with the query.

    Follows the fallback principle: with no file, an unparsable file, or
    rdflib missing, the adapter reports unavailable and expands to nothing.
    """

    def __init__(self, path: str | Path | None = None, max_terms: int = 12) -> None:
        self.path = Path(path).expanduser() if path else None
        self.max_terms = max(1, max_terms)
        self._neighbors: dict[str, set[str]] = {}
        self._normalized_labels: dict[str, str] = {}
        self.error: str | None = None
        if self.path is not None:
            self._load()

    @property
    def available(self) -> bool:
        return bool(self._normalized_labels)

    def labels(self) -> tuple[str, ...]:
        return tuple(sorted(self._normalized_labels.values()))

    def related(self, label: str) -> tuple[str, ...]:
        return tuple(sorted(self._neighbors.get(label, ())))

    def mentions(self, text: str) -> tuple[str, ...]:
        """Ontology labels that appear in the text (space-insensitive)."""
        if not self._normalized_labels:
            return ()
        compact = "".join(text.split()).lower()
        return tuple(
            sorted(
                label
                for normalized, label in self._normalized_labels.items()
                if normalized in compact
            )
        )

    def neighborhood(self, label: str) -> frozenset[str]:
        """A label plus everything directly related to it."""
        return frozenset({label} | self._neighbors.get(label, set()))

    def expand_query(self, text: str) -> tuple[str, ...]:
        """Labels related to any ontology term mentioned in the text."""
        if not self._normalized_labels:
            return ()
        compact = "".join(text.split()).lower()
        expansions: set[str] = set()
        for normalized, label in self._normalized_labels.items():
            if normalized in compact:
                expansions.update(self._neighbors.get(label, ()))
                expansions.add(label)
        mentioned = {
            label for normalized, label in self._normalized_labels.items() if normalized in compact
        }
        ordered = sorted(expansions - mentioned)
        return tuple(ordered[: self.max_terms])

    def _load(self) -> None:
        if self.path is None or not self.path.exists():
            self.error = f"ontology file not found: {self.path}"
            return
        try:
            from rdflib import RDF, RDFS, Graph
        except ImportError:
            self.error = "rdflib is not installed (pip install rdflib)"
            return
        try:
            graph = Graph()
            graph.parse(self.path, format="turtle")
        except Exception as error:
            self.error = f"failed to parse ontology: {error}"
            return

        labels: dict[object, str] = {}
        for subject, _, label in graph.triples((None, RDFS.label, None)):
            labels.setdefault(subject, str(label))

        def link(a: object, b: object) -> None:
            label_a, label_b = labels.get(a), labels.get(b)
            if label_a and label_b and label_a != label_b:
                self._neighbors.setdefault(label_a, set()).add(label_b)
                self._neighbors.setdefault(label_b, set()).add(label_a)

        for subject, _, target in graph.triples((None, RDFS.subClassOf, None)):
            link(subject, target)
        for subject, _, target in graph.triples((None, RDF.type, None)):
            link(subject, target)
        for prop, _, domain in graph.triples((None, RDFS.domain, None)):
            for _, _, range_ in graph.triples((prop, RDFS.range, None)):
                link(domain, range_)
                link(prop, domain)
                link(prop, range_)
        for subject, prop, target in graph:
            if subject in labels and target in labels and prop in labels:
                link(subject, target)

        self._normalized_labels = {
            "".join(label.split()).lower(): label for label in labels.values()
        }
