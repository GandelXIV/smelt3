import sys
sys.path.insert(1, '../../')
from smelt3 import task, use, File, cli, shell

@task('app', "Build the application")
def make_app():
    m = use(make_main())
    l = use(make_lib())
    shell(f"gcc {m} {l} -o app")
    return File('app')

@task()
def make_main():
    out = "main.o"
    src = use(File("main.c"))
    shell(f"gcc -c {src} -o {out}")
    return File(out)

@task()
def make_lib():
    out = "lib.o"
    src = use(File("lib.c"))
    shell(f"gcc -c {src} -o {out}")
    return File(out)

cli()
