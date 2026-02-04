# pygame-ios

Run pygame-ce games on iPhones and iPads easily.

This package contains a simple CLI tool that downloads a template from [pygame-ios-templates](https://github.com/seekerluke/pygame-ios-templates) and adds your game files to it. After that you can run the Xcode project and see your pygame-ce game on your device or simulator of choice.

## Usage

Assuming you have Python 3, run this to install the package:

```bash
pip install pygame-ios
```

This gives you a command you can run with one of the following:

```bash
pygame-ios
python -m pygame-ios
```

This command needs arguments. You need to provide a location for your project folder where your files will be copied from, as well as an entry point script which will be renamed to `__main__.py` and used as the entry point in Xcode.

Example usage:

```bash
pygame-ios . game.py # copies files from current folder, uses game.py as the entry point script
```

After running this command, an Xcode project will be downloaded. You can open this project in Xcode and run it on a device or simulator.

To update your Xcode project with new files or changes, just run the command again. The download step is skipped and your files are copied, overwriting previous files.

### Other Arguments

You can also specify a pygame-ce version:

```bash
pygame-ios . game.py 2.5.5 # fetches the v2.5.5 version of the template
```

Without this argument, the command will download the latest template available. But you can specify a pygame-ce version in case you need something different from the latest stable. Not all pygame-ce versions are supported, see [here](https://github.com/seekerluke/pygame-ios-templates/releases) for supported versions, and see the [repository README](https://github.com/seekerluke/pygame-ios-templates?tab=readme-ov-file#making-new-templates) for details on how to make your own.
