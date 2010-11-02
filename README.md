## Description

Running practice contests on PC^2 requires you to have input/output data for
each problem. Sometimes it is not available. This solution allows you to use
regular PC^2 but with custom external validator which will submit problem to
online judge and read the verdict.

You need to have registered accounts on online judges and configure valodator.

## Supported PC^2 on linux

Testing was done with PC^2 version 8 and 9. Instructions shown here are for 
version 9, differences between versions 8 and 9 are minimal but they exist.

## Configuring valodator

Copy config file to `/etc/`

    sudo cp valodator.config.sample /etc/valodator.sample

If you don't like to polute `/etc` you can put it someplace else and change
`valodator.py` accordingly.

_Remember_: **path to config file must be absolute and not relative path**.

## Configuring PC^2 for valodator

### Step 1: Languages tab

Since we are using online validator, program does not have to be executed
on our computer instead we would like to give it online judge for evaluation.

In the field **Execution command line** you should put something trivial like
`echo`. I chose `echo` since it is mostly harmless and is present on every 
unix-like system.

![Languages window](http://imgur.com/yTuDY.png) ![Languages tab](http://imgur.com/hsYDe.png)

If you want to be adventurous you can try replacing compiler command with
`touch` command, this is not important and it is up to you.

### Step 2: Add new problems

To configure problems follow screenshots shown below.

![Problem window 1](http://imgur.com/9cV1H.png) ![Problem window 2](http://imgur.com/2GNzv.png) ![Problem window 3](http://imgur.com/eQZlF.png)

In short, you don't need to set input/output files and you need to set
external validator to `validator.py`. In addition, **validator command line**
should be  set to, for example:

    ./{:validator} {:mainfile} {:resfile} tju/1001

Last argument is the reference to the problem, it has following format:

    <website>/<problem>

Value of `<website>` can be of following

* `uva`
* `livearchive`
* `tju`
* `timus`

## Future support

This will work only until some change is made on online judge website which 
will cause this validator to misbehave.

## Contact

Here on github or email: [emiraga@gmail.com](mailto:emiraga@gmail.com)

