# ngc

A version control system created as a proof-of-concept project. 

[![ngc-workflow Actions Status](https://github.com/drs-11/ngc/workflows/ngc-build/badge.svg)](https://github.com/drs-11/ngc/actions)
---

## Commands

Initialise a folder as an ngc repo:

```
$ alias ngc="python3 /path/to/ngc/ngc.py"
$ ngc init
```

Commit changes in a repo:

```
$ ngc commit
Enter commit message: first commit
```

Get status of modified files:

```
$ ngc status
```

Reset to the last commit:

```
$ ngc reset
```

Get the logs of commits:

```
$ ngc log
```

Checkout a specific commit:

```
$ ngc checkout <hash value of commit>
```

---

A design document was made for this project located in docs.
