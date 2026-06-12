import os
import subprocess
import sys

FILE = "download1.txt"

def install():
    if not os.path.exists(FILE):
        print("download1.txt not found!")
        return

    with open(FILE, "r") as f:
        libs = [i.strip() for i in f if i.strip()]

    for lib in libs:
        print(f"Installing: {lib}")
        subprocess.run([sys.executable, "-m", "pip", "install", lib])

    print("Done.")

if __name__ == "__main__":
    install()

