# Disclaimer

This library is not well tested, and shouldn't be considered production ready. Most importantly, I haven't tested App Store builds yet.

There's still a lot of work to be done and I'm working on documenting what's doable and what's not.

---

# pygame-ios

Run pygame-ce games on iPhones and iPads easily.

This package contains a simple CLI tool that downloads a template from [pygame-ios-templates](https://github.com/seekerluke/pygame-ios-templates) and adds your game files to it. After that you can run the Xcode project and see your pygame-ce game on your device or simulator of choice.

## Usage

To use this package, you need macOS, and you need Xcode and Python 3 installed.

Run this to install the package:

```bash
pip install pygame-ios
```

This gives you a command you can run with one of the following:

```bash
pygame-ios
python -m pygame-ios
```

This command needs arguments. You need to provide a location for your project folder where your files will be copied from, as well as an entry point script which will be renamed to `__main__.py` and used as the entry point in Xcode. You must also specify the pygame-ce version.

Example usage:

```bash
pygame-ios . game.py 2.5.6 # copies files from current folder, uses game.py as the entry point script, pygame-ce v2.5.6
```

After running this command, an Xcode project will be downloaded. You can open this project in Xcode and run it on a device or simulator.

To update your Xcode project with new files or changes, just run the command again. The download step is skipped and your files are copied, overwriting previous files.

It's recommended that you modify the Xcode project directly if you want to change metadata like the product name and icon, and add it to source control. **You cannot recover these changes if you delete the project,** like you might be able to in other libraries like Briefcase or Flutter.

Not all pygame-ce versions are supported, see [here](https://github.com/seekerluke/pygame-ios-templates/blob/main/patches/pygame-ce.json) for supported versions, and see the [repository README](https://github.com/seekerluke/pygame-ios-templates?tab=readme-ov-file#making-new-templates) for details on how to make your own.
