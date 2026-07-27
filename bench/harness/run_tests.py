"""Framework-free test runner: discovers test_* functions in test_*.py files,
runs them, exits 1 on any failure. Kept dependency-free so neither benchmark
arm ever needs to install anything."""
import importlib.util
import pathlib
import sys
import traceback


def main():
    failures = 0
    ran = 0
    for path in sorted(pathlib.Path(".").glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[path.stem] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            print("IMPORT FAIL %s" % path)
            traceback.print_exc()
            failures += 1
            continue
        for name in sorted(dir(mod)):
            if not name.startswith("test_"):
                continue
            fn = getattr(mod, name)
            if not callable(fn):
                continue
            ran += 1
            try:
                fn()
                print("PASS %s::%s" % (path.name, name))
            except Exception:
                failures += 1
                print("FAIL %s::%s" % (path.name, name))
                traceback.print_exc()
    print("ran=%d failures=%d" % (ran, failures))
    sys.exit(1 if failures or not ran else 0)


if __name__ == "__main__":
    main()
