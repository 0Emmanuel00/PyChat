# PyChat — version source of truth
# Format : MAJOR.MINOR.PATCH  (SemVer)

MAJOR = 0
MINOR = 2
PATCH = 1

VERSION = f"{MAJOR}.{MINOR}.{PATCH}"
APP_NAME = "PyChat"
FULL_NAME = f"{APP_NAME} v{VERSION}"


if __name__ == "__main__":
    print(FULL_NAME)
