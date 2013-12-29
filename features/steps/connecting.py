import logging, subprocess, re, sys, signal, os
from behave import given, when, then, step

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

        port = int(m.groups()[0])
        logging.debug("started an nrepl on port {0} with pid {1}".format(port, lein_process.pid))
        return (lein_process, port)
    except TypeError: ## happens when the readline doesn't work
        destroy_repl((lein_process, -1))
        raise

def destroy_repl(repl):
    logging.debug("Terminating lein on port {0}".format(repl[1]))
    os.killpg(repl[0].pid, signal.SIGTERM) 
    repl[0].wait()

@given('a headless nrepl has been started on localhost')
def step_impl(context):
    pass
    
@when('a connection is created')
def step_impl(context):
    assert False

@then('a replmanager is returned')
def step_impl(context):
    assert False

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    repl = create_headless_repl()
    destroy_repl(repl)