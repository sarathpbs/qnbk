## DEVEX

# venerable build tool
# Follow caveats during installation to complete setup
brew "make" if OS.mac? # otherwise, assume we have GNU Make on Linux
# Python version manager
# Follow caveats during installation to complete setup
brew "pyenv"
# Manage virtualenvs with Pyenv just in case
brew "pyenv-virtualenv"
# Pre-commit checks, if we have a config
brew "pre-commit" if File.exist?(".pre-commit-config.yaml")
# json query
brew "jq"

## PYTHON BUILD DEPENDENCIES
py_version = open(".python-version").read.strip.split(".").take(2).join(".")
# Drop link:false when https://github.com/orgs/Homebrew/discussions/6133 is fixed
brew "python@#{py_version}", link: false, args: ["only-dependencies"]
# PyEnv suggests installing these for building Python using
# Homebrew-provided dependencies on Linux.
# This exists here primarily for running in containers, such as
# for devex CI and for demos.
# This can probably go away in favor of installing Homebrew's
# Python dependencies above, but kept here since there are
# some differences between that and what PyEnv suggests.
if OS.linux?
  brew "bzip2"
  brew "libffi"
  brew "openssl@3"
  brew "readline"
  brew "sqlite"
  brew "xz"
  brew "zlib"
end

# vim: set filetype=ruby syntax=brewfile
