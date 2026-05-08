#!/usr/bin/env python3

def _check_dependency_versions():
    from packaging.version import Version
    import caveclient
    import nglui
    minimums = [
        ('caveclient', caveclient.__version__, '8.0.0'),
        ('nglui', nglui.__version__, '4.0.0'),
    ]
    for name, found, minimum in minimums:
        if Version(found) < Version(minimum):
            raise ImportError(
                f'fanc requires {name}>={minimum}, but found {name}=={found}. '
                f'Please upgrade with:  pip install --upgrade "{name}>={minimum}"'
            )

_check_dependency_versions()
del _check_dependency_versions

from . import (
    annotations,
    connectivity,
    lookup,
    skeletonize,
    statebuilder,
    statemanager,
    synaptic_links,
    template_spaces,
    transforms,
    upload
)

from .auth import *
from .render_neurons import *
from .visualize import plot_neurons
