import sys, os, json, hashlib, inspect, atexit

CACHE_FILENAME = ".smelt"
HELP = """
    No targets or options provided.
    Options:
    --help    -> display this info screen
    --list    -> show a list of all tasks
    --all     -> perform all named tasks
    --clean   -> clean cache and force remaking
    """

# Globals

tasklist = {}

class TaskNode:
    def __init__(self, fun, id, pubname=None, pubdesc=None):
        self.fun = fun
        self.id = id
        self.pubname = pubname
        self.pubdesc = pubdesc
        self.skip = False
        self.srcs = []

def find_my_taskid():
    #print("=============")
    stack = inspect.stack()
    for finfo in stack:
        frame = finfo.frame
        #print(finfo[3])
        # print(finfo)
        if "__secret" in frame.f_locals:
            return frame.f_locals["__secret"]
        elif finfo[3] in tasklist:
            return finfo[3]

    # raise BaseException("something went wrong :P")

def find_my_tasknode():
    return tasklist[find_my_taskid()]

## utils

def rf(name):
    with open(name, 'r') as f:
        return f.read()

def rfb(name):
    with open(name, 'rb') as f:
        return f.read()

def af(name, data):
    with open(name, 'a') as f:
        return f.write(data)

def wf(name, data):
    with open(name, 'w') as f:
        return f.write(data)

## Caching, for now inefficient

def cache_spawn():
    if not os.path.exists(CACHE_FILENAME):
        wf(CACHE_FILENAME, "")

def cache_get(taskid):
    cache_spawn()
    for line in rf(CACHE_FILENAME).split('\n'):
        try:
            (id, sign) = line.split(' ')
            if id == taskid:
                return sign
        except: pass
    return None

def cache_set(taskid, sign):
    cache_spawn()
    body = ""
    present = False
    for line in rf(CACHE_FILENAME).split('\n'):
        try:
            (id, csign) = line.split(' ')
        except:
            continue
        if id == taskid:
            present = True
            body += f"{taskid} {sign}\n"
        else:
            body += f"{id} {csign}\n"
    if not present:
        body += f"{taskid} {sign}\n"
    wf(CACHE_FILENAME, body)

## Interaction

def cli():
    if len(sys.argv) == 1:
        print(HELP)
        return
    for arg in sys.argv[1:]:
        if arg[0:2] == "--":
            if arg == "--help":
                print(HELP)
                return
            elif arg == "--list":
                print("Available tasks:")
                for tn in tasklist.values():
                    if tn.pubname is not None:
                        print(f"--> {tn.pubname}", end='')
                        if tn.pubdesc is not None:
                            print(" -", tn.pubdesc)
                        else:
                            print('')
                return
            elif arg == "--all":
                for task in tasklist.values():
                    if task.pubname is not None:
                        do_task(task.pubname)
            elif arg == "--clean":
                wf(CACHE_FILENAME, "")
            else:
                print(f"No option '{arg}' found")
        else:
            do_task(arg)

def do_task(name):
    print(f"[GOAL] {name}")
    validpubname = False
    for tn in tasklist.values():
        if tn.pubname == name:
            tn.fun()
            validpubname = True
    if not validpubname:
        print(f"Could not find task with public name '{name}'")

## Artifacts

def use(art):
    find_my_tasknode().srcs.append(art)
    art.set_used()
    return art

class Artifact:
    ## system

    def __init__(self):
        self.used = False

    def set_used(self):
        self.used = True

    def is_used(self):
        return self.used

    def __del__(self):
        if not self.is_used():
            print("[WARN] Dropped an unused artifact")

    # redefinable
    def identify(self) -> str:
        raise BaseException('undefined artifact feature')

    def exists(self) -> bool:
        raise BaseException('undefined artifact feature')

    def reset(self):
        pass


class Token(Artifact):
    def __init__(self, token):
        super().__init__()
        self.token = token

    def identify(self):
        return self.token

    def exists(self):
        return True

    def is_used(self):
        return self.used


class File(Artifact):
    def __init__(self, fname, mtime=False, hash=True, size=True):
        super().__init__()
        self.fname = fname
        self.content = None
        self.mtime = None
        self.size = None
        if os.path.exists(fname):
            if hash:
                self.content = rfb(fname).decode('latin-1')
            if mtime:
                self.mtime = os.path.getmtime(fname)
            if size:
                self.size = os.path.getsize(fname)

    def exists(self):
        return self.content is not None

    def identify(self):
        return f"{self.fname}{self.content}{self.mtime}{self.size}"

    def __str__(self):
        return self.fname

## Minimalization

def grok_sign(arr):
    sign = ""
    for src in arr:
        if not src.exists():
            print("Missing artifact:", src)
            sys.exit()
        sha256 = hashlib.sha256()
        txt = json.dumps(src.identify()).encode('utf-8')
        sha256.update(txt)
        sign += sha256.hexdigest() + "+"
    return sign

def check4skip():
    tnode = find_my_tasknode()

    # Dont recompute if we know nothing has changed. This assumes that sources are not modified during builds.
    if tnode.skip:
       return True

    sign = grok_sign(tnode.srcs)
    #print(tnode.fun, sign, cache_get(tnode.id))
    cached_sign = cache_get(tnode.id)
    #print(cached_sign, sign, tnode.skip)
    if cached_sign == sign:
        tnode.skip = True
        print(f'[SKIP] {tnode.id} ({tnode.pubname})')
        return True
    print(f'[EXEC] {tnode.id} ({tnode.pubname})')
    return False

## Actions

def shell(cmd):
    if check4skip():
        return
    return os.system(cmd)

## Tasks

def task(name=None, desc=None):
    def real_decorator(f):
        def inner(__secret=f.__name__, **kwargs):
            tnode = find_my_tasknode()
            scriptdep = File(sys.argv[0])
            scriptdep.set_used()
            tnode.srcs.append(scriptdep)
            result = f(**kwargs)
            if not tnode.skip:
                cache_set(tnode.id, grok_sign(tnode.srcs))
            # clearing sources
            tnode.srcs = []
            return result
        id  = f.__name__
        tasklist[id] = TaskNode(inner, id, name, desc)
        return inner
    return real_decorator
