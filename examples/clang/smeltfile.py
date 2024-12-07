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
    # Artifacts can be configured to reduce build analysis time
    return File(out, mtime=True, hash=False)

# We can define abstractions
def gcc_compile(main, name="a.out", hdrs=[], tobj = False):
    use(File(main))
    for hdr in hdrs:
        use(File(hdr))
    flags = ""
    if tobj:
        flags += "-c"
    shell(f"gcc {flags} {main} -o {name}")
    return File(name)

# A task using an abstraction
@task()
def make_lib():
    return gcc_compile(
        main = "lib.c",
        name = "lib.o",
        hdrs = ["lib.h"],
        tobj = True
    )

# Turn this script into a CLI program
smelt3.cli()
