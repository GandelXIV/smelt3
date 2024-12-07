import sys
sys.path.insert(1, '../../')
import smelt3
from smelt3 import task, use, File, shell

# Tasks are functions that simply return their produced artifacts
@task('app', "Build the application")
def make_app():
    out = "app"
    # We can use the output of another task as our sources
    # All artifacts we want to use as sources need to be marked with the `use()` function
    obj1 = use(make_main(compiler="cc"))
    obj2 = use(make_lib())
    # `shell()` is an action, meaning it will only be executed if there was a change of sources
    shell(f"gcc {obj1} {obj2} -o {out}")
    return File(out)

@task('main.o')
# Tasks can have keyword arguments
def make_main(compiler="gcc"):
    out = "main.o"
    # If we want to depend on file content, we can use the `File` artifact
    src = use(File("main.c"))
    hdr = use(File("lib.h"))
    shell(f"{compiler} -c {src} -o {out}")
    return File(out)

@task()
def make_lib():
    out = "lib.o"
    src = use(File("lib.c"))
    hdr = use(File("lib.h"))
    shell(f"gcc -c {src} -o {out}")
    return File(out)

# Turn this script into a CLI program
smelt3.cli()
