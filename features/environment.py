import logging, subprocess, inspect
from steps.connecting import create_headless_repl, destroy_repl

def before_all(context):
    context.lein_repl = create_headless_repl()


def after_all(context):
    if hasattr(context, 'lein_repl'):
        destroy_repl(context.lein_repl)

def after_feature(context, feature):
    pass