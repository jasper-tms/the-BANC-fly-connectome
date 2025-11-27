# The Brain And Nerve Cord fly connectome

The BANC (said "the bank") is the Brain And Nerve Cord, a connectome of a female adult _Drosophila melanogaster_'s central nervous system generated from a GridTape transmission electron microscopy dataset.
- Read our bioRxiv preprint: **["Distributed control circuits across a brain-and-cord connectome"](https://www.biorxiv.org/content/10.1101/2025.07.31.667571)**
- Find more resources on **[our Wiki](https://github.com/jasper-tms/the-BANC-fly-connectome/wiki)**

This repository contains a python package for interacting with the connectome data (see the folder [`banc/`](banc), and installation instructions below), mainly focused on the effort to _build_ the connectome. **Users interested in _downloading and analyzing_ the connectome should go first to [View & download publicly released data](https://github.com/jasper-tms/the-BANC-fly-connectome/wiki#view--download-publicly-released-data).**

Have any questions? Please [open an issue](https://github.com/jasper-tms/BANC-fly-connectome/issues/new) or contact [Jasper Phelps (jasper.s.phelps@gmail.com)](http://jasper.science).

## Installing and configuring the `banc` python package

### Before you start

As is always the case in python, consider making a virtual environment (using your preference of virtualenv/virtualenvwrapper or conda) before installing.

### Installation option 1: pip install from PyPI

    pip install banc

### Installation option 2: pip install directly from GitHub
The code on GitHub will sometimes be slightly more up to date than the version on PyPI

    pip install git+https://github.com/jasper-tms/BANC-fly-connectome.git

### Installation option 3: Clone then install
This is the best option if you want to make changes yourself to the code

    cd ~/repos  # or wherever you keep your repos
    git clone https://github.com/jasper-tms/BANC-fly-connectome.git
    cd BANC-fly-connectome
    pip install -e .

### Troubleshooting
Depending on your Python 3 version and your operating system, you may need to battle some bugs in order to get the `pip install` commands above to succeed.

If you get something that looks like

    .. ERROR:: Could not find a local HDF5 installation.
       You may need to explicitly state where your local HDF5 headers and
       library can be found by setting the ``HDF5_DIR`` environment
       variable or by using the ``--hdf5`` command-line option.

and you're on a Mac, install `brew` (https://brew.sh) if you haven't yet, then use `brew` to install HDF5 with `brew install hdf5`, then put `HDF5_DIR=/opt/homebrew/opt/hdf5` in front of your `pip install` command (e.g. `HDF5_DIR=/opt/homebrew/opt/hdf5 pip install banc`).

If you get an error that contains

    Error compiling Cython file:
    ...
    Cython.Compiler.Errors.CompileError: tables/utilsextension.pyx

try to `pip install` the latest version of `tables` from GitHub by running `HDF5_DIR=/opt/homebrew/opt/hdf5 pip install git+https://github.com/PyTables/PyTables`, or alternatively, use conda to install it (`conda install tables`). After you get this package installed successfully, try installing `banc` again.

### Provide credentials

Access to the latest reconstruction of BANC is restricted to authorized users. If you are a member of the BANC community (see [Collaborative community](../../wiki#collaborative-community) on this repo's wiki) and have been granted access, you can generate an API key by visiting [https://global.daf-apis.com/auth/api/v1/create_token](https://global.daf-apis.com/auth/api/v1/create_token) and logging in with your BANC-authorized google account. Copy the key that is displayed, then run the following commands in python to save your key to the appropriate file:
```python
import banc
banc.save_cave_credentials("THE API KEY YOU COPIED")
```

Alternatively, you can manually do what the command above accomplishes, which is to create a text file at `~/.cloudvolume/secrets/cave-secret.json` with these contents:

    {
      "token": "THE API KEY YOU COPIED",
      "brain_and_nerve_cord": "THE API KEY YOU COPIED"
    }

You can verify that your API key has been saved successfully by running:
```python
import banc
client = banc.get_caveclient()
```

### Optional installation steps for additional functionality

#### Install Elastix to transform neurons into alignment with the VNC template
The mesh manipulation and coordinate transform code requires `pytransformix`, which is itself a Python wrapper for Elastix. Therefore, Elastix must be installed and its lib and bin paths must be appended to the `LD_LIBRARY_PATH` and `PATH` environment variables. See [`pytransformix` documentation](https://github.com/jasper-tms/pytransformix#installation) for specific instructions.

## Documentation
- First go through [`fanc_python_package_examples.ipynb`](https://github.com/jasper-tms/BANC-fly-connectome/blob/main/example_notebooks/fanc_python_package_examples.ipynb)
- Then check out other notebooks in [`example_notebooks/`](https://github.com/jasper-tms/BANC-fly-connectome/tree/main/example_notebooks)
- Finally you can [browse the code](https://github.com/jasper-tms/BANC-fly-connectome/tree/main/banc), check out modules that have names that interest you, and read the docstrings.

### Technical note
The `banc` package is a fork on the `fanc` (Female Adult Nerve Cord) package, which can be found at the [upstream repository](https://github.com/htem/FANC_auto_recon). To make it easier to synchronize new features in `banc` and `fanc` packages, the folder `banc/` in this repo is a link to the folder `fanc/` – but files in this repo's version of the `fanc/` folder have been adapted for use with the BANC.
