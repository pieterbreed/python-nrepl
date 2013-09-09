# TODO

## Immediate

 - finish the other session commands: `stdin`, `ls-sessions`, `load-file`, `interrupt`
 - capture any output from any command via an overload or callback. figure out how
   the end of a response is indicated and handle that properly.p6

## Next milestone: nrepl-cli

**To create an `nrepl` client in python that does not rely on too many external libraries (or none at all if I can get away with it)**

 - Create a 'top-level' class with which to interact with the nrepl session
 - Have a reasonable source folder structure

**done**

 - nice consistent callback api. All operations invoked on the session take both the 'value' (if appropriate) and a callback function with which the result or value of that
 operation will be invoked. The callback accepts both the sending session (object) and
 the primary value of that operation (a data structure of some kind as appropriate)
 - these sessions commands are done:

      - `eval`
      - `describe`
      - `close`


## Feature list
 - Implement the suggestions on [this page](http://infinitemonkeycorps.net/docs/pph/)