import sys

from starter_files.interactive_mode import InteractiveMode
from starter_files.service_mode import ServiceManager

def main():
    if '--service-run' in sys.argv:
        ServiceManager().run()
    else:
        InteractiveMode().run()

if __name__ == "__main__":
    main()