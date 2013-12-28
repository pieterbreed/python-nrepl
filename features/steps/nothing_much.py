import logging
from behave import given, when, then, step


@given('Nothing much')
def step_impl(context):
    logging.debug("given")

@when('I don\'t really do anything')
def step_impl(context):
    logging.debug("when")

@then('Nothing much will happen')
def step_impl(context):
    logging.debug("then")
