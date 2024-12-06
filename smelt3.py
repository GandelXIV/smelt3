import sys, os, json, hashlib, inspect, atexit

SMELT_CACHE_FNAME = ".smelt"
HELP = """
    No targets or options provided.
    Options:
    --help    -> display this info screen
    --list    -> show a list of all tasks
    --all     -> perform all named tasks
    --clean   -> clean cache and force remaking  
    """   

# globals
named_tasks = {}
named_task_descs = {}
task_cache = {}
# task globals
src_stack = []
skip = False
current_task = None

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

## Caching

def load_cache():
    global task_cache
    if task_cache == {}:
        for line in rf(SMELT_CACHE_FNAME):
            try:
                (id, sign) = line.split(' ')
                task_cache[id] = sign
            except:pass

def save_cache():
    print("Saving cache...")
    body = ""
    for t in task_cache:
        body += f"{t} {task_cache[t]}\n"
    wf(SMELT_CACHE_FNAME, body)

atexit.register(save_cache)

def cache_get(task_id):
    if task_id not in task_cache:
        return None
    return task_cache[task_id]

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
                for task in named_tasks:
                    print(f"--> {task}", end='')
                    if task in named_task_descs:
                        print(" -", named_task_descs[task])
                return
            elif arg == "--all":
                for task in named_tasks:
                    do_task(task)
            elif arg == "--clean":
                wf(SMELT_CACHE, "")
        else:
            do_task(arg)
    
def do_task(name):
    print(f"[GOAL] {name}")
    named_tasks[name]()

## Artifacts

def use(art):
    src_stack[-1].append(art)
    art.set_used()
    return art    

class Artifact:
    ## system
    
    def __del__(self):
        if not self.is_used():
            print("DROPPED AN UNUSED ARTIFACT")

    ## redefinable
    def set_used(self):
        raise BaseException('undefined artifact feature')

    def is_used(self):
        raise BaseException('undefined artifact feature')
    
    def identify(self):
        raise BaseException('undefined artifact feature')
        
    def exists(self):
        raise BaseException('undefined artifact feature')

    def reset(self):
        pass


class Token(Artifact):
    def __init__(self, token):
        self.token = token
        self.used = False

    def set_used(self):
        self.used = True

    def exists(self):
        return True

    def identify(self):
        return self.token

    def is_used(self):
        return self.used
        

class File(Artifact):
    def __init__(self, fname, mtime=False, hash=True, size=True):
        self.used = False
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

    def set_used(self):
        self.used = True

    def exists(self):
        return self.content is not None

    def identify(self):
        return f"{self.fname}{self.content}{self.mtime}{self.size}"

    def __str__(self):
        return self.fname

    def is_used(self):
        return self.used
    

## Actions

def grok_sign(arr):
    sign = ""
    for src in arr:
        if not src.exists():
            print("Missing artifact:", src)
            sys.exit()
        sha256 = hashlib.sha256()
        txt = json.dumps(src.identify()).encode('utf-8')
        sha256.update(txt)
        sign += sha256.hexdigest()
    return sign

def check4skip():
    load_cache()
    global skip
    # Dont recompute if we already know everything is fine
    if skip:
       return True

    sign = grok_sign(src_stack[-1])

    print(sign)
    if cache_get(current_task) == sign:
        skip = True
        print('[SKIP]', current_task)
        return True
    print('[BUILD]', current_task)
    return False

def shell(cmd):
    if check4skip():
        return
    return os.system(cmd)    

## Tasks

def task(name=None, desc=None):
    def real_decorator(f):
        def inner(*args, **kwargs):
            global skip, src_stack, current_task
            current_task = f.__name__
            src_stack.append([File(sys.argv[0])])
            result = f(*args, **kwargs)
            if not skip:
                task_cache[current_task] = grok_sign(src_stack[-1])
            src_stack.pop()
            skip = False
            return result
        if name is not None:
            named_tasks[name] = inner
            if desc is not None:
                named_task_descs[name] = desc
        return inner
    return real_decorator
