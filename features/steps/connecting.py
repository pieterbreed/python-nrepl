import logging, subprocess, re, sys, signal, os
from behave import given, when, then, step
from pyjurer.session_container import connect_nrepl, SessionContainer

# these tests might not work on windows
# on mac os x the subprocess starts lein
# which in turn starts the server in a subprocess
# and if you terminate the headless lein
# you also need to terminate the server process
# on unix you can do it with a process group
# (start_new_session=True along with os.killpg(...))
# but I don't know if this will work on windows or
# what the equivalent will be

def create_headless_repl():
    lein_process = subprocess.Popen(
        ['lein', 'repl', ':headless', ':host', 'localhost'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True) # this line might/will fail on windows
    try:
        firstline = lein_process.stdout.readline()
        logging.debug("First output line of lein subprocess: {0}".format(firstline))
        
        if sys.stdout.encoding:
            firstlineTxt = firstline.decode(sys.stdout.encoding)
        else:
            firstlineTxt = firstline.decode('UTF-8')
        
        m = re.search("nREPL server started on port (\d+) on host localhost", firstlineTxt)

        p = int(m.groups()[0])
        logging.debug("started an nrepl on port {0} with pid {1}".format(p, lein_process.pid))
        return {
            'process': lein_process, 
            'port': p,
            'pid': lein_process.pid
        }
    except TypeError: ## happens when the readline doesn't work
        destroy_repl((lein_process, -1))
        raise

def destroy_repl(repl):
    logging.debug("Terminating lein on port {0}".format(repl['port']))
    os.killpg(repl['pid'], signal.SIGTERM) 
    repl['process'].wait()

@given('a headless nrepl has been started on localhost')
def step_impl(context):
    pass

@when('a connection is opened to \'nrepl://localhost:port/\'')
def step_impl(context):
    connection = connect_nrepl('nrepl://{0}:{1}'.format('localhost', context.lein_repl['port']))
    context.connection = connection

@then('a \'{0}\' is returned in \'{1}\'')
def step_impl(context, t, n):
    assert hasattr(context, n)
    assert getattr(context, n).__class__.__name__ == t

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    repl = create_headless_repl()
    destroy_repl(repl)