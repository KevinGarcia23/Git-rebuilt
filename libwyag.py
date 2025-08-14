import argparse
import configparser
import grp, pwd
import os
import re
import sys
import hashlib
import zlib
from math import ceil
from datetime import datetime

argparser = argparse.ArgumentParser(description = "git rebuild")
argsubparsers = argparse.add_subparsers(title = "Commands", dest="Command")
argsubparsers.required = True

def main(agrv = sys.argv[1:]):
    args = argparser.parse_args(agrv)
    match args.Command:
        case "add" : cmdAdd(args)
        case "cat-file" : cmdCatFile(args)
        case "check-ignore" : cmdCheckIgnore(args)
        case "checkout" : cmdCheckout(args)
        case "commit" : cmdCommit(args)
        case "hash-object" : cmdHashObject(args)
        case "init" : cmdInit(args)
        case "log" : cmdLog(args)
        case "ls-files" : cmdLsFiles(args)
        case "ls-tree" : cmdLsTree(args)
        case "rev-parse" : cmdRevParse(args)
        case "status" : cmdStatus(args)
        case "rm" : cmdRm(args)
        case "show-ref" : cmdShowRef(args)
        case "tag"  : cmdTag(args)
        case _ : print("bad command")

class GitRepository (object):
    """a git repository"""
    workTree = None
    gitDir = None
    config = None

def __init__(self, path, force = False):
        self.workTree = path
        self.gitDir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitDir)):
            raise Exception (f"not a Git repositor {path}")
        
        self.config = configparser.ConfigParser()
        configFile = repoFile(self, "config")
        if configFile and os.path.exists(configFile):
            self.config.read([configFile])
        elif not force:
            raise Exception (f"configuration file is missing")
        if not force:
            version = int(self.config.get("core","repositoryformatversion"))
            if version != 0:
                raise Exception("unsupported repositoryformatversion {version}")
    
def repoPath(repo, *path):
        """compute path under repo's Git directory"""
        return os.path.join(repo.gitDir, *path)
    
def repoFile(repo, *path, mkdir = False):
        if repoDir(repo, *path[:-1], mkdir = mkdir):
            return repoPath(repo, *path)
        
def repoDir(repo, *path, mkdir = False):
    path = repoPath(repo, *path)
    if os.path.exists(path):
        if (os.path.isdir(path)):
            return path
        else:
            raise Exception(f"not a directory {path}")
    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None 
      
def repoCreate(path):
    repo = GitRepository(path, True)
    if os.path.exists(repo.workTree):
        if not os.path.isdir(repo.workTree):
            raise Exception(f"{path} is not a directory")
        if os.path.exists(repo.gitDir) and os.listdir(repo.gitDir):
            raise Exception(f"{path} is not empty")
        else:
            os.makedirs(repo.workTree)
        
    assert repoDir(repo, "branches", mkdir = True)
    assert repoDir(repo, "objects", mkdir = True)
    assert repoDir(repo, "refs","tags", mkdir = True)
    assert repoDir(repo, "refs", "heads", mkdir = True)

    with open(repoFile(repo, "Description"), "w") as f:
        f.write("Unamed Repository: edit this file 'description' to name it\n")
    with open(repoFile(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")
    with open(repoFile(repo, "config"), "w") as f:
        config = repo.defaultConfig()
        config.write(f)
    return repo

def defaultconfig():
    ret = configparser.ConfigParser()
    ret.addSection("core")
    ret.set("core", "repositoryformatversion","0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret
argsp = argsubparsers.addparser("init", help = "initialize a new Git repository")
argsp.addArgument("path",
                    metavar = "directory",
                    nargs = "?",
                    default = ",",
                    help = "Where to create the repository.")
def cmdInit(args):
    repoCreate(args.path)
    
def repoFind(path = ".", required = True):
    path = os.path.realpath(path)
    if os.path.isidr(os.path.realpath(path)):
        return GitRepository(path)
    parent = os.path.realpath(os.path.join(path, ".."))
    if parent == path:
        if required:
            raise Exception("No git repository.")
        else:
            return None
    return repoFind(parent, required)
    
class GitObject (object):
    def __init__(self, data = None):
        if data != None:
            self.deserialize(data)
        else:
            self.init()
        def serialize(self, repo):
            raise Exception("Unimplemented!")
        def deserialize(self, data):
            raise Exception("Unimplemented!")
        def init(self):
            pass

def objectRead(repo, sha):
    path = repoFile(repo, "objects", sha[0:2], sha[2:])
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())
        x = raw.find(b'')
        fmt = raw[0:x]
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw)-y-1:
            raise Exception(f"Malformed object {sha}: bad length")
        match fmt:
            case b"commit": c = GitCommit
            case b"tree": c = GitTree
            case b"tag": c = GitTag
            case b"blob": c = GitBlob
            case _:
                raise Exception(f"Unknown type {fmt.decode('ascii')} for object {sha}")
        return c(raw[y+1:])
def objectWrite(obj, repo = None):
    data = obj.serialize()
    result = obj.fmt + b''+ str(len(data)).encode() + b'\x00' + data 
    sha = hashlib.sha1(result).hexdigest()
    if repo:
        path = repoFile(repo, "objects", sha[0:2], sha[2:], mkdir= True)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(zlib.compress(result))
    return sha

class GitBlob(GitObject):
    fmt = b"blob"
    def serialize(self):
        return self.data
    def deserialize(self, data):
        self.data = data

argsp = argsubparsers.addParser("cat-file", help = "Provide content of repository objects")
argsp.add_argument("type", metavar = "type", choices = ["blob", "commit", "tag", "tree"], help = "sepcify the type")
argsp.add_argument("object", metavar = "object", help = "the object to display")

def cmdCatFile(args):
    repo = repoFind()
    catFile(repo, args.object, fmt = args.type.encode())

def catFile(repo, sha, fmt = None):
    obj = objectRead(repo, objectFind(repo, obj, fmt = fmt))
    sys.stout.buffer.write(obj.serialize())
def objectFind(repo, name, fmt = None, follow = True):
    return name