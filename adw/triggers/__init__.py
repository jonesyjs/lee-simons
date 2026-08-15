"""triggers — entry points that turn GitHub issues into pipeline runs.

Two front-ends over the shared core (modules.trigger): a cron poller and a
webhook server. Both call trigger.handle_issue; neither duplicates its logic.
"""
