# Gnome Desktop Session Restore

`gnome-desktop-session-restore`

This is a simple tool that restores the state of one or more Gnome workspaces.
It is designed on Ubuntu 20.04 but should work with earlier versions but is as
yet untested in older versions. It may also work on other Linux distros that
also use Gnome workspaces.

## Prerequisits/Dependencies

This tools is written in Python and requires a Python interpreter. We also use
the `wmctrl` tool to manage windows. These can be installed by running
[`install.sh`](./install.sh). This installation script uses `apt` to install
dependencies thus it will only work on Debian-derived distros.

## Installation

Run the installation script:

* via `curl`:
  ```bash
  curl -so- https://raw.githubusercontent.com/K-and-R/gnome-desktop-session-restore/v0.1.0/install.sh | bash
  ```

* via `wget`:
  ```bash
  wget -qO- https://raw.githubusercontent.com/K-and-R/gnome-desktop-session-restore/v0.1.0/install.sh | bash
  ```

## Configuration

The configuration file is `~/.gnome-desktop-session.json`. There is [an example
file included in this repo](./session.json.example) which can be obtained from
GitHub and used as a starting point for configation:

```bash
curl -s https://raw.githubusercontent.com/K-and-R/gnome-desktop-session-restore/v0.1.0/session.json.example -o ~/.gnome-desktop-session.json
```

This configration file is meant to be modified. It is expected to be valid JSON.
You can validate your JSON file using [JSONLint](https://jsonlint.com/).

NB: This configuration file is created by the `install.sh` script, from the
example file, if it doesn't already exist.

## Restoring a Session

Simply run: `restore-gnome-desktop-session`

## Upgrade

To upgrade to a newer version, simply run the installation script for that newer
version.

## Uninstallation

To remove this tool and its configuration file, run [`uninstall.sh`](./uninstall.sh):

```bash
curl -so- https://raw.githubusercontent.com/K-and-R/gnome-desktop-session-restore/v0.1.0/uninstall.sh | bash
```

NB: The additional packages installed by the `install.sh` script (`curl`,
`python`, and `wmctrl`) will not be removed automatically and will need to be
removed manually if they are no longer wanted:

```bash
sudo apt remove curl python wmctrl
```

## Maintainers

* [Karl Wilbur](https://github.com/karlwilbur)
