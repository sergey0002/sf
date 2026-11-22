"""Command packages for the arch CLI.

Each command is a separate class implementing the Command protocol.
This keeps the CLI modular and follows the Open/Closed Principle:
new commands can be added without modifying the dispatcher or parser.
"""
