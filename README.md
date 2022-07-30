# Simple file transfer system

This is a simple system to transfer files between machines on the same network.
Totally unsafe, and mostly a toy system for learning how to create quick
network servers in Python.

## How it works

* launch a `registry` at a well known IP and port
* participants run a `receiver`
  * registers itself in the registry
  * accepts files from peers (after asking the user)
* files are sent with the `send` command

## Example

Run registry in one terminal:

```
venv/bin/python registry.py localhost 60000
```

Run receiver in another terminal:

```
venv/bin/python receiver.py localhost 60001 my_receiver
```

Send a file from yet another terminal:

```
venv/bin/python client.py send my_receiver /tmp/bigfile.dat
```

Back in the receiver's terminal the user will have to accept/deny the file
transfer request. If accepted the file is streamed over to the receiver and
saved in a `files` directory relative to `cwd`. Receiver can override save
location with `SAVE_DIR` env variable.
