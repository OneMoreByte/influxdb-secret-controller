import os
import tomllib


def main():
    print("checking pyproject for version")
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    version = data["tool"]["poetry"]["version"]
    print(f"current version is {version}")

    print("writing version to github environment as CURRENT_VERSION")
    with open(os.getenv("GITHUB_ENV"), "a") as f:
        f.write("CURRENT_VERSION=" + version)


if __name__ == "__main__":
    main()
