#!/usr/bin/env python3

import warnings
import sqlite3

import pandas as pd
import numpy as np

from . import auth


def get_synapses(seg_ids,
                 direction='outputs',
                 threshold=3,
                 drop_duplicates=True,
                 client=None):
    '''
    Find synapses that are either inputs to or outputs from a specified list of neurons
    args:
    seg_ids:          list, int root ids to query
    direction:        str, inputs or outputs
    threshold:        int, synapse threshold to use. default is 3
    drop_duplicates:  bool, whether to drop links between the same supervoxel pair 
    client:           caveclient.CAVEclient or None
    
    returns:
    a pd.DataFrame of synapse information from CAVE, 
    '''
    if isinstance(seg_ids, (int, np.integer)):
        seg_ids = [seg_ids]

    if direction == 'inputs':
        to_find = 'post'
        to_threshold = 'pre'
        
    elif direction == 'outputs':
        to_find = 'pre'   
        to_threshold = 'post'

    if client is None:
        client = auth.get_caveclient()

    result = []                                  
    for i in range(len(seg_ids)):
        syn_i = client.materialize.query_table(
            client.info.get_datastack_info()['synapse_table'],
            filter_equal_dict = {'{}_pt_root_id'.format(to_find): seg_ids[i]}
        )
        if len(syn_i) >= 200000:
            warnings.warn('query is maxed out')
        result.append(syn_i)
    
    result_c = pd.concat(result)
    counts = result_c['{}_pt_root_id'.format(to_threshold)].value_counts()
    t_idx = counts >= threshold
    syn_table = result_c[result_c['{}_pt_root_id'.format(to_threshold)].isin(set(t_idx.index[t_idx==1]))]

    if drop_duplicates:
        syn_table.drop_duplicates(subset=['pre_pt_supervoxel_id',
                                          'post_pt_supervoxel_id'],
                                  inplace=True)

    return syn_table


def get_adj(pre_ids,post_ids,symmetric = False):
    if symmetric is True:
        index = set(pre_ids).intersection(post_ids)
        columns = index
    else:
        index = set(pre_ids)
        columns = set(post_ids)
        
    adj = pd.DataFrame(index=index,columns=columns).fillna(0)
    for i in adj.index:
        partners,synapses = np.unique(post_ids[pre_ids == i],return_counts=True)  
        for j in range(len(partners)):
            adj.loc[i,partners[j]] = synapses[j]
    
    return adj


def get_partner_synapses_csv(root_id, 
                             df, 
                             direction='inputs', 
                             threshold=None):
    if direction == 'inputs':
        to_find = 'post_root'
        to_threshold = 'pre_root'
        
    elif direction == 'outputs':
        to_find = 'pre_root'   
        to_threshold = 'post_root'
    
    partners = df.loc[df[to_find]==root_id]
        
    if threshold is not None:
        counts = partners[to_threshold].value_counts()
        t_idx = counts >= threshold
        
        partners = partners[partners[to_threshold].isin(set(t_idx.index[t_idx==1]))]
    
    return partners


def get_partner_synapses_sql(root_id, 
                         database='synapses.db', 
                         direction='inputs', 
                         threshold=None):
    
    con = sqlite3.connect(database)
    if direction == 'inputs':
        to_find = 'post_root'
        to_threshold = 'pre_root'
        
    elif direction == 'outputs':
        to_find = 'pre_root'   
        to_threshold = 'post_root'
    
    partners = pd.read_sql_query("SELECT * from synapses WHERE {} = {}".format(to_find,root_id),con)

    con.close()   
    if threshold is not None:
        counts = partners[to_threshold].value_counts()
        t_idx = counts >= threshold
        
        partners = partners[partners[to_threshold].isin(set(t_idx.index[t_idx==1]))]


    return partners


def batch_partners(root_id, fname, direction, threshold=None):

    result = pd.DataFrame(columns=['pre_SV','post_SV','pre_pt','post_pt','source','pre_root','post_root'])

    for chunk in pd.read_csv(fname, chunksize=1000000):
        chunk_result = get_partner_synapses_csv(root_id,chunk,direction=direction,threshold=threshold)
        if len(chunk_result) > 0:
            result = result.append(chunk_result, ignore_index=True)
    

    return result 
