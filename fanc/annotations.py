#!/usr/bin/env python3
"""
This module specifies rules governing what annotations are allowed to be posted
to certain "managed" CAVE tables (where only pre-approved types of annotations
may be posted). These rules are typically used for centralized community tables
to which many users can post annotations, in order to maintain some consistency
in which annotations are posted to the table.
"""

from datetime import datetime, timezone

import anytree

from . import auth, lookup

help_url = 'https://banc.community/Annotations-(cell-types,-etc.)'
help_msg = 'See the annotation scheme described at ' + help_url

default_table = 'cell_info'


cell_info = {
    'primary class': {
        'afferent': {
            'sensory neuron': {
                'unknown sensory subtype': {},
                'visual neuron': {
                    'photoreceptor neuron': {
                        'R1-6': {},
                        'R7': {},
                        'R8': {}},
                    'ocellar neuron': {
                        'ocellar_retinula_cell': {}}},
                'chordotonal neuron': {
                    "Johnston's organ neuron": {},
                    'club chordotonal neuron': {},
                    'claw chordotonal neuron': {},
                    'hook chordotonal neuron': {}},
                'bristle mechanosensory neuron': {
                    'bristle mechanosensory neuron at gustatory sensillum': {}},
                'hair plate neuron': {},
                'campaniform sensillum neuron': {},
                'olfactory receptor neuron': {},
                'gustatory neuron': {},
                'thermosensory neuron': {},
                'hygrosensory neuron': {}}},
        'intrinsic': {
            'central nervous system': {
                'optic lobe intrinsic': {
                    'centrifugal': {
                        'C2': {},
                        'C3': {}},
                    'distal medulla': {
                        'Dm1': {},
                        'Dm2': {},
                        'Dm3p': {},
                        'Dm3q': {},
                        'Dm3v': {},
                        'Dm4': {},
                        'Dm6': {},
                        'Dm8a': {},
                        'Dm8b': {},
                        'Dm9': {},
                        'Dm10': {},
                        'Dm11': {},
                        'Dm12': {},
                        'Dm13': {},
                        'Dm14': {},
                        'Dm15': {},
                        'Dm16': {},
                        'Dm17': {},
                        'Dm18': {},
                        'Dm19': {},
                        'Dm20': {}},
                    'distal medulla dorsal rim area': {
                        'DmDRA1': {},
                        'DmDRA2': {}},
                    'lamina intrinsic': {
                        'Lai': {}},
                    'lamina monopolar': {
                        'L1': {},
                        'L2': {},
                        'L3': {},
                        'L4': {},
                        'L5': {}},
                    'lamina tangential': {
                        'Lat': {}},
                    'lamina wide field': {
                        'Lawf1': {},
                        'Lawf2': {}},
                    'lobula intrinsic': {
                        'Li01': {},
                        'Li02': {},
                        'Li03': {},
                        'Li04': {},
                        'Li05': {},
                        'Li06': {},
                        'Li07': {},
                        'Li08': {},
                        'Li09': {},
                        'Li10': {},
                        'Li11': {},
                        'Li12': {},
                        'Li13': {},
                        'Li14': {},
                        'Li15': {},
                        'Li16': {},
                        'Li17': {},
                        'Li18': {},
                        'Li19': {},
                        'Li20': {},
                        'Li21': {},
                        'Li22': {},
                        'Li23': {},
                        'Li24': {},
                        'Li25': {},
                        'Li26': {},
                        'Li27': {},
                        'Li28': {},
                        'Li29': {},
                        'Li30': {},
                        'Li31': {},
                        'Li32': {},
                        'Li33': {}},
                    'lobula lobula plate tangential': {
                        'LLPt': {}},
                    'lobula medulla amacrine': {
                        'CT1': {},
                        'LMa1': {},
                        'LMa2': {},
                        'LMa3': {},
                        'LMa4': {},
                        'LMa5': {}},
                    'lobula medulla tangential': {
                        'LMt1': {},
                        'LMt2': {},
                        'LMt3': {},
                        'LMt4': {}},
                    'lobula plate intrinsic': {
                        'LPi01': {},
                        'LPi02': {},
                        'LPi03': {},
                        'LPi04': {},
                        'LPi05': {},
                        'LPi06': {},
                        'LPi07': {},
                        'LPi08': {},
                        'LPi09': {},
                        'LPi10': {},
                        'LPi11': {},
                        'LPi12': {},
                        'LPi13': {},
                        'LPi14': {},
                        'LPi15': {}},
                    'medulla intrinsic': {
                        'Mi1': {},
                        'Mi2': {},
                        'Mi4': {},
                        'Mi9': {},
                        'Mi10': {},
                        'Mi13': {},
                        'Mi14': {},
                        'Mi15': {}},
                    'medulla lobula lobula plate amacrine': {
                        'Am1': {}},
                    'medulla lobula tangential': {
                        'MLt1': {},
                        'MLt2': {},
                        'MLt3': {},
                        'MLt4': {},
                        'MLt5': {},
                        'MLt6': {},
                        'MLt7': {},
                        'MLt8': {}},
                    'proximal distal medulla tangential': {
                        'PDt': {}},
                    'proximal medulla': {
                        'Pm01': {},
                        'Pm02': {},
                        'Pm03': {},
                        'Pm04': {},
                        'Pm05': {},
                        'Pm06': {},
                        'Pm07': {},
                        'Pm08': {},
                        'Pm09': {},
                        'Pm10': {},
                        'Pm11': {},
                        'Pm12': {},
                        'Pm13': {},
                        'Pm14': {}},
                    'serpentine medulla': {
                        'Sm01': {},
                        'Sm02': {},
                        'Sm03': {},
                        'Sm04': {},
                        'Sm05': {},
                        'Sm06': {},
                        'Sm07': {},
                        'Sm08': {},
                        'Sm09': {},
                        'Sm10': {},
                        'Sm11': {},
                        'Sm12': {},
                        'Sm13': {},
                        'Sm14': {},
                        'Sm15': {},
                        'Sm16': {},
                        'Sm17': {},
                        'Sm18': {},
                        'Sm19': {},
                        'Sm20': {},
                        'Sm21': {},
                        'Sm22': {},
                        'Sm23': {},
                        'Sm24': {},
                        'Sm25': {},
                        'Sm26': {},
                        'Sm27': {},
                        'Sm28': {},
                        'Sm29': {},
                        'Sm30': {},
                        'Sm31': {},
                        'Sm32': {},
                        'Sm33': {},
                        'Sm34': {},
                        'Sm35': {},
                        'Sm36': {},
                        'Sm37': {},
                        'Sm38': {},
                        'Sm39': {},
                        'Sm40': {},
                        'Sm41': {},
                        'Sm42': {},
                        'Sm43': {}},
                    'T1 neuron': {
                        'T1': {},
                    },
                    'T2 neuron': {
                        'T2': {},
                        'T2a': {}},
                    'T3 neuron': {
                        'T3': {}},
                    'T4 neuron': {
                        'T4a': {},
                        'T4b': {},
                        'T4c': {},
                        'T4d': {}},
                    'T5 neuron': {
                        'T5a': {},
                        'T5b': {},
                        'T5c': {},
                        'T5d': {}},
                    'translobula plate': {
                        'Tlp1': {},
                        'Tlp4': {},
                        'Tlp5': {},
                        'Tlp14': {}},
                    'transmedullary': {
                        'Tm1': {},
                        'Tm2': {},
                        'Tm3': {},
                        'Tm4': {},
                        'Tm5a': {},
                        'Tm5b': {},
                        'Tm5c': {},
                        'Tm5d': {},
                        'Tm5e': {},
                        'Tm5f': {},
                        'Tm7': {},
                        'Tm8a': {},
                        'Tm8b': {},
                        'Tm9': {},
                        'Tm16': {},
                        'Tm20': {},
                        'Tm21': {},
                        'Tm25': {},
                        'Tm27': {},
                        'Tm31': {},
                        'Tm32': {},
                        'Tm33': {},
                        'Tm34': {},
                        'Tm35': {},
                        'Tm36': {},
                        'Tm37': {}},
                    'transmedullary Y': {
                        'TmY3': {},
                        'TmY4': {},
                        'TmY5a': {},
                        'TmY9q': {},
                        'TmY9q__perp': {},
                        'TmY10': {},
                        'TmY11': {},
                        'TmY14': {},
                        'TmY15': {},
                        'TmY16': {},
                        'TmY20': {},
                        'TmY31': {}},
                    'Y neuron': {
                        'Y1': {},
                        'Y3': {},
                        'Y4': {},
                        'Y11': {},
                        'Y12': {}}},
                'visual projection': {
                    'LC': {
                        'LC34': {},
                        'LC33a': {},
                        'LCe07': {},
                        'LC19': {},
                        'LC31b': {},
                        'LC41': {},
                        'LC15': {},
                        'LC4': {},
                        'LC16': {},
                        'LCe04': {},
                        'LC40': {},
                        'LC35': {},
                        'LC10f': {},
                        'LC10a': {},
                        'LC10b': {},
                        'LC46': {},
                        'LC43': {},
                        'LC10c': {},
                        'LC22': {},
                        'LC17': {},
                        'LC25': {},
                        'LC12': {},
                        'LC26': {},
                        'LC44': {},
                        'LC29': {},
                        'LC27': {},
                        'LCe09': {},
                        'LCe01a': {},
                        'LC13': {},
                        'LCe06': {},
                        'LC28a': {},
                        'LC21': {},
                        'LC37a': {},
                        'LC20b': {},
                        'LCe05': {},
                        'LC36': {},
                        'LC18': {},
                        'LC31c': {},
                        'LC24': {},
                        'LC45': {},
                        'LC39': {},
                        'LC9': {},
                        'LCe03': {},
                        'LC6': {},
                        'LCe01': {},
                        'LC10e': {},
                        'LC20a': {},
                        'LC31a': {},
                        'LC11': {},
                        'LCe02': {},
                        'LC10d': {},
                        'LCe01b': {},
                        'LCe08': {}},
                    'LT': {
                        'LTe59': {},
                        'LTe75': {},
                        'LTe30': {},
                        'LTe44': {},
                        'LT52': {},
                        'LTe13': {},
                        'LTe16': {},
                        'LT43': {},
                        'LTe51': {},
                        'LT59': {},
                        'LTe65': {},
                        'LT63': {},
                        'LT69': {},
                        'LTe10': {},
                        'LTe52a': {},
                        'LTe31': {},
                        'LT82a': {},
                        'LTe33': {},
                        'LTe52b': {},
                        'LTe55': {},
                        'LTe61': {},
                        'LTe46': {},
                        'LTe23': {},
                        'LTe49e': {},
                        'LT61a': {},
                        'LT83': {},
                        'LTe49b': {},
                        'LTe72': {},
                        'LTe60': {},
                        'LTe09': {},
                        'LTe69': {},
                        'LTe49c': {},
                        'LTe06': {},
                        'LT75': {},
                        'LTe66': {},
                        'LTe04': {},
                        'LT79': {},
                        'LTe76': {},
                        'LT1b': {},
                        'LTe73': {},
                        'LTe50': {},
                        'LT1a': {},
                        'LTe21': {},
                        'LTe56': {},
                        'LTe22': {},
                        'LTe58': {},
                        'LT60': {},
                        'LT80': {},
                        'LTe48': {},
                        'LT72': {},
                        'LTe29': {},
                        'LTe57': {},
                        'LTe41': {},
                        'LT76': {},
                        'LT66': {},
                        'LTe42a': {},
                        'LT1d': {},
                        'LTe17': {},
                        'LTe49f': {},
                        'LTe54': {},
                        'LT68': {},
                        'LT65': {},
                        'LT84': {},
                        'LTe07': {},
                        'LTe49a': {},
                        'LT67': {},
                        'LTe43': {},
                        'LTe15': {},
                        'LTe05': {},
                        'LT51': {},
                        'LTe62': {},
                        'LTe02': {},
                        'LTe70': {},
                        'LTe63': {},
                        'LTe38c': {},
                        'LTe11': {},
                        'LTe37': {},
                        'LT47': {},
                        'LTe28': {},
                        'LTe68': {},
                        'LTe12': {},
                        'LT74': {},
                        'LTe42c': {},
                        'LT61b': {},
                        'LTe14': {},
                        'LTe27': {},
                        'LTe74': {},
                        'LTe53': {},
                        'LTe67': {},
                        'LT86': {},
                        'LTe08': {},
                        'LT87': {},
                        'LTe38a': {},
                        'LT81': {},
                        'LT62': {},
                        'LT78': {},
                        'LTe40': {},
                        'LTe38b': {},
                        'LT53': {},
                        'LT85': {},
                        'LTe25': {},
                        'LTe19': {},
                        'LTe24': {},
                        'LT55': {},
                        'LTe47': {},
                        'LT57': {},
                        'LT64': {},
                        'LT73': {},
                        'LTe32': {},
                        'LTe42b': {},
                        'LTe26': {},
                        'LTe45': {},
                        'LT11': {},
                        'LTe36': {},
                        'LTe01': {},
                        'LTe20': {},
                        'LTe35': {},
                        'LTe18': {},
                        'LTe03': {},
                        'LTe49d': {},
                        'LT1c': {},
                        'LT77': {},
                        'LTe64': {}},
                    'LPC': {
                        'LPC1': {},
                        'LPC2': {}},
                    'LPLC': {
                        'LPLC4': {},
                        'LPLC2': {},
                        'LPLC1': {}},
                    'LLPC': {
                        'LLPC3': {},
                        'LLPC2': {},
                        'LLPC4': {},
                        'LLPC1': {}},
                    'LPT': {
                        'LPT28': {},
                        'LPT42_Nod4': {},
                        'LPT51': {},
                        'LPT49': {},
                        'LPT52': {},
                        'LPT50': {},
                        'LPT31': {},
                        'LPT23': {},
                        'LPTe01': {},
                        'LPT27': {},
                        'LPT22': {},
                        'LPT48_vCal3': {},
                        'LPT26': {},
                        'LPT21': {},
                        'LPTe02': {},
                        'LPT29': {},
                        'LPT04_HST': {},
                        'LPT47_vCal2': {},
                        'LPT54': {},
                        'LPT30': {}},
                    'MeMe': {
                        'MeMe_e04': {},
                        'MeMe_e05': {},
                        'MeMe_e07': {},
                        'MeMe_e02': {},
                        'MeMe_e08': {},
                        'MeMe_e06': {},
                        'MeMe_e03': {}},
                    'MeTu': {
                        'MeTu4_unknown': {},
                        'MeTu3c': {},
                        'MeTu1': {},
                        'MeTu3a': {},
                        'MeTu4b': {},
                        'MeTu4a': {},
                        'MeTu2b': {},
                        'MeTu3b': {},
                        'MeTu4c': {},
                        'MeTu2a': {},
                        'MeTu4d': {}},
                    'MeLp': {
                        'MeLp1': {}},
                    'aMe': {
                        'aMe19a': {},
                        'aMe9': {},
                        'aMe19b': {},
                        'aMe20': {},
                        'aMe3': {},
                        'aMe6a': {},
                        'aMe1': {},
                        'aMe5': {},
                        'aMe8': {},
                        'aMe25': {},
                        'aMe12': {},
                        'aMe26': {},
                        'aMe10': {}},
                    'VS': {
                        'VS2': {},
                        'VST1': {},
                        'VST2': {},
                        'VSm': {},
                        'VS8': {},
                        'VS3': {},
                        'VS4': {},
                        'VS1': {},
                        'VS6': {},
                        'VS7': {},
                        'VS5': {}},
                    'MT': {
                        'MTe32': {},
                        'MTe47': {},
                        'MTe36': {},
                        'MTe01a': {},
                        'MTe48': {},
                        'MTe24': {},
                        'MTe50': {},
                        'MTe45': {},
                        'MTe10': {},
                        'MTe27': {},
                        'MTe37': {},
                        'MTe11': {},
                        'MTe06': {},
                        'MTe13': {},
                        'MTe03': {},
                        'MTe30': {},
                        'MTe28': {},
                        'MTe19': {},
                        'MTe26': {},
                        'MTe49': {},
                        'MTe40': {},
                        'MTe44': {},
                        'MTe29': {},
                        'MTe25': {},
                        'MTe43': {},
                        'MTe53': {},
                        'MTe07': {},
                        'MTe23': {},
                        'MTe20': {},
                        'MTe09': {},
                        'MTe16': {},
                        'MTe18': {},
                        'MTe39': {},
                        'MTe35': {},
                        'MTe54': {},
                        'MTe12': {},
                        'MTe02': {},
                        'MTe08': {},
                        'MTe31': {},
                        'MTe42': {},
                        'MTe17': {},
                        'MTe14': {},
                        'MTe52': {},
                        'MTe38': {},
                        'MTe22': {},
                        'MTe51': {},
                        'MTe01b': {},
                        'MTe46': {},
                        'MTe05': {},
                        'MTe04': {},
                        'MTe34': {},
                        'MTe33': {},
                        'MTe15': {},
                        'MTe41': {},
                        'MTe21': {}},
                    'Nod': {
                        'Nod1': {},
                        'Nod3': {},
                        'Nod5': {},
                        'Nod2': {}},
                    'H': {
                        'H2': {}},
                    'HS': {
                        'HSS': {},
                        'HSE': {},
                        'HSN': {}},
                    'MC': {
                        'MC65': {}}},
                'visual centrifugal': {
                    'LT': {
                        'LT34': {},
                        'LT40': {},
                        'LT41': {},
                        'LT36': {},
                        'LT42': {},
                        'LT39': {},
                        'LT37': {},
                        'LT56': {},
                        'LT38': {},
                        'LT70': {}},
                    'LPT': {
                        'LPT53': {},
                        'LPT58': {},
                        'LPT57': {}},
                    'aMe': {
                        'aMe17a2': {},
                        'aMe4': {},
                        'aMe17a1': {},
                        'aMe17b': {},
                        'aMe17c': {}},
                    'mAL': {
                        'mALC5': {},
                        'mALC4': {},
                        'mALC3': {}},
                    'cM': {
                        'cM07': {},
                        'cM16': {},
                        'cM05': {},
                        'cM02a': {},
                        'cM01a': {},
                        'cM08a': {},
                        'cM01c': {},
                        'cM08b': {},
                        'cM06': {},
                        'cM11': {},
                        'cM03': {},
                        'cM12': {},
                        'cM10': {},
                        'cM19': {},
                        'cM18': {},
                        'cM02b': {},
                        'cM04': {},
                        'cM09': {},
                        'cM14': {},
                        'cM17': {},
                        'cM15': {},
                        'cM13': {},
                        'cM08c': {},
                        'cM01b': {}},
                    'cML': {
                        'cML01': {},
                        'cML02': {}},
                    'cMLLP': {
                        'cMLLP01': {},
                        'cMLLP02': {}},
                    'cL': {
                        'cL22b': {},
                        'cL21': {},
                        'cL13': {},
                        'cL15': {},
                        'cL08': {},
                        'cL07': {},
                        'cL22c': {},
                        'cL19': {},
                        'cL12': {},
                        'cL02d': {},
                        'cL22a': {},
                        'cL02a': {},
                        'cL04': {},
                        'cL02b': {},
                        'cL10': {},
                        'cL14': {},
                        'cL11': {},
                        'cL17': {},
                        'cL09': {},
                        'cL18': {},
                        'cL03': {},
                        'cL02c': {},
                        'cL16': {},
                        'cL06': {},
                        'cL20': {},
                        'cL05': {},
                        'cL01': {}},
                    'cLM': {
                        'cLM01': {}},
                    'cLP': {
                        'cLPL01': {},
                        'cLP04': {},
                        'cLP05': {},
                        'cLP01': {},
                        'cLP02': {},
                        'cLP03': {}},
                    'cLLP': {
                        'cLLP02': {}},
                    'cLLPM': {
                        'cLLPM01': {},
                        'cLLPM02': {}},
                    'VC': {
                        'VCH': {}},
                    'OA': {
                        'OA-AL2i4': {},
                        'OA-AL2i1': {},
                        'OA-AL2b1': {},
                        'OA-ASM1': {},
                        'OA-AL2i3': {},
                        'OA-AL2i2': {},
                        'OA-AL2b2': {}}},
                'central brain intrinsic': {},
                'VNC intrinsic': {}},
            'glia': {
                'trachea': {},
                'astrocyte': {},
                'cortex glia': {},
                'ensheathing glia': {},
                'perineural glia': {},
                'subperineural glia': {}}},
        'efferent': {
            'motor neuron': {},
            'UM neuron': {},
            'endocrine': {}}},
    'hemilineage': {
        '0A': {},
        '0B': {},
        '1A': {},
        '1B': {},
        '2A': {},
        '3A': {},
        '3B': {},
        '4A': {},
        '4B': {},
        '5B': {},
        '6A': {},
        '6B': {},
        '7B': {},
        '8A': {},
        '8B': {},
        '9A': {},
        '9B': {},
        '10B': {},
        '11A': {},
        '11B': {},
        '12A': {},
        '12B': {},
        '13A': {},
        '13B': {},
        '14A': {},
        '14B': {},
        '15B': {},
        '16B': {},
        '17A': {},
        '18B': {},
        '19A': {},
        '19B': {},
        '20A/22A': {},
        '21A': {},
        '23B': {},
        '24A': {},
        '24B': {}},
    'fast neurotransmitter': {
        'cholinergic': {},
        'GABAergic': {},
        'glutamatergic': {}},
    'other neurotransmitter': {
        'dopaminergic': {},
        'histaminergic': {},
        'octopaminergic': {},
        'serotonergic': {},
        'tyraminergic': {}},
    'soma side': {
        'soma on left': {},
        'soma on right': {},
        'soma on midline': {}},
    'soma region': {
        'soma in brain': {
            'soma in central brain': {},
            'soma in optic lobe': {}},
        'soma in VNC': {
            'soma in T1': {},
            'soma in T2': {},
            'soma in T3': {},
            'soma in abdominal ganglion': {}}},
    'anterior-posterior projection pattern': {
        'leg local': {
            'T1 leg local': {},
            'T2 leg local': {},
            'T3 leg local': {}},
        'descending': {},
        'ascending': {}},
    'left-right projection pattern': {
        'unilateral': {},
        'bilateral': {},
        'midplane': {}},
    'body part innervated': {
        'innervates antenna': {
            'innervates scape': {},
            'innervates pedicel': {},
            'innervates funiculus': {
                'innervates sacculus': {}},
            'innervates arista': {}},
        'innervates maxillary palp': {},
        'innervates proboscis': {},
        'innervates retina': {},
        'innervates ocelli': {},
        'innervates neck': {},
        'innervates corpus cardiacum': {},
        'innervates corpus allatum': {},
        'innervates aorta': {},
        'innervates leg': {
            'innervates T1 leg': {
                'innervates thorax': {},
                'innervates thorax-coxa joint': {},
                'innervates coxa': {},
                'innervates coxa-trochanter joint': {},
                'innervates trochanter': {},
                'innervates femur': {},
                'innervates femur-tibia joint': {},
                'innervates tibia': {},
                'innervates tarsus': {}},
            'innervates T2 leg': {
                'innervates thorax': {},
                'innervates thorax-coxa joint': {},
                'innervates coxa': {},
                'innervates coxa-trochanter joint': {},
                'innervates trochanter': {},
                'innervates femur': {},
                'innervates femur-tibia joint': {},
                'innervates tibia': {},
                'innervates tarsus': {}},
            'innervates T3 leg': {
                'innervates thorax': {},
                'innervates thorax-coxa joint': {},
                'innervates coxa': {},
                'innervates coxa-trochanter joint': {},
                'innervates trochanter': {},
                'innervates femur': {},
                'innervates femur-tibia joint': {},
                'innervates tibia': {},
                'innervates tarsus': {}}},
        'innervates wing': {},
        'innervates haltere': {},
        'innervates spiracle': {},
        'innervates abdomen': {}},
    'muscle innervated': {
        'innervates tergopleural promotor': {},
        'innervates pleural promotor': {},
        'innervates pleural remotor and abductor': {},
        'innervates sternal anterior rotator': {},
        'innervates sternal posterior rotator': {},
        'innervates sternal adductor': {},
        'innervates tergotrochanter extensor': {},
        'innervates sternotrochanter extensor': {},
        'innervates trochanter extensor': {},
        'innervates trochanter flexor': {},
        'innervates accessory trochanter flexor': {},
        'innervates femur reductor': {},
        'innervates tibia extensor': {},
        'innervates tibia flexor': {},
        'innervates accessory tibia flexor': {},
        'innervates tarsus depressor': {},
        'innervates tarsus retro depressor': {},
        'innervates tarsus levator muscle': {},
        'innervates long tendon muscle 2': {},
        'innervates long tendon muscle 1': {},
        'innervates indirect flight muscle': {
            'innervates dorsal longitudinal muscle': {},
            'innervates dorsoventral muscle': {}},
        'innervates wing steering muscle': {},
        'innervates wing tension muscle': {}},
    'motor neuron primary neurite bundle': {
        'L1 bundle': {},
        'L2 bundle': {},
        'L3 bundle': {},
        'L4 bundle': {},
        'L5 bundle': {},
        'A1 bundle': {},
        'A2 bundle': {},
        'A3 bundle': {},
        'A4 bundle': {},
        'A5 bundle': {},
        'V1 bundle': {},
        'V2 bundle': {},
        'V3 bundle': {},
        'V4 bundle': {},
        'V5 bundle': {},
        'V6 bundle': {},
        'D1 bundle': {},
        'D2 bundle': {},
        'L6 bundle': {},
        'L7 bundle': {},
        'L8 bundle': {},
        'L9 bundle': {},
        'L10 bundle': {},
        'L11 bundle': {},
        'L12 bundle': {},
        'L13 bundle': {},
        'A6 bundle': {},
        'A7 bundle': {},
        'PDMN bundle': {},
        'A11 bundle': {},
        'A12 bundle': {},
        'L14 bundle': {},
        'L15 bundle': {},
        'L16 bundle': {},
        'L18 bundle': {},
        'tbd bundle': {},
        'C1 bundle': {},
        'D bundle': {},
        'A8 bundle': {},
        'A9 bundle': {},
        'A10 bundle': {},
        'ADMN1 bundle': {},
        'ADMN2 bundle': {},
        'ADMN3 bundle': {},
        'PDMN1 bundle': {},
        'PDMN2 bundle': {},
        'HN bundle': {},
        'T3 H1 bundle': {},
        'T3 H2 bundle': {},
        'T3 H3 bundle': {}},
    'neuron identity': {},
    'freeform': {},
}
FANC_cell_info = cell_info.copy()
FANC_cell_info['publication'] = {
    'Azevedo Lesser Phelps Mark et al. 2024': {},
    'Lesser Azevedo et al. 2024': {},
    'Cheong Boone Bennett et al. 2023': {},
    'Sapkal et al. 2023': {},
    'Yang et al. 2023': {},
    'Dallmann et al. 2023': {},
    'Yoshikawa et al. 2024': {},
    'Lee et al. 2024': {},
    'Stürner Brooks ... Eichler 2024': {},
    'Syed et al. 2024': {},
    'Guo et al. 2024': {},
}

proofreading_notes = [
    'spans neck',
    'soma is damaged',
    'arbor is damaged',
    'thoroughly proofread',
    'merge monster',
]

# A mapping that tells which CAVE tables are governed by which
# annotation lists/hierarchies
rules_governing_tables = {
    'neuron_information': FANC_cell_info,
    'cell_info': cell_info,
    'proofreading_notes': proofreading_notes,
}


# ------------------------- #


def _dict_to_anytree(dictionary):
    """
    Given a dictionary containing a hierarchy of strings, return a dictionary
    with each string as a key and the corresponding anytree.Node as the value.
    """
    def _build_tree(annotations: dict, parent: dict = None, nodes: dict = {}):
        for annotation in annotations.keys():
            node = anytree.Node(annotation, parent=parent)
            nodes[annotation] = nodes.get(annotation, []) + [node]
            _build_tree(annotations[annotation], parent=node, nodes=nodes)
        return nodes

    return _build_tree(dictionary)


# Convert any hierarchical dictionaries to a tree format that is easier to use
rules_governing_tables = {table_name: _dict_to_anytree(annotations)
                          if isinstance(annotations, dict) else annotations
                          for table_name, annotations in rules_governing_tables.items()}


def print_recognized_annotations(table_name: str = default_table):
    """
    Print the annotation hierarchy for a table.

    Parameters
    ----------
    table_name : str
        The name of the table to print the recognized annotations for.
        OR
        Users will not typically do this, but you can also pass in a list or
        dict specifying the valid annotations directly and it will be used. If
        a dictionary, must map annotation names (str) to anytree.Node objects,
        as output by running _dict_to_anytree() on a hierarchy of annotations.
    """
    if isinstance(table_name, str):
        try:
            annotations = rules_governing_tables[table_name]
        except:
            raise ValueError(f'Table name "{table_name}" not recognized.')
    elif isinstance(table_name, (dict, list)):
        annotations = table_name
    else:
        raise TypeError(f'Unrecognized type for table_name: {type(table_name)}')

    if isinstance(annotations, dict):
        def print_one_tree(annotations, root: str):
            for prefix, _, node in anytree.RenderTree(annotations[root][0]):
                print(f'{prefix}{node.name}')

        for root_node in {anno for anno, nodes in annotations.items()
                          if len(nodes) == 1 and nodes[0].is_root}:
            print_one_tree(annotations, root_node)
    elif isinstance(annotations, list):
        for annotation in annotations:
            print(annotation)


def guess_class(annotation: str, table_name: str = default_table) -> str:
    """
    Look up the parent (or "class") of an annotation based on the rules
    governing the given table. If the annotation is not found or the
    class can't be determined, raise a ValueError.

    Parameters
    ----------
    annotation : str
        The annotation to look up the class of.
    table_name : str
        The name of the table whose rules should be used to look up the
        class of the annotation.
        OR
        Users will not typically do this, but you can also pass in a dict
        specifying the annotation hierarchy/rules directly. The dict must
        map annotation names (str) to anytree.Node objects, as output by
        running _dict_to_anytree() on a hierarchy of annotations.
    """
    if isinstance(table_name, str):
        try:
            annotations = rules_governing_tables[table_name]
        except KeyError:
            raise ValueError(f'Table name "{table_name}" not recognized.')
        if not isinstance(annotations, dict):
            raise ValueError(f'"{table_name}" does not use paired annotations.')
    elif isinstance(table_name, dict):
        annotations = table_name
    else:
        raise TypeError(f'Unrecognized type for table_name: {type(table_name)}')

    try:
        annotation_nodes = annotations[annotation]
    except KeyError:
        raise ValueError(f'Annotation "{annotation}" not recognized. {help_msg}')

    if len(annotation_nodes) > 1:
        raise ValueError(f'Class of "{annotation}" could not be guessed'
                         f' because it has multiple possible classes. {help_msg}')

    if annotation_nodes[0].is_root:
        raise ValueError(f'"{annotation}" is a base annotation with no class. {help_msg}')
    return annotation_nodes[0].parent.name


def is_valid_annotation(annotation: str or tuple[str, str] or bool,
                        table_name: str = default_table,
                        response_on_unrecognized_table='raise',
                        raise_errors: bool = True) -> bool:
    """
    Determine whether an annotation is a recognized/valid annotation
    for the given table.

    Parameters
    ----------
    annotation : str or list/tuple of 2 strs or bool
        The annotation or annotation pair to check the validity of.
    table_name : str
        The name of the table whose rules should be used to determine the
        validity of the annotation.
        OR
        Users will not typically do this, but you can also pass in a list or
        dict specifying the valid annotations directly and it will be used. If
        a dictionary, must map annotation names (str) to anytree.Node objects,
        as output by running _dict_to_anytree() on a hierarchy of annotations.
    """
    if isinstance(table_name, str):
        annotations = rules_governing_tables.get(table_name, None)
        if annotations is None:
            client = auth.get_caveclient()
            if (client.annotation.get_table_metadata(table_name)['schema_type']
                    != 'proofreading_boolstatus_user'):
                if response_on_unrecognized_table == 'raise':
                    raise ValueError(f'No annotation rules found for table "{table_name}"')
                return response_on_unrecognized_table
            annotations = [True, False]
    elif isinstance(table_name, (dict, list)):
        annotations = table_name
    else:
        raise TypeError(f'Unrecognized type for table_name: {type(table_name)}')

    if isinstance(annotations, list):
        if (annotation not in annotations) and raise_errors:
            raise ValueError(f'Annotation "{annotation}" not recognized. {help_msg}')
        return annotation in annotations

    if raise_errors:
        annotation_class, annotation = parse_annotation_pair(annotation)
    else:
        try:
            annotation_class, annotation = parse_annotation_pair(annotation)
        except:
            return False
    return is_valid_pair(annotation_class, annotation,
                         annotations, raise_errors=raise_errors)


def parse_annotation_pair(annotation: str or tuple[str, str],
                          table_name: str = default_table) -> tuple[str, str]:
    """
    Convert any of the following into a proper (annotation_class, annotation) tuple:
    - A single annotation (str). In this case the annotation_class will be
      guessed based on the rules governing the given table.
    - An annotation_class-annotation pair given as one string with a separator
      (colon, comma, or >) between the annotation_class and annotation.
    - An (annotation_class, annotation) pair given as a 2-length iterable.

    Parameters
    ----------
    annotation : str or list/tuple of 2 strs
        The annotation or annotation pair to parse.

    Returns
    -------
    tuple of 2 strs
        The annotation_class and annotation.
    """
    # If not a str, should be a 2-length iterable
    if not isinstance(annotation, str):
        try:
            annotation_class, annotation = annotation
        except:
            raise TypeError('annotation must be a str or a list/tuple of 2 strs.')
        return annotation_class, annotation

    # If str
    separators = ':>,'
    if not any(separator in annotation for separator in separators):
        annotation_class = guess_class(annotation, table_name)
    else:
        for separator in separators:
            if separator in annotation:
                annotation_class, annotation = annotation.split(separator)
                break
        annotation_class = annotation_class.strip(' ')
        annotation = annotation.strip(' ')

    return annotation_class, annotation


def is_valid_pair(annotation_class: str,
                  annotation: str,
                  table_name: str = default_table,
                  raise_errors: bool = True) -> bool:
    """
    Determine whether `annotation` is a valid annotation for the given
    `annotation_class`, according to the rules for the given table.
    See https://banc.community/Annotations-(cell-types,-etc.)

    Parameters
    ----------
    annotation_class, annotation : str
        The pair of annotations to check the validity of.
    table_name : str
        The name of the table whose rules should be used to determine the
        validity of the annotation.
        OR
        Users will not typically do this, but you can also pass in a dict
        specifying the valid annotations directly and it will be used. The
        dict must map annotation names (str) to anytree.Node objects, as
        output by running _dict_to_anytree() on a hierarchy of annotations.
    """
    if isinstance(table_name, str):
        try:
            annotations = rules_governing_tables[table_name]
        except KeyError:
            raise ValueError(f'Table name "{table_name}" not recognized.')
        if not isinstance(annotations, dict):
            raise ValueError(f'"{table_name}" does not use paired annotations.')
    elif isinstance(table_name, dict):
        annotations = table_name
    else:
        raise TypeError(f'Unrecognized type for table_name: {type(table_name)}')

    if annotation_class in ['neuron identity', 'freeform']:
        if annotation in annotations:
            if raise_errors:
                raise ValueError(f'The term "{annotation}" is a class,'
                                 f' not an identity. {help_msg}')
            return False
        if (' and ' in annotation.lower()
                or annotation.lower().startswith('and ')
                or annotation.lower().endswith(' and')):
            if raise_errors:
                raise ValueError('An annotation may not contain " and ".'
                                 ' Consider using "&" instead.')
            return False
        if annotation.lower().startswith('not '):
            if raise_errors:
                raise ValueError('An annotation may not start with "not ".'
                                 ' Try to rephrase the annotation.')
            return False
        return True

    try:
        class_nodes = annotations[annotation_class]
    except KeyError:
        if raise_errors:
            raise ValueError(f'Annotation class "{annotation_class}" not'
                             f' recognized. {help_msg}')
        return False
    try:
        annotation_nodes = annotations[annotation]
    except KeyError:
        if raise_errors:
            raise ValueError(f'Annotation "{annotation}" not recognized.'
                             f' {help_msg}')
        return False

    for class_node in class_nodes:
        for annotation_node in annotation_nodes:
            if annotation_node in class_node.children:
                return True

    if raise_errors:
        parent_names = [node.parent.name
                        if node.parent is not None else '<no class>'
                        for node in annotation_nodes]
        if len(annotation_nodes) == 1:
            raise ValueError(f'Annotation "{annotation}" belongs to class'
                             f' "{parent_names[0]}" but you specified class'
                             f' "{annotation_class}". {help_msg}')
        else:
            raise ValueError(f'Annotation "{annotation}" belongs to classes'
                             f' {parent_names} but you specified class'
                             f' "{annotation_class}". {help_msg}')
    return False


class MissingParentAnnotationError(Exception):
    def __init__(self, missing_annotation, message):
        self.missing_annotation = missing_annotation
        self.message = message
        super().__init__(message)


def is_allowed_to_post(segid: int,
                       annotation: str or tuple[str, str] or bool,
                       table_name: str = default_table,
                       response_on_unrecognized_table='raise',
                       raise_errors: bool = True) -> bool:
    """
    Determine whether a particular segment is allowed to be annotated
    with the given annotation (or annotation_class+annotation pair, if the
    table uses paired annotations).

    For posting to be allowed:
    - `is_valid_annotation(annotation, table_name)` must return True.
    - The segment must not already have this exact annotation in this table.
    - For tables that use paired annotations (two tag columns), two
      additional constraints apply:
      1. The given annotation pair may not be posted if the segment
      already has any annotation pair with the same annotation_class.
      This and also prevents a class from having multiple subclasses.
      This rule is NOT enforced for a few special annotation_classes
      that are allowed to have many subannotations:
        - 'neuron identity'
        - 'freeform'
        - 'publication'
      2. The given annotation pair may only be posted if its
      annotation_class is at the root of the annotation tree (e.g.
      'primary class'), or if its annotation_class is already an
      annotation on the segment. In other words, allow posts will start
      from the root of the annotation tree, or add detail/subclass
      information to an annotation already on the segment.

    For tables with two tag columns, `annotation` should be in a format
    that `parse_annotation_pair()` can handle, which is:
    - A single annotation (str). In this case the annotation_class will
      be guessed based on the rules governing the given table.
    - An annotation_class-annotation pair given as one string with a separator
      (colon, comma, or >) between the annotation_class and annotation.
    - An (annotation_class, annotation) pair given as a 2-length iterable.

    Returns
    -------
    bool
    - True: This segment MAY be annotated with the annotation or
      annotation_class+annotation pair in the given CAVE table without
      violating any rules about redundancy or mutual exclusivity.
    - False: The proposed annotation or annotation_class+annotation pair
      MAY NOT be posted for this segment without violating a rule.
      If `raise_errors` is True, an exception with an informative error
      message will be raised instead of returning False.
    """
    annotations = rules_governing_tables.get(table_name, None)
    if annotations is None:
        client = auth.get_caveclient()
        if (client.annotation.get_table_metadata(table_name)['schema_type']
                != 'proofreading_boolstatus_user'):
            if response_on_unrecognized_table == 'raise':
                raise ValueError(f'No annotation rules found for table "{table_name}"')
            return response_on_unrecognized_table
        if not isinstance(annotation, bool):
            raise ValueError(f'Table "{table_name}" only uses True/False annotations.')
        existing_annos = client.materialize.live_live_query(
            table_name,
            datetime.now(timezone.utc),
            filter_equal_dict={table_name: {
                'valid_id': segid,
                'proofread': {True: 't', False: 'f'}[annotation]
            }}
        )
        if raise_errors and not existing_annos.empty:
            raise ValueError(f'Segment {segid} already has this annotation'
                             f' in the table "{table_name}".')
        return existing_annos.empty

    if not is_valid_annotation(annotation, table_name=table_name,
                               response_on_unrecognized_table=response_on_unrecognized_table,
                               raise_errors=raise_errors):
        return False

    existing_annos = lookup.annotations(segid, source_tables=table_name,
                                        return_details=True)

    if isinstance(annotations, list):
        if annotation in existing_annos.tag.values:
            if raise_errors:
                raise ValueError(f'Segment {segid} already has the'
                                 f' annotation "{annotation}".')
            return False
        return True

    # If we get here, the table uses paired annotations
    if raise_errors:
        annotation_class, annotation = parse_annotation_pair(annotation)
    else:
        try:
            annotation_class, annotation = parse_annotation_pair(annotation)
        except:
            return False

    # Rule 1
    multiple_subclasses_allowed = [
        'other neurotransmitter',
        'neuron identity',
        'freeform',
        'publication'
    ]
    if annotation_class in multiple_subclasses_allowed:
        # Check if any tag,tag2 pair is the same as annotation,annotation_class
        if ((existing_annos.tag == annotation) &
                (existing_annos.tag2 == annotation_class)).any():
            if raise_errors:
                raise ValueError(f'Segment {segid} already has this exact'
                                 ' annotation pair.')
            return False
        #------
        # The block of code below is not currently used due to a refactoring of
        # the annotation tree, but it might be useful to bring back later
        #------
        # Multiple subclasses are only allowed if they don't violate the
        # following mutual exclusivity rules. For example, a neuron can't be
        # annotated with both 'unilateral' and 'bilateral'.
        #exclusivity_groups = [
        #    # Exclusivity groups within 'projection pattern':
        #    {'unilateral', 'bilateral'},
        #    {'local', 'intersegmental', 'ascending', 'descending'}
        #]
        #for group in exclusivity_groups:
        #    if annotation in group:
        #        # Check if any annotation in this group already exists
        #        if not existing_annos.loc[existing_annos.tag.isin(group)].empty:
        #            if raise_errors:
        #                raise ValueError(f'Segment {segid} already has an'
        #                                 f' annotation in the group'
        #                                 f' {group}. {help_msg}')
        #            return False
    elif (existing_annos.tag2 == annotation_class).any():
        if raise_errors:
            raise ValueError(f'Segment {segid} already has an annotation with'
                             f' class "{annotation_class}". {help_msg}')
        return False

    # Rule 2
    root_classes = [anno for anno, nodes in annotations.items()
                    if len(nodes) == 1 and nodes[0].is_root]
    if (annotation_class not in root_classes and
            not (existing_annos.tag == annotation_class).any()):
        if raise_errors:
            raise MissingParentAnnotationError(
                annotation_class,
                f'Segment {segid} must be annotated with "{annotation_class}" '
                f'before this term can be used as an annotation class. {help_msg}'
            )
        return False

    return True
