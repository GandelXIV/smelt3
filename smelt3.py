import sys, os, json, hashlib, inspect, atexit, shutil, subprocess

HELP = """
    No targets, settings or options provided.
    Options:
    --help    -> display this info screen
    --list    -> show a list of all tasks
    --all     -> perform all named tasks
    --clean   -> clean cache and force remaking
    Setting syntax: NAME=VALUE
    """
# Config
CACHE_FILENAME = ".smelt"
CACHE_SYNC_PERIODIC = False
CACHE_SYNC_ATEXIT = True
SETTING_RC_FILENAME = "smeltrc.cfg"

# Globals

tasklist = {}
cache = {}
is_cache_changed = False
settings = {}

# Core

class TaskNode:
    def __init__(self, fun, id, pubname=None, pubdesc=None):
        self.fun = fun
        self.id = id
        self.pubname = pubname
        self.pubdesc = pubdesc
        self.skip = False
        self.setting_tracker = Token({})
        self.setting_tracker.set_used()
        self.srcs = [self.setting_tracker] # First token will hold used settings

def find_my_taskid():
    stack = inspect.stack()
    for finfo in stack:
        frame = finfo.frame
        if "__secret" in frame.f_locals:
            return frame.f_locals["__secret"]
        elif finfo[3] in tasklist:
            return finfo[3]

    raise BaseException("Invalid context, no associated task found")

def find_my_tasknode():
    return tasklist[find_my_taskid()]

## Setting management

def create_setting(name, default_value):
    global settings
    settings[name] = default_value

def sett(setting):
    tn = find_my_tasknode()
    if not (setting in tn.setting_tracker.token):
        tn.setting_tracker.token[setting] = settings[setting]
    return settings[setting]

def update_setting(line):
    (setting, value) = line.split("=")
    if setting not in settings:
        print(f"Unknown setting '{setting}'")
        sys.exit()
    settings[setting] = value

def load_setting_rc():
    global settings
    if not os.path.exists(SETTING_RC_FILENAME):
        return
    print(f"Loading settings from {SETTING_RC_FILENAME}...")
    for line in SETTING_RC_FILENAME:
        if "=" in line:
            update_setting(line)

## FS utils

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

## Caching

def cache_spawn():
    global cache
    if not os.path.exists(CACHE_FILENAME):
        wf(CACHE_FILENAME, "")
        return
    for line in rf(CACHE_FILENAME).split('\n'):
        try:
            (id, sign) = line.split(' ')
            cache[id] = sign
        except: pass

def cache_sync():
    if not is_cache_changed:
        return
    body = ""
    for id in cache:
        body += f"{id} {cache[id]}\n"
    wf(CACHE_FILENAME, body)
    print(f"[SYNC] Cache {CACHE_FILENAME}")

atexit.register(lambda: cache_sync() if CACHE_SYNC_ATEXIT else None )

def cache_get(taskid):
    global cache
    cache_spawn()
    if taskid not in cache:
        return None
    return cache[taskid]

def cache_set(taskid, sign):
    global cache, is_cache_changed
    cache[taskid] = sign
    is_cache_changed = True
    if CACHE_SYNC_PERIODIC:
        cache_sync()

"""
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
"""

## Interaction

def cli():
    if len(sys.argv) == 1:
        print(HELP)
        return
    load_setting_rc()
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
                print("Avaiable settings:")
                for s in settings:
                    print(f"{s}={settings[s]}")
                return
            elif arg == "--all":
                for task in tasklist.values():
                    if task.pubname is not None:
                        do_task(task.pubname)
            elif arg == "--clean":
                wf(CACHE_FILENAME, "")
            else:
                print(f"No option '{arg}' found")
        elif "=" in arg:
            update_setting(arg)
        else:
            do_task(arg)

def do_task(name):
    print(f"[GOAL] {name}")
    validpubname = False
    for tn in tasklist.values():
        if tn.pubname == name:
            final = tn.fun()
            if type(final) != type([]):
                final = [final]
            print("[DONE] ", end="")
            for a in final:
                a.set_used()
                print(a.display(), end=" ")
            print()
            validpubname = True
    if not validpubname:
        print(f"Could not find task with public name '{name}'")

def use(art):
    # Flatten lists and dicts
    if type(art) == type([]):
        for a in art:
            use(a)
        return art
    elif type(art) == type({}):
        for val in art.values():
            use(val)
        return art

    find_my_tasknode().srcs.append(art)
    art.set_used()
    return art

## Artifacts

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

    def display(self) -> str:
        raise BaseException('undefined artifact feature')


class Token(Artifact):
    def __init__(self, token):
        super().__init__()
        self.token = token

    def identify(self):
        return str(self.token)

    def exists(self):
        return True

    def display(self) -> str:
        return f"Token({self.token})"


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
        return os.path.exists(self.fname)

    def identify(self):
        return f"{self.fname}{self.content}{self.mtime}{self.size}"

    def display(self) -> str:
        return f"File({self.fname})"

    def __str__(self):
        return self.fname

# Tools

def file_tree(directory: str):
    result = {}
    for e in os.listdir(directory):
        if os.path.isfile(directory + "/" + e):
            result[e] = File(directory + "/" + e)
        elif os.path.isdir(directory + "/" + e):
            result[e] = file_tree(directory + "/" + e)
    return result

## Minimalization

def grok_sign(arr):
    sign = ""
    for src in arr:
        if not src.exists():
            print("[ERROR] Missing artifact:", src.display())
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
    cached_sign = cache_get(tnode.id)

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
    print(cmd)
    ret = subprocess.call(cmd, shell=True)
    if ret != 0:
        print(f"[ERROR] While shell processing: {cmd}")
        sys.exit(ret)

def copy(src, dest):
    if check4skip():
        return
    print(f"> copy {src} to {dest}")
    shutil.copy(src, dest)

def delete(fname, ignore_error=False):
    if check4skip():
        return
    print("> delete", fname)
    if ignore_error:
        try:
            os.remove(fname)
        except: pass
    else:
        os.remove(fname)

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
