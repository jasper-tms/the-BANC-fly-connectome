import numpy as np
from pathlib import Path
import meshparty
import skeletor
import pymaid
import json

def catmaid_login(project,project_id,key_file_path):
    '''' Establish a CATMAID login instance for pulling data from a project. Usually this will run as part of a pull request, not directly.
    
    Parameters
    ----------
    project :     project name in your api key dictionary.  Example uses 'fanc'
    pid:          project ID in the case that there are multiple stacks in the catmaid instance
    key_file:     full file name of the api keys for your catmaid project, check example for format.  DO NOT KEEP THIS IN SOURCE CONTROL!!!
    Returns
    -------
    myInstance:   A CATMAID login instance.  
    ''' 
    
    fname = key_file_path
    with open(fname, 'r') as f:
            apikeys = json.load(f)
    myInstance = pymaid.CatmaidInstance( apikeys[project]['website'],
                                         apikeys[project]['token'],
                                         project_id= project_id);
    return(myInstance)


def pymaid_from_swc(f,smooth_diameter=True,
                    downsample=True,
                    **kwargs):
    
    neuron = pymaid.from_swc(f)
    if smooth_diameter == True:
        if 'smooth_method' in kwargs.keys():
            smooth_method = kwargs['smooth_method']
        else:
            smooth_method = 'strahler'
        if 'smooth' in smooth_method:
            if 'smooth_bandwidth' in kwargs.keys():
                smooth_bandwidth = kwargs['smooth_bandwidth']
            else:
                smooth_bandwidth = 1000
        else:
            smooth_bandwidth = None
        
        neuron = skeleton_manipulations.diameter_smoothing(neuron,smooth_method=smooth_method,smooth_bandwidth=smooth_bandwidth)
    
    if downsample == True:
        if 'downsample_factor' in kwargs.keys():
            downsample_factor = kwargs['downsample_factor']
        else:
            downsample_factor = 4
        
        pymaid.resample.downsample_neuron(neuron,downsample_factor,inplace=True)

        
    return(neuron)
    

    
def upload_to_CATMAID(neuron,
                      target_project=None,
                      annotations = None,
                      NG_voxel_resolution = np.array([4.3,4.3,45]), 
                      CM_voxel_resolution = np.array([4.3,4.3,45])):
    
    target_project = pymaid.utils._eval_remote_instance(target_project)
    
    neuron.neuron_name = neuron.neuron_name[0:str.find(neuron.neuron_name,'_pre_catmaid')]
    neuron.nodes[['x','y','z']] = neuron.nodes[['x','y','z']] / NG_voxel_resolution
    neuron.nodes[['x','y','z']] = neuron.nodes[['x','y','z']] * CM_voxel_resolution
    if annotations is not None:
        pymaid.add_annotations(neuron,annotations)
    
    pymaid.upload.upload_neuron(neuron,source_type='skeleton',remote_instance=target_project,import_annotations=True)