import logging
from behave import given, when, then, step


@given('Nothing much')
def step_impl(context):
    logging.warning("given")
    pass

@when('I don\'t really do anything')
def step_impl(context):
    logging.debug("when")
    pass

@then('Nothing much will happen')
def step_impl(context):
    logging.debug("then")
    assert context.failed is False
