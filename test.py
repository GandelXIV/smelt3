import smelt3
from smelt3 import task, Token, shell, File, use

@task('hello')
def hello():
    print("Hello World!")

@task('test')
def testlol():
    x = use(Token("123"))
    shell("echo All good!")

@task('foo')
def foo():
    x = use(File("foo.txt"))
    shell(f"echo 123 > {x}")
    return x

@task('bar')
def bar():
    x = use(foo())
    y = use(File('car.txt'))
    shell(f"cat {x} {y} > bar.txt")
    return File('bar.txt')

## example 1

@task('app')
def make_app():
    m = use(make_main())
    l = use(make_lib())
    shell(f"gcc {m} {l} -o app")
    return File('app')

@task('main.o')
def make_main():
    out = "main.o"
    src = use(File("main.c"))
    shell(f"gcc -c {src} -o {out}")
    return File(out)

@task('lib.o')
def make_lib():
    out = "lib.o"
    src = use(File("lib.c"))
    shell(f"gcc -c {src} -o {out}")
    return File(out)


smelt3.do_task('app')
