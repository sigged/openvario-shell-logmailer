# Log Mailer for the Open Vario Shell

This is an extension for the Open Vario Shell by kedder (https://github.com/kedder/openvario-shell)

Log Mailer adds a menu option through which you can select an IGC log file, and mail to one or more recipients. The OpenVario will require internet access (e.g. Wi-Fi through a mobile hotspot).

## Installation

The easiest way to install is using `opkg` package manager on
internet-connected Openvario device.

```sh
wget https://raw.githubusercontent.com/kedder/openvario-shell/master/scripts/openvario-shell-install.sh -O - | sh
```

After executing this command, `ovshell` command should be available. It will
start automatically next time Openvario boots up.

In case you didn't like it and would like to return to stock Openvario menu,
run this command:

```sh
wget https://raw.githubusercontent.com/kedder/openvario-shell/master/scripts/openvario-shell-uninstall.sh -O - | sh
```

## Development

### Setting up the development environment

The `logmailer` extension uses `pipenv` to create a dev environment so it can run alongside the main `ovshell` application. 

To set this up yourself, do this in a linux/WSL shell:

1. Install python and pipenv

```sh
pip install pipenv  # or pip3 if you don't have "pip"
```

2. Ensure `pipenv` is added to PATH

3. Create a workspace directory e.g. `ovshell-workspace` and clone both these repositories:
  - https://github.com/kedder/openvario-shell 
  - https://github.com/sigged/openvario-shell-logmailer

4. Create this Pipfile in the workspace root folder to install both projects in the same environment

```sh
[packages]
setuptools = "*"
openvario-shell = {editable = true, path = "./openvario-shell"}
openvario-shell-logmailer = {editable = true, path = "./openvario-shell-logmailer"}

```

5. cd to the workspace root and install the enviroment:

```sh
pipenv install
```

6. Now you can activate the environment and run `ovshell`

```sh
pipenv shell
ovshell
```

The `ovshell` main application should automatically find the extenions and install it during startup.

It is possible to adjust few options by providing them in an `.env`, which you can place in the workspace root directory. It is useful to point the xcsoar path to a local folder containing log files:

Sample **.env** file:
```
XCSOAR_HOME = /mnt/c/OVData/xcsoar-test-home
```

