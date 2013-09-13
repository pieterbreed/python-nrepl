# TODO

## Immediate

 - 

## Next milestone: nrepl-cli

**To create an `nrepl` client in python that does not rely on too many external libraries (or none at all if I can get away with it)**

 - Create a 'top-level' class with which to interact with the nrepl session
 - Have a reasonable source folder structure

**done**

 - nice consistent callback api. All operations invoked on the session take appropriately named callback functions. All callbacks that take a value will be invoked with three arguments, the session, the id that got the value and the actual value. All status callbacks (eg `done`) takes the session and the id.
 - these sessions commands are done:

      - `eval`
      - `describe`
      - `close`
      - `load-file`
      - `interrupt`
      - `stdin`
      - `ls-sessions`


## Feature list
 - Implement the suggestions on [this page](http://infinitemonkeycorps.net/docs/pph/)