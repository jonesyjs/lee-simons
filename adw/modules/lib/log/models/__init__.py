"""models — the data model and state holders of the logging subsystem.

The "what" of logging (data + state), separate from the behaviour files
(logger, layouts, filters, sinks, appenders):

- events.py  — the event data model (LogEvent + Operational/Audit + enums).
- context.py — the run's correlation ids + stage (contextvars).
- schema.py  — the upcaster registry for schema evolution.
"""
