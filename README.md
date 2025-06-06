# filemaker_recovery_check

## Validate files in a directory using the FMDeveloperTool

```
filemaker_recovery_check directoryPath filePattern [-n | --newest] [-p | --passphrase]
```

Run a recovery of any found files in the specified directory, and then scan the resulting log for any issues it had validating objects.

An exact directory can specified, but more often you may need to use the `-n` or `--newest` option so you can have it use whichever directory was most recently modified. This allows pointing it to FMS' Backup directory and but only scan the files in the most recent backup directory.
