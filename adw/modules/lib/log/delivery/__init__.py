"""delivery — how a log event reaches a destination.

An Appender is a bundle of (filter, layout, sink); this package holds it and its
three ingredients:

- appenders.py — Appender: filter -> layout -> sink, best-effort.
- filters.py   — predicates that decide whether an appender takes an event.
- layouts.py   — format an event into a string (JSON / human text).
- sinks.py     — write the string to a destination (console / file).
"""
