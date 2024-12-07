import sys
sys.path.insert(1, '../../')
from smelt3 import task, use, File, cli, shell

@task('app', "Build the application")
def make_app():
    out = "app"
    obj1 = use(make_main())
    obj2 = use(make_lib())
    shell(f"gcc {obj1} {obj2} -o {out}")
    return File(out)

@task('main.o')
def make_main():
    out = "main.o"
    src = use(File("main.c"))
    hdr = use(File("lib.h"))
    shell(f"gcc -c {src} -o {out}")
    return File(out)

@task()
def make_lib():
    out = "lib.o"
    src = use(File("lib.c"))
    hdr = use(File("lib.h"))
    shell(f"gcc -c {src} -o {out}")
    return File(out)

cli()
